# RepoSense — Demo Repo Candidates

> **Always test each repo end-to-end before recording — pick the one with the most visually compelling output.**

Run a full ingest → Ask → Risk Review cycle on each candidate. Choose whichever produces the clearest Risk Score and the most interesting Q&A answer. The table below is a starting point, not a commitment.

---

## Candidates

### 1. Python web app with tests — `pallets/flask-sqlalchemy`

| Field | Detail |
|---|---|
| URL | `https://github.com/pallets/flask-sqlalchemy` |
| Language | Python |
| Why it's good | Manageable size, real test suite, clean module structure — Python AST gives accurate untested-function detection |
| Expected Risk Score | **65–80** — coverage score will be healthy, security and complexity scores should be clean |
| Zero-test banner | Not expected — tests exist |
| Money question | *"How is the SQLAlchemy session managed across requests?"* |

**What the demo shows:** A healthy repo with a meaningful Q&A answer grounded in real session-handling code. Good baseline to contrast against the zero-test candidate.

**Fallback:** `tiangolo/fastapi` if flask-sqlalchemy is too small or the ingestion output is thin.

---

### 2. Zero-test JS repo — `expressjs/express`

| Field | Detail |
|---|---|
| URL | `https://github.com/expressjs/express` |
| Language | JavaScript |
| Why it's good | Universally recognised name — judges know what Express is; JS detection uses best-effort regex, so coverage score will appear notably lower than a Python repo of equal quality |
| Expected Risk Score | **20–45** — JS regex detection limits coverage visibility; zero-test banner likely to appear |
| Zero-test banner | Expected (best-effort detection on JS finds few test-to-function links) |
| Money question | *"Where is request routing handled and how are middleware functions chained?"* |

**What the demo shows:** The zero-test edge case — the banner appears prominently, score drops, but the tool doesn't fail. Security and complexity sub-scores still compute. Good contrast beat in the Risk Review tab.

**Fallback:** `janl/mustache.js` (small, minimal test structure) if Express produces an error or a suspiciously high score.

---

### 3. Go CLI — `urfave/cli`

| Field | Detail |
|---|---|
| URL | `https://github.com/urfave/cli` |
| Language | Go |
| Why it's good | Smaller and more demo-friendly than `cli/cli`; Go uses best-effort regex detection so coverage score will be partial — shows the "language-agnostic" label working honestly |
| Expected Risk Score | **40–60** — partial coverage detection, moderate complexity, likely clean on security |
| Zero-test banner | Unlikely — test files exist, though detection is labeled best-effort |
| Money question | *"How does urfave/cli parse flags and dispatch subcommands?"* |

**What the demo shows:** Language-agnostic reach — the tool runs on Go just as easily as Python, with honest labeling of best-effort detection. Useful talking point for judges asking about multi-language support.

**Fallback:** `spf13/cobra` if urfave/cli ingestion is slow or the output is sparse.

---

## Quick Comparison

| Repo | Language | Detection | Expected Score | Best for showing |
|---|---|---|---|---|
| `pallets/flask-sqlalchemy` | Python | AST (accurate) | 65–80 | Healthy repo, real Q&A citations |
| `expressjs/express` | JavaScript | Regex (best-effort) | 20–45 | Zero-test banner, score still computes |
| `urfave/cli` | Go | Regex (best-effort) | 40–60 | Language-agnostic reach |

---

## Pre-Demo Verification Steps

1. Run `POST /ingest` with each repo URL and confirm ingestion completes without error
2. Check the Risk Score renders — not `null`, not `0` unless expected
3. Ask the money question for each repo and confirm the answer cites a real file path
4. Switch to Risk Review and verify findings are non-empty and formatted
5. Click Download Markdown and open the file — confirm it is readable
6. Pick the candidate where steps 1–5 all look clean and visually compelling
