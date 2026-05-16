import hashlib
import logging
import os

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from api import state
from api.state import RepoState
from ingestion import github_loader, chunker, embedder
from intelligence import context_builder
from review import risk_analyzer, security_scanner, report_generator

logger = logging.getLogger(__name__)

router = APIRouter()


class IngestRequest(BaseModel):
    repo_url: str
    github_token: str | None = None


class IngestResponse(BaseModel):
    repo_id: str
    status: str


def _run_pipeline(repo_id: str, repo_url: str, token: str | None) -> None:
    s = state.get(repo_id)
    try:
        # Stage 1: ingestion
        logger.info("[%s] Stage 1/4: loading repo from GitHub", repo_id)
        loader_output = github_loader.load_repo(repo_url, github_token=token)
        s.files = loader_output["files"]
        if not s.files:
            raise ValueError(
                "No source files found in this repository. "
                "RepoSense supports Python, JS/TS, Go, Java, Rust, Ruby, C/C++, and more. "
                "Check that the repo contains code files and is not empty."
            )
        s.summary = context_builder.build_repo_summary(loader_output)
        logger.info("[%s] Stage 2/4: chunking and embedding %d files", repo_id, len(s.files))
        chunks = chunker.chunk_files(s.files)
        s.retriever = embedder.embed_chunks(repo_id, chunks)

        # Stage 2: review
        logger.info("[%s] Stage 3/4: running risk analysis", repo_id)
        s.status = "reviewing"
        risk = risk_analyzer.analyze_repo(s.files)
        logger.info("[%s] Stage 4/4: running security scan (IBM Bob enrichment)", repo_id)
        sec = security_scanner.scan_security(s.files)
        logger.info("[%s] Generating report (risk_score computation)", repo_id)
        report = report_generator.generate_report(s.summary, risk, sec)
        report["repo_id"] = repo_id
        s.report = report
        s.risk_score = report["risk_score"]

        s.status = "ready"
        logger.info("[%s] Pipeline complete — risk_score=%.1f, status=ready", repo_id, s.risk_score)
    except ValueError as e:
        logger.warning("[%s] Pipeline ValueError: %s", repo_id, e)
        s.status = "error"
        s.error = str(e)
    except Exception as e:
        s.status = "error"
        s.error = f"Pipeline failed: {type(e).__name__}: {e}"
        logger.exception("Pipeline failure for repo_id=%s", repo_id)


@router.post("/ingest", response_model=IngestResponse)
def ingest_repo(payload: IngestRequest, background: BackgroundTasks) -> IngestResponse:
    repo_id = hashlib.sha256(payload.repo_url.encode()).hexdigest()[:12]

    if state.exists(repo_id) and state.get(repo_id).status == "ready":
        return IngestResponse(repo_id=repo_id, status="ready")

    token = payload.github_token or os.getenv("GITHUB_TOKEN") or None

    fresh = RepoState(repo_id=repo_id, repo_url=payload.repo_url, status="ingesting")
    state.put(fresh)
    background.add_task(_run_pipeline, repo_id, payload.repo_url, token)

    return IngestResponse(repo_id=repo_id, status="ingesting")
