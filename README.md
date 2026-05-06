# RepoSense 🧠🔍
> Your repo. Understood. Reviewed. Ready.

RepoSense is an AI-powered developer tool built on **IBM Bob** that combines deep codebase intelligence with automated risk analysis — giving developers both understanding and actionable insights in one shot.

Built for the **IBM Bob Hackathon** (May 15–17, 2026) on [lablab.ai](https://lablab.ai).

---

## What It Does

Drop a GitHub repo URL and RepoSense gives you two superpowers:

### 🧠 Module 1 — Repo Intelligence (Q&A)
- Ingests any GitHub repository via the GitHub API
- IBM Bob analyzes the full codebase with real context
- Exposes a conversational Q&A interface about the repo
- Ask anything: *"Where is auth handled?"*, *"What does this function depend on?"*, *"How does the payment flow work?"*

### 🔍 Module 2 — Automated Risk Review
- Runs on the same ingested repo — no extra setup
- Flags untested functions and missing test coverage
- Detects potential breaking points and risky dependencies
- Highlights security smells and anti-patterns
- Outputs a clean, structured risk report

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Partner | IBM Bob |
| Backend | Python (FastAPI) |
| RAG Pipeline | LangChain / LlamaIndex |
| GitHub Integration | GitHub REST API (PyGithub) |
| Vector Store | ChromaDB / FAISS |
| Frontend | React |

---

## Project Structure

```
reposense/
├── README.md
├── ARCHITECTURE.md
├── requirements.txt
├── .env.example
│
├── ingestion/
│   ├── github_loader.py       # Fetch repo files via GitHub API
│   ├── chunker.py             # Split code into meaningful chunks
│   └── embedder.py            # Embed chunks into vector store
│
├── intelligence/
│   ├── qa_engine.py           # Q&A over codebase using IBM Bob + RAG
│   └── context_builder.py     # Build repo context for Bob
│
├── review/
│   ├── risk_analyzer.py       # Detect untested code, breaking points
│   ├── security_scanner.py    # Flag security smells
│   └── report_generator.py    # Format structured risk report
│
├── api/
│   ├── main.py                # FastAPI entry point
│   ├── routes/
│   │   ├── ingest.py          # POST /ingest
│   │   ├── qa.py              # POST /ask
│   │   └── review.py          # GET /review
│
└── ui/
    └── app.py                 # Streamlit UI
```

---

## Getting Started

### Prerequisites
- Python 3.10+
- GitHub Personal Access Token
- IBM Bob API access (provided at hackathon kickoff)

### Installation

```bash
git clone https://github.com/yourusername/reposense.git
cd reposense
pip install -r requirements.txt
cp .env.example .env
# Fill in your API keys in .env
```

### Run

```bash
# Start the backend
uvicorn api.main:app --reload

# Start the UI
streamlit run ui/app.py
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/ingest` | Ingest a GitHub repo by URL |
| POST | `/ask` | Ask a question about the ingested repo |
| GET | `/review` | Get the full risk review report |

---

## Hackathon Context

**Event:** IBM Bob Hackathon — lablab.ai  
**Dates:** May 15–17, 2026  
**Prize Pool:** $10,000  
**Challenge:** Build tools and workflows that developers would actually use, powered by IBM Bob  

**How IBM Bob is used:**
- Full repository context analysis (not just snippets)
- Intent-aware Q&A over real codebases
- Logic reasoning for risk detection
- Multi-step workflow automation for review pipeline

---

## Judging Criteria Alignment

| Criteria | How RepoSense addresses it |
|---|---|
| Application of Technology | IBM Bob is the core engine for both modules |
| Business Value | Solves real dev pain: onboarding & code risk |
| Originality | Combines Q&A + risk review in one unified pipeline |
| Presentation | Clean UI, structured report output, live demo |

---

## Author

Built solo by [Your Name] — Software & AI Engineering Student  
IBM Bob Hackathon 2026
