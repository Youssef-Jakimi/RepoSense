# RepoSense — 90-Second Demo Script

> **Total runtime: ~90 seconds.** Practice until the narration feels natural, not read.

---

## Setup (do this before hitting Record)

- Browser open at `http://localhost:8501` (Streamlit landing page visible)
- One or two additional browser tabs open with target repo URLs visible — no typing during the demo
- FastAPI backend running: `uvicorn api.main:app --reload` (Terminal 1)
- Streamlit running: `streamlit run ui/app.py` (Terminal 2)
- `.env` filled in with IBM Bob API key and base URL (provided at hackathon kickoff, May 15)
- Demo repo pre-cloned locally as a fallback if GitHub API is slow during recording

---

## Beat-by-Beat Narration

| Time | Visual | Spoken script |
|---|---|---|
| 0:00–0:08 | Streamlit landing page — URL input field and Ingest button visible | "This is RepoSense. Drop in any GitHub repo, get understanding and risk in one shot." |
| 0:08–0:18 | Switch to the prepared tab, copy the URL, paste it into the sidebar, click Ingest | "Let's try a real one — [repo name]. One URL. That's all it needs." |
| 0:18–0:35 | Spinner running → spinner disappears → big Risk Score metric appears | "In under 30 seconds, RepoSense ingested the entire repo, computed a coverage score, a complexity score, and a security score — and collapsed them into a single number: [SCORE] out of 100." |
| 0:35–0:55 | Click the Ask tab, type the pre-prepared question, answer appears with file citations | "Now I can ask anything. 'Where is authentication handled?' Notice it cites the exact file and line — IBM Bob grounds every answer in the real code, not a hallucination." |
| 0:55–1:20 | Switch to Risk Review tab, scroll slowly through the findings | "Here's the breakdown: [X] untested functions, [Y] hardcoded secrets caught, [Z] high-fan-out functions that would ripple through the codebase if changed. Each one is actionable — not just a warning." |
| 1:20–1:30 | Click Download Markdown, file saves | "Full report exports as Markdown — drop it in a PR description, share it with the team. One URL in, repo understood and risk-scored." |

---

## Recording Tips

- **Mic check:** Record a 10-second test clip before starting; listen for background noise or peaking
- **Clean desktop:** Hide the taskbar, close any notification banners, set browser to full-screen or a clean profile
- **Close noisy tabs:** Disable browser notifications, mute all communication apps (Slack, email) before recording
- **Fallback plan:** Have the demo repo pre-cloned locally and the report JSON pre-generated — if GitHub is slow, switch to the fallback without breaking flow
- **One take is fine:** A single smooth 90-second cut is better than a heavily edited multi-take; re-record from the top if you stumble past 0:30
- **Cursor discipline:** Move the mouse deliberately and slowly — erratic cursor movement looks unprofessional on screen recordings

---

## Submission Checklist

- [ ] Demo video uploaded to the submission platform (lablab.ai) and link verified
- [ ] GitHub repository set to **public** before submission deadline
- [ ] README includes at least one screenshot of the Risk Score and the Ask tab
- [ ] Live demo URL included if a deployed instance is available
- [ ] IBM Bob usage clearly explained in the README: Q&A engine (`qa_engine.py`) and security scanner (`security_scanner.py`)
- [ ] `requirements.txt` and `.env.example` present so judges can run it locally
- [ ] Project description on lablab.ai matches the README (no conflicting claims)
