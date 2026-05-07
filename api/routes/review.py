from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from api import state
from review import report_generator

router = APIRouter()


@router.get("/review")
def review(repo_id: str, format: str = "json") -> Response:
    s = state.get(repo_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Repo not found. Please ingest first.")

    if s.status != "ready":
        raise HTTPException(
            status_code=409,
            detail=f"Review not ready (status: {s.status}). Please wait.",
        )

    if s.report is None:
        raise HTTPException(
            status_code=500,
            detail="Report missing despite ready status — internal error.",
        )

    if format == "markdown":
        md = report_generator.render_markdown(s.report)
        return PlainTextResponse(
            content=md,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename=reposense_report_{repo_id}.md"
            },
        )

    return JSONResponse(content=s.report)
