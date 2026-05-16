"""RepoSense — Streamlit UI"""
from __future__ import annotations

import os
import time

import httpx
import pandas as pd
import streamlit as st

API_BASE = os.getenv("REPOSENSE_API_BASE", "http://localhost:8000")
_TIMEOUT = 30.0       # fast ops: ingest trigger, status poll
_LLM_TIMEOUT = 120.0  # slow ops: /ask, /review (LLM generation)

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def api_post(path: str, payload: dict, timeout: float = _TIMEOUT) -> dict:
    try:
        r = httpx.post(f"{API_BASE}{path}", json=payload, timeout=timeout)
        if not r.is_success:
            raise RuntimeError(r.text)
        return r.json()
    except httpx.TimeoutException:
        raise RuntimeError(f"API timeout — is the backend running on {API_BASE}?")


def api_get(path: str, params: dict | None = None, timeout: float = _TIMEOUT) -> dict | str:
    try:
        r = httpx.get(f"{API_BASE}{path}", params=params or {}, timeout=timeout)
        if not r.is_success:
            raise RuntimeError(r.text)
        if "json" in r.headers.get("content-type", ""):
            return r.json()
        return r.text
    except httpx.TimeoutException:
        raise RuntimeError(f"API timeout — is the backend running on {API_BASE}?")


# ---------------------------------------------------------------------------
# Page config — must be the first Streamlit call
# ---------------------------------------------------------------------------

st.set_page_config(page_title="RepoSense", page_icon="🧠", layout="wide")

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------

for _k, _v in {
    "repo_id": None,
    "status": "idle",
    "report": None,
    "messages": [],
    "error": None,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🧠 RepoSense")
    st.caption("AI-powered repo risk analysis")

    repo_url = st.text_input("Repo URL", placeholder="https://github.com/owner/repo")
    is_private = st.checkbox("Private repo")
    github_token: str | None = None
    if is_private:
        github_token = st.text_input("GitHub Token", type="password") or None

    ingest_btn = st.button("Ingest", type="primary", use_container_width=True)

    if ingest_btn:
        if not repo_url:
            st.warning("Please enter a repo URL.")
        elif is_private and not github_token:
            st.warning("Private repo selected but no GitHub token provided.")
        else:
            st.session_state.update(
                repo_id=None, status="idle", report=None, messages=[], error=None
            )
            try:
                result = api_post("/ingest", {"repo_url": repo_url, "github_token": github_token})
                st.session_state.repo_id = result["repo_id"]
                st.session_state.status = result["status"]
            except RuntimeError as exc:
                st.session_state.error = str(exc)
                st.session_state.status = "error"

    # Status indicator
    st.divider()
    _status = st.session_state.status
    if _status == "idle":
        st.info("Status: idle")
    elif _status == "ingesting":
        st.warning("⏳ Status: Ingesting…")
    elif _status == "reviewing":
        st.warning("🧪 Status: Reviewing…")
    elif _status == "ready":
        st.success("✅ Status: Ready")
        if repo_url:
            st.caption(f"Repo: `{repo_url.removeprefix('https://github.com/')}`")
    elif _status == "error":
        st.error(f"❌ Error: {st.session_state.error or 'unknown'}")

# ---------------------------------------------------------------------------
# Polling while ingesting / reviewing
# ---------------------------------------------------------------------------

if st.session_state.status in ("ingesting", "reviewing") and st.session_state.repo_id:
    _poll_msg = (
        "⏳ Ingesting repository…"
        if st.session_state.status == "ingesting"
        else "🧪 Running risk review…"
    )
    with st.spinner(_poll_msg):
        time.sleep(2)
        try:
            _poll = api_get("/status", {"repo_id": st.session_state.repo_id})
            assert isinstance(_poll, dict)
            st.session_state.status = _poll["status"]
            if _poll.get("error"):
                st.session_state.error = _poll["error"]
        except RuntimeError as exc:
            st.session_state.error = str(exc)
            st.session_state.status = "error"
    st.rerun()

# ---------------------------------------------------------------------------
# Fetch report once when status transitions to ready
# ---------------------------------------------------------------------------

if (
    st.session_state.status == "ready"
    and st.session_state.report is None
    and st.session_state.repo_id
):
    try:
        _fetched = api_get("/review", {"repo_id": st.session_state.repo_id}, timeout=_LLM_TIMEOUT)
        assert isinstance(_fetched, dict)
        st.session_state.report = _fetched
    except RuntimeError as exc:
        st.error(str(exc))

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

if st.session_state.status == "ready" and st.session_state.report is not None:
    report = st.session_state.report
    scores = report["scores"]
    summary = report["summary"]

    # Risk score + sub-scores
    c_main, c_cov, c_cmp, c_sec = st.columns([2, 1, 1, 1])
    with c_main:
        st.metric("📊 Risk Score", f"{report['risk_score']}/100")
    with c_cov:
        _cov = scores["coverage_score"]
        st.metric("Coverage", f"{_cov}/100" if _cov is not None else "N/A")
    with c_cmp:
        st.metric("Complexity", f"{scores['complexity_score']}/100")
    with c_sec:
        st.metric("Security", f"{scores['security_score']}/100")

    st.divider()

    tab_ask, tab_review = st.tabs(["💬 Ask", "🔍 Risk Review"])

    # ------------------------------------------------------------------
    # Tab: Ask
    # ------------------------------------------------------------------
    with tab_ask:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and msg.get("sources"):
                    _srcs = msg["sources"]
                    if msg.get("is_location_question"):
                        st.caption("**Sources:**")
                        for s in _srcs:
                            st.caption(
                                f"📄 `{s['path']}` lines {s['start_line']}–{s['end_line']}"
                            )
                    else:
                        with st.expander("Sources"):
                            for s in _srcs:
                                st.caption(
                                    f"📄 `{s['path']}` lines {s['start_line']}–{s['end_line']}"
                                )

        question = st.chat_input("Ask anything about the repo…")
        if question:
            st.session_state.messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    try:
                        resp = api_post(
                            "/ask",
                            {"repo_id": st.session_state.repo_id, "question": question},
                            timeout=_LLM_TIMEOUT,
                        )
                        answer = resp["answer"]
                        sources = resp["sources"]
                        is_loc = resp["is_location_question"]

                        st.markdown(answer)
                        if sources:
                            if is_loc:
                                st.caption("**Sources:**")
                                for s in sources:
                                    st.caption(
                                        f"📄 `{s['path']}` lines {s['start_line']}–{s['end_line']}"
                                    )
                            else:
                                with st.expander("Sources"):
                                    for s in sources:
                                        st.caption(
                                            f"📄 `{s['path']}` lines {s['start_line']}–{s['end_line']}"
                                        )

                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": answer,
                                "sources": sources,
                                "is_location_question": is_loc,
                            }
                        )
                    except RuntimeError as exc:
                        st.error(str(exc))

    # ------------------------------------------------------------------
    # Tab: Risk Review
    # ------------------------------------------------------------------
    with tab_review:
        if summary["no_tests_detected"]:
            st.warning("⚠️ No test files detected — coverage score is 0%.")
        if not summary["bob_enrichment_available"]:
            st.warning(
                "⚠️ IBM Bob enrichment was unavailable — security findings are regex-only (preliminary)."
            )

        # Untested functions
        st.subheader("Untested Functions")
        _untested = report["untested_functions"][:20]
        if _untested:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Function": f["name"],
                            "File": f["path"],
                            "Line": f["line"],
                            "Language": f["language"],
                            "Detection": f["detection_method"],
                        }
                        for f in _untested
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("No untested functions detected. ✅")

        # Breaking points
        st.subheader("Breaking Points")
        _bps = report["breaking_points"][:10]
        if _bps:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Function": b["name"],
                            "File": b["path"],
                            "Line": b["line"],
                            "Fan-Out": b["fan_out"],
                        }
                        for b in _bps
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("No breaking points detected. ✅")

        # Security findings
        _SEV_EMOJI = {"high": "🔴", "medium": "🟠", "low": "🟡"}
        st.subheader("Security Findings")
        _findings = report["security_findings"][:20]
        if _findings:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Severity": f"{_SEV_EMOJI.get(f['severity'], '')} {f['severity'].upper()}",
                            "Pattern": f["pattern_matched"],
                            "File": f["file_path"],
                            "Line": f["line"],
                            "Description": f["description"],
                            "Bob Enriched": "✅" if f.get("bob_enriched") else "❌",
                        }
                        for f in _findings
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("No security findings detected. ✅")

        # Recommendations
        st.subheader("Recommendations")
        for _i, _rec in enumerate(report["recommendations"], 1):
            st.markdown(f"{_i}. {_rec}")

        # Download markdown report
        st.divider()
        try:
            _md = api_get(
                "/review",
                {"repo_id": st.session_state.repo_id, "format": "markdown"},
                timeout=_LLM_TIMEOUT,
            )
            assert isinstance(_md, str)
            st.download_button(
                "📄 Download Markdown Report",
                data=_md,
                file_name=f"reposense_report_{st.session_state.repo_id}.md",
                mime="text/markdown",
            )
        except RuntimeError as exc:
            st.error(f"Could not fetch markdown report: {exc}")

elif st.session_state.status == "error":
    st.error(f"❌ {st.session_state.error or 'An error occurred.'}")
elif st.session_state.status == "idle":
    st.info("Enter a GitHub repo URL in the sidebar and click **Ingest** to get started.")
