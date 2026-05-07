from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api import state

router = APIRouter()


class StatusResponse(BaseModel):
    repo_id: str
    status: str
    risk_score: float | None = None
    error: str | None = None


@router.get("/status", response_model=StatusResponse)
def get_status(repo_id: str) -> StatusResponse:
    if not state.exists(repo_id):
        raise HTTPException(status_code=404, detail="repo_id not found")

    s = state.get(repo_id)
    return StatusResponse(
        repo_id=repo_id,
        status=s.status,
        risk_score=s.risk_score,
        error=s.error,
    )
