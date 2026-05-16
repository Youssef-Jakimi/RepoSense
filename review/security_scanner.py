"""
Hybrid security scanner: regex pre-pass (always runs) + IBM Bob enrichment (best-effort).
Never executes code from the analyzed repo.
"""

import logging
import os
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security patterns: (name, regex, severity, default_description)
# ---------------------------------------------------------------------------

PATTERNS = [
    ("aws_access_key",  r"\bAKIA[0-9A-Z]{16}\b",                                                                          "high",   "Hardcoded AWS access key"),
    ("aws_secret_key",  r"(?i)aws[_-]?secret[_-]?(access[_-]?)?key\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}['\"]",               "high",   "Hardcoded AWS secret key"),
    ("stripe_live_key", r"\bsk_live_[A-Za-z0-9]{20,}\b",                                                                  "high",   "Hardcoded Stripe live key"),
    ("github_token",    r"\bgh[pousr]_[A-Za-z0-9]{36,}\b",                                                                "high",   "Hardcoded GitHub token"),
    ("openai_key",      r"\bsk-[A-Za-z0-9]{32,}\b",                                                                       "high",   "Hardcoded OpenAI API key"),
    ("generic_secret",  r"(?i)(api[_-]?key|secret|password|passwd|pwd|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]",              "medium", "Possible hardcoded secret"),
    ("eval_call",       r"\beval\s*\(",                                                                                    "medium", "Use of eval() — possible code injection"),
    ("exec_call",       r"\bexec\s*\(",                                                                                    "medium", "Use of exec() — possible code injection"),
    ("sql_concat",      r"(?i)(SELECT|INSERT|UPDATE|DELETE)\b[^;]{0,200}\+\s*\w+",                                        "high",   "Possible SQL string concatenation — injection risk"),
    ("insecure_http",   r"http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)",                                                   "low",    "Insecure http:// URL"),
    ("debug_true",      r"(?i)\bdebug\s*[:=]\s*true\b",                                                                   "low",    "DEBUG=True in code/config"),
    ("dangerous_yaml",  r"\byaml\.load\s*\(",                                                                             "medium", "yaml.load without SafeLoader — possible code execution"),
    ("pickle_load",     r"\bpickle\.loads?\s*\(",                                                                         "medium", "pickle.load — unsafe deserialization on untrusted data"),
]

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

_COMPILED_PATTERNS = [
    (name, re.compile(pattern), severity, description)
    for name, pattern, severity, description in PATTERNS
]

# ---------------------------------------------------------------------------
# Internal helpers (mirrored from risk_analyzer to keep modules self-contained)
# ---------------------------------------------------------------------------

def _is_test_file(path: str) -> bool:
    path_norm  = path.replace("\\", "/")
    basename   = path_norm.split("/")[-1].lower()
    stem       = basename.rsplit(".", 1)[0] if "." in basename else basename
    path_lower = path_norm.lower()

    if "test_" in basename or "_test" in stem:
        return True

    segments = path_lower.split("/")
    if any(seg in {"test", "tests", "__tests__", "spec"} for seg in segments[:-1]):
        return True

    if any(basename.endswith(ext) for ext in (".test.js", ".test.ts", ".spec.js", ".spec.ts")):
        return True

    return False


def _line_of(content: str, match_start: int) -> int:
    return content[:match_start].count("\n") + 1


def _code_snippet(content: str, line: int, context: int = 2) -> str:
    """Return a few lines around `line` (1-indexed) for Bob context."""
    lines = content.splitlines()
    start = max(0, line - 1 - context)
    end   = min(len(lines), line - 1 + context + 1)
    return "\n".join(lines[start:end])


# ---------------------------------------------------------------------------
# IBM Bob enrichment (stubbed — awaiting API details at hackathon kickoff)
# ---------------------------------------------------------------------------

_ENRICH_LIMIT = 15  # keep JSON output well within 1024-token chat limit


def _call_bob_enrichment(findings: list[dict]) -> list[dict]:
    import json

    from langchain_ibm import ChatWatsonx
    from langchain_core.messages import HumanMessage, SystemMessage

    model = ChatWatsonx(
        model_id=os.environ.get("WATSONX_MODEL_ID", "meta-llama/llama-3-3-70b-instruct"),
        url=os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
        project_id=os.environ["WATSONX_PROJECT_ID"],
        apikey=os.environ["WATSONX_API_KEY"],
        params={"max_tokens": 1024, "temperature": 0},
    )

    # Only enrich the highest-priority findings so the response fits in one call
    batch = findings[:_ENRICH_LIMIT]

    findings_text = "\n".join(
        f'{i}. [{f["severity"].upper()}] {f["file_path"]}:{f["line"]} — {f["description"]}\n'
        f'   Code: {f.get("_snippet", "")}'
        for i, f in enumerate(batch)
    )

    system = (
        "You are a security code reviewer. Analyze these static-analysis findings. "
        "For each, decide if it is a false positive and write a refined description. "
        "Return ONLY a JSON array — no markdown fences, no explanation. "
        'Each element: {"index": <int>, "false_positive": <bool>, '
        '"refined_description": <str>, "exploitability": "high"|"medium"|"low"|"none"}'
    )
    user = f"Findings:\n\n{findings_text}\n\nReturn the JSON array."

    response = model.invoke([SystemMessage(content=system), HumanMessage(content=user)])

    text = response.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        enriched_list = json.loads(text)
        enriched_map = {item["index"]: item for item in enriched_list}
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Watsonx returned malformed JSON: %s — skipping enrichment", exc)
        return findings

    result: list[dict] = []
    for i, finding in enumerate(findings):
        enrichment = enriched_map.get(i)
        if enrichment is None:
            result.append(finding)
            continue
        if enrichment.get("false_positive"):
            continue
        result.append({
            **finding,
            "description":  enrichment.get("refined_description", finding["description"]),
            "bob_enriched": True,
        })

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_security(files: list[dict]) -> dict:
    """
    Args:
        files: list of {path, content, language, size} from github_loader

    Returns:
        {
            "findings": list[dict],   # [{file_path, line, pattern_matched, severity, description, bob_enriched}]
            "counts": {"high": int, "medium": int, "low": int},
            "bob_enrichment_available": bool,
        }
    """
    # -----------------------------------------------------------------------
    # Stage 1 — Regex pre-pass (always runs)
    # -----------------------------------------------------------------------
    findings: list[dict] = []

    source_files = [
        f for f in files
        if f.get("content") and not _is_test_file(f.get("path", ""))
    ]

    for file in source_files:
        path    = file["path"]
        content = file["content"]

        for name, pattern, severity, description in _COMPILED_PATTERNS:
            for match in pattern.finditer(content):
                line = _line_of(content, match.start())
                findings.append({
                    "file_path":       path,
                    "line":            line,
                    "pattern_matched": name,
                    "severity":        severity,
                    "description":     description,
                    "bob_enriched":    False,
                    "_snippet":        _code_snippet(content, line),
                })

    # Sort: severity (high → medium → low), then file_path
    findings.sort(key=lambda f: (_SEVERITY_ORDER.get(f["severity"], 99), f["file_path"]))

    # Cap at 50 findings total
    findings = findings[:50]

    # -----------------------------------------------------------------------
    # Stage 2 — IBM Bob enrichment (best-effort)
    # -----------------------------------------------------------------------
    bob_api_key = os.environ.get("WATSONX_API_KEY", "").strip()
    bob_enrichment_available = False

    if bob_api_key:
        try:
            findings = _call_bob_enrichment(findings)
            bob_enrichment_available = True
        except Exception as exc:
            logger.warning(
                "Bob enrichment unavailable: %s — returning regex findings unchanged", exc
            )

    # Strip internal snippet key before returning
    for f in findings:
        f.pop("_snippet", None)

    counts = {
        "high":   sum(1 for f in findings if f["severity"] == "high"),
        "medium": sum(1 for f in findings if f["severity"] == "medium"),
        "low":    sum(1 for f in findings if f["severity"] == "low"),
    }

    return {
        "findings":                 findings,
        "counts":                   counts,
        "bob_enrichment_available": bob_enrichment_available,
    }


# ---------------------------------------------------------------------------
# Verification (run directly: python -m review.security_scanner)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import pprint

    SECRET_CONTENT = 'password = "hunter2hunter2"\n'

    # --- Test 1: generic_secret detected in a source file -------------------
    r1 = scan_security([
        {"path": "config.py", "content": SECRET_CONTENT, "language": "python", "size": 30},
    ])
    assert len(r1["findings"]) == 1, f"Expected 1 finding, got {r1['findings']}"
    f = r1["findings"][0]
    assert f["pattern_matched"] == "generic_secret", f"pattern_matched: {f['pattern_matched']}"
    assert f["line"] == 1,                            f"line: {f['line']}"
    assert f["severity"] == "medium",                 f"severity: {f['severity']}"
    assert f["bob_enriched"] is False
    assert r1["bob_enrichment_available"] is False
    assert r1["counts"] == {"high": 0, "medium": 1, "low": 0}
    print("Test 1 PASSED — generic_secret detected at line 1")

    # --- Test 2: test file is skipped entirely ------------------------------
    r2 = scan_security([
        {"path": "test_config.py", "content": SECRET_CONTENT, "language": "python", "size": 30},
    ])
    assert r2["findings"] == [], f"Expected no findings for test file, got {r2['findings']}"
    assert r2["counts"] == {"high": 0, "medium": 0, "low": 0}
    print("Test 2 PASSED — test file correctly skipped")

    # --- Test 3: high-severity findings sorted before medium ----------------
    mixed_content = (
        'eval("user_input")\n'             # medium (line 1)
        'AKIAIOSFODNN7EXAMPLE\n'           # high (line 2)
    )
    r3 = scan_security([
        {"path": "app.py", "content": mixed_content, "language": "python", "size": 50},
    ])
    sevs = [f["severity"] for f in r3["findings"]]
    high_indices  = [i for i, s in enumerate(sevs) if s == "high"]
    medium_indices = [i for i, s in enumerate(sevs) if s == "medium"]
    if high_indices and medium_indices:
        assert max(high_indices) < min(medium_indices), "High findings must precede medium findings"
    print(f"Test 3 PASSED — severity sort correct ({sevs})")

    # --- Test 4: 50-finding cap applied ------------------------------------
    many_http = "\n".join(f'url = "http://example{i}.com/api"' for i in range(60))
    r4 = scan_security([
        {"path": "urls.py", "content": many_http, "language": "python", "size": 1000},
    ])
    assert len(r4["findings"]) <= 50, f"Expected ≤50 findings, got {len(r4['findings'])}"
    print(f"Test 4 PASSED — cap enforced ({len(r4['findings'])} findings)")

    # --- Test 5: empty file list --------------------------------------------
    r5 = scan_security([])
    assert r5["findings"] == []
    assert r5["counts"] == {"high": 0, "medium": 0, "low": 0}
    assert r5["bob_enrichment_available"] is False
    print("Test 5 PASSED — empty file list handled")

    # --- Test 6: _snippet key not present in returned findings --------------
    r6 = scan_security([
        {"path": "cfg.py", "content": SECRET_CONTENT, "language": "python", "size": 30},
    ])
    assert all("_snippet" not in f for f in r6["findings"]), "_snippet must be stripped from output"
    print("Test 6 PASSED — _snippet key stripped from findings")

    print("\nAll verification tests PASSED.")
    print("\n--- Sample output (Test 1) ---")
    pprint.pprint(r1)
