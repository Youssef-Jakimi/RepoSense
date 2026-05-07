import hashlib
import logging
import re
import time
from datetime import timezone

from github import Github, RateLimitExceededException, UnknownObjectException

logger = logging.getLogger(__name__)

_INCLUDE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".rs",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".php", ".swift", ".kt", ".scala",
    ".json", ".yaml", ".yml", ".toml", ".ini",
    ".md", ".rst",
}

_SKIP_DIRS = frozenset({
    "node_modules", ".git", "dist", "build", "__pycache__",
    ".venv", "venv", "vendor", "target", ".next", "coverage",
})

_MAX_FILE_BYTES = 200 * 1024  # 200 KB

_EXT_TO_LANG = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".java": "java",
    ".go": "go", ".rb": "ruby", ".rs": "rust",
    ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
    ".cs": "csharp", ".php": "php", ".swift": "swift",
    ".kt": "kotlin", ".scala": "scala",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".ini": "ini", ".md": "markdown", ".rst": "rst",
}

_ENTRY_POINT_STEMS = frozenset({"main", "index", "app"})
_ENTRY_POINT_EXACT = frozenset({
    "__init__.py", "package.json", "pyproject.toml", "requirements.txt",
    "Cargo.toml", "go.mod", "pom.xml", "setup.py", "README.md",
})


def _parse_github_url(url: str) -> tuple[str, str]:
    url = url.strip().rstrip("/")
    m = re.match(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", url)
    if not m:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return m.group(1), m.group(2)


def _should_skip_path(path: str) -> bool:
    parts = path.split("/")
    for part in parts[:-1]:
        if part in _SKIP_DIRS or part.startswith("."):
            return True
    return parts[-1].startswith(".")


def _get_ext(path: str) -> str:
    i = path.rfind(".")
    return path[i:].lower() if i != -1 else ""


def _detect_language(path: str) -> str:
    return _EXT_TO_LANG.get(_get_ext(path), "other")


def _is_binary(data: bytes) -> bool:
    return b"\x00" in data[:1024]


def _is_entry_point(path: str) -> bool:
    filename = path.split("/")[-1]
    if filename in _ENTRY_POINT_EXACT:
        return True
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    return stem in _ENTRY_POINT_STEMS


def _wait_for_rate_limit(gh: Github) -> None:
    reset_dt = gh.get_rate_limit().core.reset
    if reset_dt.tzinfo is None:
        reset_dt = reset_dt.replace(tzinfo=timezone.utc)
    wait = min(60, max(0, int(reset_dt.timestamp() - time.time())))
    logger.warning("Rate limit hit; sleeping %d s before retry", wait)
    if wait > 0:
        time.sleep(wait)


def _compute_ref_counts(files: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in files:
        filename = f["path"].split("/")[-1]
        stem = filename.rsplit(".", 1)[0] if "." in filename else filename
        pat = re.compile(r"\b" + re.escape(stem) + r"\b")
        counts[f["path"]] = sum(
            1 for other in files
            if other["path"] != f["path"] and pat.search(other["content"])
        )
    return counts


def _trim(files: list[dict], max_bytes: int) -> tuple[list[dict], bool, int]:
    if sum(f["size"] for f in files) <= max_bytes:
        return files, False, 0

    original = len(files)
    entry = [f for f in files if _is_entry_point(f["path"])]
    non_entry = [f for f in files if not _is_entry_point(f["path"])]

    ref_counts = _compute_ref_counts(files)
    non_entry.sort(key=lambda f: (-ref_counts.get(f["path"], 0), f["size"]))

    kept = list(entry)
    cumulative = sum(f["size"] for f in kept)
    for f in non_entry:
        if cumulative >= max_bytes:
            break
        kept.append(f)
        cumulative += f["size"]

    dropped = original - len(kept)
    return kept, dropped > 0, dropped


def _fetch_files(repo, branch: str) -> list[dict]:
    tree = repo.get_git_tree(sha=branch, recursive=True)
    files = []
    for item in tree.tree:
        if item.type != "blob":
            continue
        path = item.path
        if _get_ext(path) not in _INCLUDE_EXTENSIONS:
            continue
        if _should_skip_path(path):
            continue
        if (item.size or 0) > _MAX_FILE_BYTES:
            logger.debug("Skipping oversized file %s (%d B)", path, item.size)
            continue
        try:
            raw: bytes = repo.get_contents(path).decoded_content
        except RateLimitExceededException:
            raise
        except Exception as exc:
            logger.warning("Could not fetch %s: %s", path, exc)
            continue
        if _is_binary(raw):
            logger.debug("Skipping binary: %s", path)
            continue
        size = len(raw)
        if size > _MAX_FILE_BYTES:
            logger.debug("Skipping post-decode oversized: %s", path)
            continue
        files.append({
            "path": path,
            "content": raw.decode("utf-8", errors="replace"),
            "language": _detect_language(path),
            "size": size,
        })
    return files


def load_repo(
    repo_url: str,
    github_token: str | None = None,
    max_total_bytes: int = 2_000_000,
) -> dict:
    """
    Fetch a GitHub repo and return its files plus metadata.

    Returns:
        {
            "repo_id": str,            # sha256(repo_url)[:12]
            "repo_url": str,
            "owner": str,
            "name": str,
            "default_branch": str,
            "files": list[dict],       # [{path, content, language, size}]
            "trimmed": bool,           # True if large-repo trimming was applied
            "trimmed_count": int,      # how many files were dropped
        }
    """
    owner, name = _parse_github_url(repo_url)
    repo_id = hashlib.sha256(repo_url.encode()).hexdigest()[:12]
    gh = Github(github_token) if github_token else Github()

    try:
        repo = gh.get_repo(f"{owner}/{name}")
    except RateLimitExceededException:
        _wait_for_rate_limit(gh)
        try:
            repo = gh.get_repo(f"{owner}/{name}")
        except RateLimitExceededException:
            raise RuntimeError("GitHub API rate limit exceeded. Please try again later.")
    except UnknownObjectException:
        if not github_token:
            raise ValueError("This repo is private. Please provide a GitHub token.")
        raise

    branch = repo.default_branch
    logger.info("Fetching %s/%s @ branch=%s", owner, name, branch)

    try:
        files = _fetch_files(repo, branch)
    except RateLimitExceededException:
        _wait_for_rate_limit(gh)
        try:
            files = _fetch_files(repo, branch)
        except RateLimitExceededException:
            raise RuntimeError("GitHub API rate limit exceeded. Please try again later.")

    logger.info("Loaded %d files; budget=%d B", len(files), max_total_bytes)
    files, trimmed, trimmed_count = _trim(files, max_total_bytes)
    logger.info(
        "Final: %d files%s",
        len(files),
        f" (trimmed {trimmed_count})" if trimmed else "",
    )

    return {
        "repo_id": repo_id,
        "repo_url": repo_url,
        "owner": owner,
        "name": name,
        "default_branch": branch,
        "files": files,
        "trimmed": trimmed,
        "trimmed_count": trimmed_count,
    }
