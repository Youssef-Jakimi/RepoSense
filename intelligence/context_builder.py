import json
import re
from collections import defaultdict

COMMON_NAME_STOPLIST = {
    "get", "set", "run", "init", "main", "call", "execute", "handle",
    "process", "start", "stop", "load", "save", "send", "fetch", "parse",
    "build", "check", "create", "delete", "update", "read", "write",
}

_ENTRY_POINT_STEMS = frozenset({"main", "index", "app", "server"})
_ENTRY_POINT_EXACT = frozenset({
    "__init__.py", "package.json", "pyproject.toml", "setup.py",
    "Cargo.toml", "go.mod", "pom.xml", "Dockerfile",
})

_TREE_MAX_LINES = 30


def _is_entry_point(path: str) -> bool:
    basename = path.split("/")[-1]
    if basename in _ENTRY_POINT_EXACT:
        return True
    stem = basename.rsplit(".", 1)[0] if "." in basename else basename
    return stem in _ENTRY_POINT_STEMS


def _count_languages(files: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for f in files:
        counts[f.get("language", "other")] += 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def _build_directory_tree(files: list[dict], repo_name: str) -> str:
    top_dirs: dict[str, dict] = {}
    top_files: list[str] = []

    for f in files:
        parts = f["path"].split("/")
        if len(parts) == 1:
            top_files.append(parts[0])
        else:
            d = parts[0]
            if d not in top_dirs:
                top_dirs[d] = {"files": set(), "dirs": set()}
            if len(parts) == 2:
                top_dirs[d]["files"].add(parts[1])
            else:
                top_dirs[d]["dirs"].add(parts[1])

    lines = [f"{repo_name}/"]
    all_entries = sorted(top_dirs) + sorted(set(top_files))

    for i, entry in enumerate(all_entries):
        is_last = i == len(all_entries) - 1
        connector = "└── " if is_last else "├── "
        child_indent = "    " if is_last else "│   "

        if entry in top_dirs:
            lines.append(f"{connector}{entry}/")
            d = top_dirs[entry]
            # dirs first, then files — mirrors how `tree` renders it
            children = sorted(d["dirs"]) + sorted(d["files"])
            for j, child in enumerate(children):
                is_last_child = j == len(children) - 1
                child_conn = "└── " if is_last_child else "├── "
                suffix = "/" if child in d["dirs"] else ""
                lines.append(f"{child_indent}{child_conn}{child}{suffix}")
        else:
            lines.append(f"{connector}{entry}")

    if len(lines) > _TREE_MAX_LINES:
        extra = len(lines) - (_TREE_MAX_LINES - 1)
        lines = lines[: _TREE_MAX_LINES - 1]
        lines.append(f"... ({extra} more)")

    return "\n".join(lines)


def _find_entry_points(files: list[dict]) -> list[str]:
    return [f["path"] for f in files if _is_entry_point(f["path"])]


def _find_key_files(files: list[dict]) -> list[str]:
    scores: dict[str, int] = {}
    for f in files:
        basename = f["path"].split("/")[-1]
        stem = basename.rsplit(".", 1)[0] if "." in basename else basename
        if len(stem) <= 3 or stem.lower() in COMMON_NAME_STOPLIST:
            continue
        pat = re.compile(r"\b" + re.escape(stem) + r"\b")
        scores[f["path"]] = sum(
            1 for other in files
            if other["path"] != f["path"] and pat.search(other["content"])
        )
    return sorted(scores, key=lambda p: -scores[p])[:10]


def _detect_top_deps(files: list[dict]) -> list[str]:
    deps: list[str] = []
    for f in files:
        name = f["path"].split("/")[-1].lower()
        if name == "requirements.txt":
            for line in f["content"].splitlines():
                line = line.strip()
                if line and not line.startswith(("#", "-")):
                    pkg = re.split(r"[>=<!;\[]", line)[0].strip()
                    if pkg:
                        deps.append(pkg)
        elif name == "package.json":
            try:
                data = json.loads(f["content"])
                all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                deps.extend(all_deps.keys())
            except Exception:
                pass

    seen: set[str] = set()
    result: list[str] = []
    for d in deps:
        if d.lower() not in seen:
            seen.add(d.lower())
            result.append(d)
        if len(result) >= 8:
            break
    return result


def _build_summary_text(
    owner: str,
    name: str,
    languages: dict[str, int],
    file_count: int,
    entry_points: list[str],
    deps: list[str],
    trimmed: bool,
    trimmed_count: int,
) -> str:
    primary_lang = next(iter(languages), "unknown")
    lang_count = len(languages)

    lines = [
        f"{name} is a {primary_lang} repository owned by {owner}.",
        f"It contains {file_count} source files spanning {lang_count} language(s).",
    ]

    if lang_count > 1:
        breakdown = ", ".join(f"{lang} ({cnt})" for lang, cnt in list(languages.items())[:5])
        lines.append(f"Language breakdown: {breakdown}.")

    if deps:
        lines.append(f"Key dependencies/frameworks detected: {', '.join(deps[:6])}.")

    if entry_points:
        lines.append(f"Entry points: {', '.join(entry_points[:5])}.")
    else:
        lines.append("No standard entry points detected.")

    if trimmed:
        lines.append(
            f"Note: {trimmed_count} file(s) were dropped to fit the analysis budget."
        )

    lines.append(
        "Refer to the directory tree and key files listed above when answering questions about this repo."
    )

    return "\n".join(lines)


def build_repo_summary(loader_output: dict) -> dict:
    """
    Args:
        loader_output: full return value of github_loader.load_repo()

    Returns:
        {
            "repo_id": str,
            "owner": str,
            "name": str,
            "default_branch": str,
            "file_count": int,
            "total_bytes": int,
            "trimmed": bool,
            "trimmed_count": int,
            "languages": dict[str, int],          # {language: file_count}, sorted desc
            "directory_tree": str,                 # text rendering, max ~30 lines
            "entry_points": list[str],             # paths matching entry-point patterns
            "key_files": list[str],                # top 10 most-referenced files (basename match)
            "summary_text": str,                   # 5-8 line plain-English summary for Bob
        }
    """
    files: list[dict] = loader_output["files"]
    owner: str = loader_output["owner"]
    name: str = loader_output["name"]
    trimmed: bool = loader_output["trimmed"]
    trimmed_count: int = loader_output["trimmed_count"]

    languages = _count_languages(files)
    entry_points = _find_entry_points(files)
    key_files = _find_key_files(files)
    deps = _detect_top_deps(files)

    return {
        "repo_id": loader_output["repo_id"],
        "owner": owner,
        "name": name,
        "default_branch": loader_output["default_branch"],
        "file_count": len(files),
        "total_bytes": sum(f["size"] for f in files),
        "trimmed": trimmed,
        "trimmed_count": trimmed_count,
        "languages": languages,
        "directory_tree": _build_directory_tree(files, name),
        "entry_points": entry_points,
        "key_files": key_files,
        "summary_text": _build_summary_text(
            owner, name, languages, len(files),
            entry_points, deps, trimmed, trimmed_count,
        ),
    }


if __name__ == "__main__":
    fake_loader_output = {
        "repo_id": "abc123def456",
        "repo_url": "https://github.com/acme/myapp",
        "owner": "acme",
        "name": "myapp",
        "default_branch": "main",
        "trimmed": False,
        "trimmed_count": 0,
        "files": [
            {
                "path": "app.py",
                "content": "from utils import helper\nfrom models import User\n",
                "language": "python",
                "size": 50,
            },
            {
                "path": "utils/helper.py",
                "content": "def helper():\n    pass\n",
                "language": "python",
                "size": 30,
            },
            {
                "path": "models/user.py",
                "content": "class User:\n    pass\n",
                "language": "python",
                "size": 25,
            },
            {
                "path": "requirements.txt",
                "content": "fastapi>=0.100\nuvicorn\nhttpx\n",
                "language": "other",
                "size": 35,
            },
            {
                "path": "README.md",
                "content": "# myapp\nA simple app using helper and User.\n",
                "language": "markdown",
                "size": 45,
            },
        ],
    }

    import pprint
    result = build_repo_summary(fake_loader_output)
    pprint.pprint({k: v for k, v in result.items() if k != "summary_text"})
    print("\n--- summary_text ---")
    print(result["summary_text"])
    print("\n--- directory_tree ---")
    print(result["directory_tree"])

    assert "repo_id" in result
    assert "myapp" in result["summary_text"]
    assert "python" in result["summary_text"]
    assert result["file_count"] == 5
    assert "app.py" in result["entry_points"]
    print("\nAll assertions passed.")
