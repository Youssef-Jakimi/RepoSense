import json
import logging
from typing import Optional

import tiktoken

logger = logging.getLogger(__name__)

_encoding = tiktoken.get_encoding("cl100k_base")

_CODE_LANGUAGES = {
    "python", "javascript", "typescript", "java", "go", "ruby",
    "rust", "c", "cpp", "csharp", "php", "swift", "kotlin", "scala",
}
_MARKUP_LANGUAGES = {"markdown", "rst"}
_CONFIG_LANGUAGES = {"json", "yaml", "toml", "ini"}


def _count_tokens(text: str) -> int:
    return len(_encoding.encode(text))


def _lines_of(text: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    # Ensure last line always has a newline for consistent joining
    return lines


def _line_range(full_lines: list[str], chunk_text: str, hint_start: int = 0) -> tuple[int, int]:
    """Find 1-indexed start/end line numbers of chunk_text within full_lines."""
    # Reconstruct from offset within the joined text
    full = "".join(full_lines)
    offset = full.find(chunk_text, hint_start)
    if offset == -1:
        # Fallback: search from beginning
        offset = full.find(chunk_text)
    if offset == -1:
        return 1, len(full_lines)

    start_line = full[:offset].count("\n") + 1
    end_line = start_line + chunk_text.count("\n") - (1 if chunk_text.endswith("\n") else 0)
    end_line = max(start_line, end_line)
    return start_line, end_line


def _build_chunk(path: str, language: str, content: str, index: int,
                 full_lines: list[str], search_from: int = 0) -> dict:
    start_line, end_line = _line_range(full_lines, content, search_from)
    return {
        "id": f"{path}::chunk_{index}",
        "path": path,
        "language": language,
        "content": content,
        "start_line": start_line,
        "end_line": end_line,
        "token_count": _count_tokens(content),
    }


def _split_long_line(line: str, target_tokens: int) -> list[str]:
    """Split a single very long line by character count as last resort."""
    if _count_tokens(line) <= target_tokens:
        return [line]
    # Approximate chars per token ~4
    char_budget = target_tokens * 4
    parts = []
    while line:
        parts.append(line[:char_budget])
        line = line[char_budget:]
    return parts


def _split_into_blocks(lines: list[str], target_tokens: int) -> list[str]:
    """Split lines into blank-line-separated logical blocks.

    If a block exceeds target_tokens, further splits it by individual lines.
    Returns list of text blocks (may or may not end with newline).
    """
    blocks: list[str] = []
    current: list[str] = []

    def flush(buf: list[str]) -> None:
        if not buf:
            return
        block = "".join(buf)
        if _count_tokens(block) <= target_tokens:
            blocks.append(block)
        else:
            # Fall back to line-by-line within this oversized block
            for ln in buf:
                if _count_tokens(ln) > target_tokens:
                    for part in _split_long_line(ln, target_tokens):
                        blocks.append(part)
                else:
                    blocks.append(ln)
        buf.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            current.append(line)
            flush(current)
        else:
            current.append(line)

    flush(current)
    return blocks


def _sliding_window(
    blocks: list[str],
    target_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    """Accumulate blocks into chunks using a sliding window with overlap."""
    chunks: list[str] = []
    current_blocks: list[str] = []
    current_tokens = 0

    for block in blocks:
        block_tokens = _count_tokens(block)
        if current_tokens + block_tokens > target_tokens and current_blocks:
            chunks.append("".join(current_blocks))
            # Build overlap: walk backward through current_blocks until we hit overlap budget
            overlap_blocks: list[str] = []
            overlap_count = 0
            for b in reversed(current_blocks):
                bt = _count_tokens(b)
                if overlap_count + bt > overlap_tokens:
                    break
                overlap_blocks.insert(0, b)
                overlap_count += bt
            current_blocks = overlap_blocks
            current_tokens = overlap_count

        current_blocks.append(block)
        current_tokens += block_tokens

    if current_blocks:
        chunks.append("".join(current_blocks))

    return chunks


def _chunk_code(path: str, language: str, lines: list[str],
                target_tokens: int, overlap_tokens: int) -> list[str]:
    blocks = _split_into_blocks(lines, target_tokens)
    return _sliding_window(blocks, target_tokens, overlap_tokens)


def _chunk_markup(path: str, lines: list[str],
                  target_tokens: int, overlap_tokens: int) -> list[str]:
    # Split by \n\n (paragraph) boundaries
    text = "".join(lines)
    raw_paragraphs = text.split("\n\n")
    # Re-add the separators so we can reconstruct accurately
    blocks = []
    for i, para in enumerate(raw_paragraphs):
        block = para + ("\n\n" if i < len(raw_paragraphs) - 1 else "")
        if block.strip():
            if _count_tokens(block) > target_tokens:
                # Fall back to line splitting within this paragraph
                for sub_line in block.splitlines(keepends=True):
                    if _count_tokens(sub_line) > target_tokens:
                        for part in _split_long_line(sub_line, target_tokens):
                            blocks.append(part)
                    else:
                        blocks.append(sub_line)
            else:
                blocks.append(block)
    return _sliding_window(blocks, target_tokens, overlap_tokens)


def _chunk_config_json(text: str, target_tokens: int, overlap_tokens: int) -> list[str]:
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return None  # type: ignore[return-value]
        blocks = []
        for key, value in data.items():
            segment = json.dumps({key: value}, indent=2)
            if _count_tokens(segment) > target_tokens:
                # Too big — emit as-is and let sliding window handle it
                blocks.append(segment + "\n")
            else:
                blocks.append(segment + "\n")
        return _sliding_window(blocks, target_tokens, overlap_tokens)
    except Exception:
        return None  # type: ignore[return-value]


def _chunk_config_ini_toml(text: str, target_tokens: int, overlap_tokens: int) -> Optional[list[str]]:
    """Split ini/toml by [section] headers."""
    lines = text.splitlines(keepends=True)
    sections: list[str] = []
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]") and current:
            sections.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("".join(current))

    if not sections:
        return None
    blocks = []
    for section in sections:
        if _count_tokens(section) > target_tokens:
            for ln in section.splitlines(keepends=True):
                blocks.append(ln)
        else:
            blocks.append(section)
    return _sliding_window(blocks, target_tokens, overlap_tokens)


def _chunk_config(path: str, language: str, lines: list[str],
                  target_tokens: int, overlap_tokens: int) -> list[str]:
    text = "".join(lines)
    total_tokens = _count_tokens(text)

    # Small config: emit as single chunk
    if total_tokens < 2 * target_tokens:
        return [text]

    result: Optional[list[str]] = None
    if language == "json":
        result = _chunk_config_json(text, target_tokens, overlap_tokens)
    elif language in ("ini", "toml"):
        result = _chunk_config_ini_toml(text, target_tokens, overlap_tokens)
    # yaml: no easy section splitter without a dep — fall through to line-based
    if result is None:
        blocks = _split_into_blocks(lines, target_tokens)
        result = _sliding_window(blocks, target_tokens, overlap_tokens)
    return result


def chunk_files(
    files: list[dict],
    target_tokens: int = 500,
    overlap_tokens: int = 50,
) -> list[dict]:
    """
    Split files into semantic chunks suitable for embedding.

    Args:
        files: Output of github_loader.load_repo()["files"], i.e.
               [{path, content, language, size}, ...]

    Returns:
        list of chunks: [
            {
                "id": str,             # f"{path}::chunk_{index}"
                "path": str,
                "language": str,
                "content": str,
                "start_line": int,     # 1-indexed inclusive
                "end_line": int,       # 1-indexed inclusive
                "token_count": int,
            },
            ...
        ]
    """
    result: list[dict] = []

    for file in files:
        path: str = file["path"]
        content: str = file.get("content", "")
        language: str = file.get("language", "other")

        if not content.strip():
            logger.debug("Skipping empty file: %s", path)
            continue

        total_tokens = _count_tokens(content)

        # Tiny file: single chunk regardless
        if total_tokens < 100:
            chunk = _build_chunk(path, language, content, 0, _lines_of(content))
            result.append(chunk)
            continue

        lines = _lines_of(content)

        if language in _CODE_LANGUAGES or language == "other":
            raw_chunks = _chunk_code(path, language, lines, target_tokens, overlap_tokens)
        elif language in _MARKUP_LANGUAGES:
            raw_chunks = _chunk_markup(path, lines, target_tokens, overlap_tokens)
        elif language in _CONFIG_LANGUAGES:
            raw_chunks = _chunk_config(path, language, lines, target_tokens, overlap_tokens)
        else:
            # Unknown: treat as code
            raw_chunks = _chunk_code(path, language, lines, target_tokens, overlap_tokens)

        search_offset = 0
        full_text = content
        for index, chunk_text in enumerate(raw_chunks):
            if not chunk_text.strip():
                continue
            chunk = _build_chunk(path, language, chunk_text, index, lines, search_offset)
            result.append(chunk)
            # Advance search offset past where we found this chunk
            found_at = full_text.find(chunk_text, search_offset)
            if found_at != -1:
                search_offset = found_at + len(chunk_text)

    return result
