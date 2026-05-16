import os

from langchain_ibm import ChatWatsonx
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

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


def _get_model() -> ChatWatsonx:
    return ChatWatsonx(
        model_id=os.environ.get("WATSONX_MODEL_ID", "ibm/granite-8b-code-instruct"),
        url=os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
        project_id=os.environ["WATSONX_PROJECT_ID"],
        apikey=os.environ["WATSONX_API_KEY"],
        params={"max_new_tokens": 1024, "temperature": 0.1},
    )


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

    context_text = "\n\n".join(_format_chunk(c) for c in chunks)
    system_content = (
        f"{repo_summary['summary_text']}\n\n"
        f"Code context:\n{context_text}\n\n"
        f"{_SYSTEM_SUFFIX}"
    )

    lc_messages = [SystemMessage(content=system_content)]
    for msg in trimmed_history:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        else:
            lc_messages.append(AIMessage(content=msg["content"]))
    lc_messages.append(HumanMessage(content=question))

    response = _get_model().invoke(lc_messages)

    sources = [
        {
            "path": c["path"],
            "start_line": c["start_line"],
            "end_line": c["end_line"],
            "score": c["score"],
        }
        for c in chunks
    ]

    return {
        "answer": response.content,
        "sources": sources,
        "is_location_question": is_location_question,
    }
