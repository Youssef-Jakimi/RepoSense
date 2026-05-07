# RepoSense — Sonnet Execution Prompts

> Ordered, self-contained prompts for Claude Sonnet (Executor). Run them one at a time, in order. Each prompt is fully self-contained — Sonnet has no memory between prompts.
>
> **How to use this file:** Copy each numbered prompt block (everything between `---START PROMPT N---` and `---END PROMPT N---`) and paste it into a fresh Sonnet session. Wait for completion, sanity-check the output, then move to the next.
>
> Every prompt instructs Sonnet to read `OPUS_BRIEFING.md`, `README.md`, and `ARCHITECTURE.md` first — those three files are the durable source of truth for the project.

---

## Prompt index

1. Align stale docs (README.md, ARCHITECTURE.md) with the briefing
2. Scaffold project structure (folders, `requirements.txt`, `.env.example`)
3. Build `ingestion/github_loader.py`
4. Build `ingestion/chunker.py`
5. Build `ingestion/embedder.py`
6. Build `intelligence/context_builder.py`
7. Build state store + `intelligence/qa_engine.py`
8. Build `review/risk_analyzer.py`
9. Build `review/security_scanner.py`
10. Build `review/report_generator.py`
11. FastAPI app skeleton + `/ingest` + `/status` (background task pipeline)
12. FastAPI `/ask` + `/review` routes
13. Streamlit UI (`ui/app.py`)
14. Smoke scripts (`scripts/smoke_ingest.py`, `scripts/smoke_review.py`)
15. Demo materials (`demo/DEMO_SCRIPT.md`, `demo/demo_repos.md`)
16. Final integration pass — error handling polish, run instructions, end-to-end test

---

---START PROMPT 1---



---END PROMPT 1---

---

---START PROMPT 2---



---END PROMPT 2---

---

---START PROMPT 3---



---END PROMPT 3---

---

---START PROMPT 4---


---END PROMPT 4---

---

---START PROMPT 5---


---END PROMPT 5---

---

---START PROMPT 6---


---END PROMPT 6---

---

---START PROMPT 7---



---END PROMPT 7---

---

---START PROMPT 8---


---END PROMPT 8---

---

---START PROMPT 9---


---END PROMPT 9---

---

---START PROMPT 10---


---END PROMPT 10---

---

---START PROMPT 11---


---END PROMPT 11---

---

---START PROMPT 12---

---END PROMPT 12---

---

---START PROMPT 13---


---END PROMPT 13---

---

---START PROMPT 14---


---END PROMPT 14---

---

---START PROMPT 15---


---END PROMPT 15---

---

---START PROMPT 16---


---END PROMPT 16---

---

## After all 16 prompts

You will have:
- All implementation files for ingestion, intelligence, review, api, ui
- Working FastAPI backend with `/ingest`, `/status`, `/ask`, `/review`
- Streamlit UI with Risk Score, Ask tab, Risk Review tab, Markdown download
- Two smoke scripts to verify the pipeline outside the API
- Demo materials ready for the hackathon submission
- Clear `IBM Bob TODO` markers in `qa_engine.py` and `security_scanner.py` ready to wire on May 15

**Day-of-hackathon work (May 15):** wire IBM Bob into the two TODO sites, verify against real Bob endpoints, re-record the demo with grounded answers and Bob-enriched security findings.

---
