import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api import state
from intelligence import qa_engine

logger = logging.getLogger(__name__)

router = APIRouter()


class AskRequest(BaseModel):
    repo_id: str
    question: str


class Source(BaseModel):
    path: str
    start_line: int
    end_line: int
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    is_location_question: bool


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest) -> AskResponse:
    s = state.get(payload.repo_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Repo not found. Please ingest first.")

    if s.status != "ready":
        raise HTTPException(
            status_code=409,
            detail=f"Repo is still {s.status}. Try again in a few seconds.",
        )

    s.history.append({"role": "user", "content": payload.question})

    try:
        result = qa_engine.answer_question(
            payload.question, s.retriever, s.summary, s.history
        )
    except NotImplementedError:
        chunks = s.retriever.search(payload.question, top_k=6)
        sources = [
            Source(
                path=c["path"],
                start_line=c["start_line"],
                end_line=c["end_line"],
                score=c["score"],
            )
            for c in chunks
        ]
        return AskResponse(
            answer=(
                "IBM Bob is not yet connected. This will be enabled at hackathon kickoff. "
                "Retrieved sources are shown below."
            ),
            sources=sources,
            is_location_question=qa_engine._detect_location_question(payload.question),
        )
    except Exception as exc:
        err = str(exc)
        if "CannotSetProjectOrSpace" in type(exc).__name__ or "Cannot set Project or Space" in err or "404" in err:
            raise HTTPException(
                status_code=503,
                detail="watsonx project not found — check WATSONX_PROJECT_ID and WATSONX_API_KEY in your .env",
            )
        logger.exception("Unexpected error answering question for repo %s", payload.repo_id)
        raise HTTPException(
            status_code=500, detail="An error occurred answering the question."
        )

    s.history.append({"role": "assistant", "content": result["answer"]})
    s.history = s.history[-10:]

    return AskResponse(
        answer=result["answer"],
        sources=[Source(**src) for src in result["sources"]],
        is_location_question=result["is_location_question"],
    )
