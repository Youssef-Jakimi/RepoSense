from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class RepoState:
    repo_id: str
    repo_url: str
    status: str = "ingesting"          # "ingesting" | "reviewing" | "ready" | "error"
    error: Optional[str] = None
    summary: Optional[dict] = None     # output of context_builder.build_repo_summary
    files: list[dict] = field(default_factory=list)  # raw files from loader (needed by risk_analyzer)
    retriever: Any = None              # ingestion.embedder.Retriever
    history: list[dict] = field(default_factory=list)  # [{role: "user"|"assistant", content: str}]
    report: Optional[dict] = None      # full risk report from report_generator
    risk_score: Optional[float] = None # convenience: report["risk_score"] surfaced for /status


_STORE: dict[str, RepoState] = {}


def get(repo_id: str) -> Optional[RepoState]:
    return _STORE.get(repo_id)


def put(state: RepoState) -> None:
    _STORE[state.repo_id] = state


def exists(repo_id: str) -> bool:
    return repo_id in _STORE


def all_ids() -> list[str]:
    return list(_STORE.keys())
