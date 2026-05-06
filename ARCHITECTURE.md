# RepoSense — Architecture

## Overview

RepoSense is built as a modular AI pipeline with two core modules running on a shared ingestion layer powered by IBM Bob.

```
┌─────────────────────────────────────────────────────┐
│                    USER INPUT                        │
│              GitHub Repository URL                   │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│               INGESTION LAYER                        │
│                                                      │
│  1. GitHub API → fetch all repo files & metadata     │
│  2. Chunker   → split code into semantic chunks      │
│  3. Embedder  → embed chunks into vector store       │
│  4. IBM Bob   → analyze full repo context            │
│                                                      │
└──────────────┬──────────────────┬───────────────────┘
               │                  │
               ▼                  ▼
┌──────────────────┐   ┌──────────────────────────────┐
│  MODULE 1        │   │  MODULE 2                     │
│  Repo Q&A        │   │  Risk Review                  │
│                  │   │                               │
│  - RAG pipeline  │   │  - Untested function detector │
│  - IBM Bob QA    │   │  - Breaking point analysis    │
│  - Chat UI       │   │  - Security smell scanner     │
│                  │   │  - Structured report output   │
└──────────────────┘   └──────────────────────────────┘
               │                  │
               └────────┬─────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│                  FastAPI Backend                      │
│         /ingest    /ask    /review                   │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                  Streamlit UI                        │
│       Repo Input │ Chat Interface │ Risk Report      │
└─────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Ingestion Layer

**`ingestion/github_loader.py`**
- Accepts a GitHub repo URL
- Authenticates via GitHub API token
- Fetches all files (respects .gitignore patterns)
- Filters to relevant file types: `.py`, `.js`, `.ts`, `.java`, `.go`, `.md`, etc.
- Returns list of `{path, content, language}` objects

**`ingestion/chunker.py`**
- Splits files into semantic chunks (function-level for code, paragraph-level for docs)
- Preserves file path and language metadata per chunk
- Target chunk size: ~500 tokens with overlap

**`ingestion/embedder.py`**
- Embeds chunks using an embedding model
- Stores in ChromaDB vector store with metadata
- Returns a retriever interface for downstream modules

---

### 2. Module 1 — Repo Intelligence (Q&A)

**`intelligence/context_builder.py`**
- Builds a high-level repo summary for IBM Bob:
  - Directory structure
  - Entry points
  - Key dependencies
  - Language breakdown

**`intelligence/qa_engine.py`**
- RAG pipeline: user question → vector search → retrieve top-k chunks
- Sends retrieved context + question to IBM Bob
- Bob reasons over full context to give accurate, grounded answers
- Maintains conversation history for follow-up questions

**Flow:**
```
User Question
     │
     ▼
Vector Search (ChromaDB)
     │
     ▼
Top-K Relevant Chunks
     │
     ▼
IBM Bob (question + chunks + repo summary)
     │
     ▼
Grounded Answer
```

---

### 3. Module 2 — Automated Risk Review

**`review/risk_analyzer.py`**
- Scans all functions/methods in the codebase
- Checks for corresponding test files/functions
- Flags functions with no test coverage
- Detects high-dependency functions (breaking point risk)
- Uses IBM Bob to reason about logic complexity and interdependencies

**`review/security_scanner.py`**
- Prompts IBM Bob to detect common security smells:
  - Hardcoded secrets/credentials
  - SQL injection risks
  - Unvalidated inputs
  - Insecure dependencies
  - Exposed sensitive routes

**`review/report_generator.py`**
- Aggregates findings from risk_analyzer + security_scanner
- Outputs structured JSON report:
```json
{
  "summary": {
    "total_functions": 142,
    "untested": 38,
    "high_risk": 7,
    "security_issues": 3
  },
  "untested_functions": [...],
  "breaking_points": [...],
  "security_smells": [...],
  "recommendations": [...]
}
```

**Flow:**
```
Ingested Codebase
     │
     ├──► Risk Analyzer ──► Untested functions, breaking points
     │
     └──► Security Scanner ──► Security smells
               │
               ▼
         Report Generator
               │
               ▼
      Structured Risk Report
```

---

### 4. API Layer

**`api/main.py`** — FastAPI app with 3 routes:

| Route | Method | Input | Output |
|---|---|---|---|
| `/ingest` | POST | `{ "repo_url": "..." }` | `{ "status": "ready", "repo_id": "..." }` |
| `/ask` | POST | `{ "repo_id": "...", "question": "..." }` | `{ "answer": "...", "sources": [...] }` |
| `/review` | GET | `?repo_id=...` | Full risk report JSON |

---

### 5. UI Layer

**`ui/app.py`** — Streamlit app with 3 panels:

```
┌─────────────────────────────────────────────┐
│  🔗 GitHub Repo URL input + Ingest button   │
├────────────────────┬────────────────────────┤
│  🧠 Chat Interface │  🔍 Risk Report Panel  │
│                    │                         │
│  Ask anything      │  Summary metrics        │
│  about the repo    │  Untested functions     │
│                    │  Breaking points        │
│                    │  Security issues        │
└────────────────────┴────────────────────────┘
```

---

## Data Flow (End to End)

```
1. User pastes GitHub URL
2. /ingest called → GitHub API fetches repo
3. Files chunked + embedded into ChromaDB
4. IBM Bob ingests repo for full context analysis
5. repo_id returned to UI

--- Module 1 (Q&A) ---
6. User types question in chat
7. /ask called → vector search retrieves relevant chunks
8. IBM Bob answers with full context awareness
9. Answer + source files displayed in UI

--- Module 2 (Review) ---
10. User clicks "Run Review"
11. /review called → risk_analyzer + security_scanner run
12. IBM Bob reasons over codebase for each check
13. Structured report rendered in UI
```

---

## Environment Variables

```env
GITHUB_TOKEN=your_github_pat
IBM_BOB_API_KEY=provided_at_hackathon_kickoff
IBM_BOB_BASE_URL=https://...
CHROMA_PERSIST_DIR=./chroma_db
```

---

## 48-Hour Build Plan

| Time | Task |
|---|---|
| Hour 0–2 | Project setup, env config, GitHub loader working |
| Hour 2–6 | Ingestion pipeline: chunker + embedder + ChromaDB |
| Hour 6–12 | Module 1: RAG Q&A with IBM Bob |
| Hour 12–18 | Module 2: Risk analyzer + security scanner |
| Hour 18–22 | FastAPI routes + connect everything |
| Hour 22–28 | Streamlit UI — both panels working |
| Hour 28–36 | Testing on real repos, fix bugs |
| Hour 36–42 | Polish UI, generate demo report |
| Hour 42–47 | Record demo, write submission |
| Hour 47–48 | Submit ✅ |

---

## Claude Code Prompt

> **Read this file and README.md first before writing any code.**
> 
> I am building **RepoSense** — an AI-powered developer tool for the IBM Bob Hackathon (May 15–17, 2026).
> 
> The project has two modules on a shared ingestion layer:
> - **Module 1 (Repo Intelligence):** Ingest a GitHub repo, build a RAG pipeline with IBM Bob, expose a Q&A interface about the codebase
> - **Module 2 (Risk Review):** On the same ingested repo, detect untested functions, breaking points, and security smells — output a structured report
> 
> **Stack:** Python, FastAPI, LangChain, ChromaDB, IBM Bob API, Streamlit
> **Constraint:** Solo build, 48 hours
> 
> Start by scaffolding the full folder structure from ARCHITECTURE.md, then implement the ingestion layer first (`github_loader.py` → `chunker.py` → `embedder.py`). Ask me before making any architectural decisions not covered in these docs.
