# RepoSense — Opus Briefing Prompt

> Copy everything below this line and paste it to Claude Opus in Claude Code.

---

## Who you are and what your job is

You are Claude Opus, acting as the **Planner** in a Planner/Executor workflow.

Your job is to:
1. Read and fully understand this briefing
2. Audit the existing files in this codebase (README.md, ARCHITECTURE.md)
3. Ask me about **anything that is vague, missing, or that requires a decision** — never assume
4. Once you have full clarity, produce a complete, ordered list of **Sonnet execution prompts** stored in a file called `SONNET_PROMPTS.md`

Each Sonnet prompt must be:
- Self-contained (Sonnet has no memory of previous prompts)
- Scoped to one focused task
- Explicit about inputs, outputs, file names, and behavior
- Ordered so each prompt builds on the previous one

Do not write any code yourself. Do not make architectural decisions without asking me first.

---

## The Project

**Name:** RepoSense
**Event:** IBM Bob Hackathon — lablab.ai (May 15–17, 2026)
**Format:** 48-hour online solo build
**Prize pool:** $10,000 ($5K / $3K / $2K)
**Constraint:** Must meaningfully use IBM Bob in the solution

---

## What RepoSense does

RepoSense is an AI-powered developer tool. The user pastes a GitHub repository URL. RepoSense ingests the full codebase using IBM Bob's repository context understanding, and gives the user two things:

### Module A — Repo Intelligence (Q&A)
A conversational interface where the user can ask anything about the codebase.

- Questions like: "Where is authentication handled?", "How is user data processed?", "What does this service depend on?"
- Answers must be **concise and straight to the point** — no AI filler, no padding
- File path citations included **only when the question is location-specific** (contains: where, which file, find, locate, path)
- Code snippets shown inline when directly relevant to the answer
- Conversation history is maintained within the session
- IBM Bob is the reasoning engine — it receives the question + retrieved chunks + repo summary

### Module B — Automated Risk Review
An automated scan of the repository that produces a risk report and a risk score.

**What it detects:**
- **Untested functions:** a function is untested if no test file (file with "test" in its name or path) references its name
- **Breaking points:** functions or classes referenced in 5+ other files = high fan-out = high risk if changed
- **Security smells:** hardcoded secrets/tokens, SQL injection patterns, unvalidated user inputs, insecure HTTP usage, exposed sensitive routes

**Output:**
- A **dashboard** (Streamlit UI) showing findings with a big Risk Score metric
- A **downloadable Markdown report**

**Risk Score formula (0–100):**
- `coverage_score * 0.4 + complexity_score * 0.3 + security_score * 0.3`
- `coverage_score` = (tested_functions / total_functions) * 100
- `complexity_score` = 100 - min(100, avg_fan_out * 10)
- `security_score` = 100 - min(100, high_sev*20 + med_sev*10 + low_sev*5)

**Zero-test repos:** flag prominently AND still compute a partial score (security + complexity still run). Score reflects 0% coverage explicitly.

---

## Who it's for

- New developers onboarding to an unfamiliar codebase
- Senior developers reviewing PRs for risk
- Startup teams shipping fast who need a quick repo health check

---

## The Wow Factor

The single feature that makes judges go "damn":

> **The Risk Score** — a single 0–100 number shown immediately after ingestion, computed across test coverage, code complexity, and security. It's the first thing the user sees after the repo is loaded.

---

## Technical Decisions (already made — do not change without asking)

| Decision | Choice |
|---|---|
| Backend | Python + FastAPI |
| AI partner | IBM Bob (API key + base URL provided at hackathon kickoff) |
| RAG / vector store | LangChain + ChromaDB (local) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 (free, local) |
| GitHub integration | PyGithub |
| UI | Streamlit |
| Repo support | Public by default, private with user-supplied GitHub token |
| Language support | Any language — IBM Bob handles language-agnostic reasoning |
| Large repos | Handle silently with smart chunking — prioritize entry points and high-import files, trim least-referenced files. Never reject a repo. |
| Zero-test repos | Flag clearly in report + still compute partial score |
| Report output | Dashboard (Streamlit) + downloadable Markdown |
| Internal data format | JSON between modules |
| Session state | In-memory (stateless per session, no database persistence) |

---

## Architecture Overview

```
GitHub URL input
      ↓
Ingestion Layer (github_loader → chunker → embedder → context_builder)
      ↓
      ├── Module A: Q&A Engine (RAG + IBM Bob) → Chat UI
      └── Module B: Risk Review (risk_analyzer + security_scanner + report_generator) → Dashboard + Report
            ↓
      FastAPI Backend (/ingest  /ask  /review)
            ↓
      Streamlit UI
```

### Folder structure

```
reposense/
├── README.md
├── ARCHITECTURE.md
├── OPUS_BRIEFING.md
├── SONNET_PROMPTS.md          ← you will create this
├── requirements.txt
├── .env.example
│
├── ingestion/
│   ├── github_loader.py       # Fetch repo files via GitHub API
│   ├── chunker.py             # Split code into semantic chunks
│   └── embedder.py            # Embed chunks into ChromaDB
│
├── intelligence/
│   ├── context_builder.py     # Build repo summary for Bob
│   └── qa_engine.py           # RAG Q&A pipeline with IBM Bob
│
├── review/
│   ├── risk_analyzer.py       # Untested functions + breaking points
│   ├── security_scanner.py    # Security smells via IBM Bob
│   └── report_generator.py    # Risk score + Markdown report
│
├── api/
│   ├── main.py                # FastAPI app
│   └── routes/
│       ├── ingest.py          # POST /ingest
│       ├── qa.py              # POST /ask
│       └── review.py          # GET /review
│
├── ui/
│   └── app.py                 # Streamlit UI
│
└── demo/
    ├── DEMO_SCRIPT.md
    └── demo_repos.md
```

---

## User Flow (step by step)

1. User opens the Streamlit app
2. Pastes a GitHub repo URL in the sidebar
3. Optionally toggles "Private repo" and enters a GitHub token
4. Clicks "Ingest" → spinner shows while ingestion runs
5. After ingestion: **Risk Score appears immediately** as a large metric
6. User is now in the "Ask" tab — can start asking questions
7. User switches to "Risk Review" tab to see full breakdown
8. User downloads the Markdown report

---

## Edge Cases (must be handled)

| Edge case | Expected behavior |
|---|---|
| Invalid GitHub URL | Clear ValueError with human-readable message |
| Private repo without token | Raise with: "This repo is private. Please provide a GitHub token." |
| GitHub API rate limit hit | Wait and retry once, then raise with clear message |
| Repo already ingested | Return cached retriever, skip re-embedding |
| IBM Bob API error or timeout | Return graceful fallback message, never expose stack trace |
| Zero test files in repo | coverage_score = 0, flag "no_tests_detected": true, still run security + complexity |
| Zero detectable functions (config-only repo) | coverage_score = null, flag "no_functions_detected": true |
| Security scanner returns malformed JSON | Log warning, return empty findings list, continue |
| Unknown repo_id in API call | Return 404 with {error: "Repo not found. Please ingest first."} |
| Large repo (> 2MB content) | Silently prioritize entry points and high-import files, trim least-referenced |

---

## Hard Constraints (never violate)

- ⛔ No auth system, no user accounts, no database persistence
- ⛔ No IDE plugin, no CLI tool, no GitHub App — web UI only
- ⛔ No real-time collaboration features
- ⚡ Must be fully demo-ready in 48 hours
- 🧑‍💻 Solo dev — keep infra minimal (FastAPI + ChromaDB local + Streamlit)
- 💸 No paid services beyond IBM Bob (which is provided)

---

## What IBM Bob is

IBM Bob is an AI-powered development partner that operates with **full repository context**. It can:
- Understand how an entire codebase is structured
- Reason through logic and dependencies
- Navigate complex codebases
- Automate multi-step development workflows

Bob is accessed via a REST API (base URL + API key provided at hackathon kickoff on May 15). Until then, the code should be structured so Bob's API call is isolated in one place and easy to swap in.

Bob is used in two places:
1. `qa_engine.py` — for answering user questions about the repo
2. `security_scanner.py` — for detecting security smells across the codebase

---

## Your instructions

1. **Read README.md and ARCHITECTURE.md** in this repo first
2. **Identify anything vague, missing, or requiring a decision** — list them and ask me before proceeding
3. **Do not assume anything** — if you are unsure about a behavior, an edge case, an API shape, or an architectural choice, ask
4. Once you have full clarity, **produce SONNET_PROMPTS.md** with a numbered, ordered list of Sonnet execution prompts
5. Each prompt must be fully self-contained — Sonnet has no memory between prompts
6. Each prompt must reference the specific files it touches and the exact behavior expected
7. Order the prompts so each one can be executed cleanly on top of the previous one's output

Start by reading the existing files, then tell me what you understand and what you need clarified.
