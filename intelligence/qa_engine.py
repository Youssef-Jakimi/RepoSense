import os

_LOCATION_KEYWORDS = {"where", "which file", "find", "locate", "path", "directory"}

_SYSTEM_SUFFIX = (
    "Answer concisely and directly. No filler. "
    "If the question asks where something is, cite file paths. "
    "If a code snippet is directly relevant, include it inline. "
    "Otherwise, do not show code."
)


def _detect_location_question(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in _LOCATION_KEYWORDS)


def _format_chunk(chunk: dict) -> str:
    return f"[file: {chunk['path']}, lines {chunk['start_line']}-{chunk['end_line']}]\n{chunk['content']}"


def answer_question(
    question: str,
    retriever,
    repo_summary: dict,
    history: list[dict],
    top_k: int = 6,
) -> dict:
    """
    Returns:
        {
            "answer": str,
            "sources": list[{"path": str, "start_line": int, "end_line": int, "score": float}],
            "is_location_question": bool,
        }
    """
    chunks = retriever.search(question, top_k=top_k)

    is_location_question = _detect_location_question(question)

    trimmed_history = history[-10:]

    system_prompt = f"{repo_summary['summary_text']}\n\n{_SYSTEM_SUFFIX}"

    context_text = "\n\n".join(_format_chunk(c) for c in chunks)

    messages = trimmed_history + [{"role": "user", "content": question}]

    sources = [
        {
            "path": c["path"],
            "start_line": c["start_line"],
            "end_line": c["end_line"],
            "score": c["score"],
        }
        for c in chunks
    ]

    try:
        # TODO: implement Bob API call
        # Expected request shape (to be confirmed at hackathon kickoff May 15):
        #   POST {IBM_BOB_BASE_URL}/...
        #   Headers: {"Authorization": f"Bearer {IBM_BOB_API_KEY}"}
        #   Body: {"system": str, "messages": list[{role, content}], "context": str}
        # Expected response: {"answer": str}
        raise NotImplementedError("IBM Bob API call not yet wired — see TODO above")
    except NotImplementedError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Bob API call failed: {exc}") from exc

    return {  # noqa: unreachable — placeholder for post-Bob wiring
        "answer": answer,
        "sources": sources,
        "is_location_question": is_location_question,
    }
