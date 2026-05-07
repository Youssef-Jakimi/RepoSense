"""
Combines risk_analyzer + security_scanner outputs, computes the Risk Score,
and produces the canonical JSON report and downloadable Markdown.
Never calls any LLM — pure synthesis from the analyzer/scanner inputs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Optional


# ---------------------------------------------------------------------------
# Score computation helpers
# ---------------------------------------------------------------------------

def _compute_coverage_score(
    total: int,
    tested: int,
    no_functions_detected: bool,
) -> Optional[float]:
    if no_functions_detected:
        return None
    if total == 0:
        return 0.0
    return round((tested / total) * 100, 1)


def _compute_complexity_score(breaking_points: list[dict]) -> float:
    avg_fan_out = mean(bp["fan_out"] for bp in breaking_points) if breaking_points else 0.0
    return round(100.0 - min(100.0, avg_fan_out * 10.0), 1)


def _compute_security_score(high: int, medium: int, low: int) -> float:
    penalty = high * 20 + medium * 10 + low * 5
    return round(100.0 - min(100.0, float(penalty)), 1)


def _compute_risk_score(
    coverage_score: Optional[float],
    complexity_score: float,
    security_score: float,
) -> float:
    cov = coverage_score if coverage_score is not None else 0.0
    return round(cov * 0.4 + complexity_score * 0.3 + security_score * 0.3, 1)


# ---------------------------------------------------------------------------
# Recommendations (deterministic, no LLM)
# ---------------------------------------------------------------------------

_SECRET_PATTERN_NAMES = frozenset({
    "aws_access_key",
    "aws_secret_key",
    "stripe_live_key",
    "github_token",
    "openai_key",
    "generic_secret",
})

_FALLBACK_RECS = [
    "Add a CI pipeline that runs tests and linting on every push.",
    "Enforce dependency version pinning for reproducible and auditable builds.",
    "Schedule periodic reviews of medium and low-severity security findings.",
]


def _generate_recommendations(
    no_tests_detected: bool,
    coverage_score: Optional[float],
    untested_count: int,
    breaking_points: list[dict],
    security_counts: dict,
    security_findings: list[dict],
    bob_enrichment_available: bool,
) -> list[str]:
    recs: list[str] = []

    if no_tests_detected:
        recs.append(
            "This repository has no test files. Add a test suite — "
            "even smoke tests improve confidence dramatically."
        )

    if coverage_score is not None and coverage_score < 50:
        n = min(untested_count, 5)
        recs.append(
            f"Test coverage is low ({coverage_score:.1f}%). "
            f"Prioritize tests for the {n} most-referenced functions."
        )

    if breaking_points:
        n = len(breaking_points)
        s = "s" if n != 1 else ""
        v = "are" if n != 1 else "is"
        recs.append(
            f"{n} function{s} {v} referenced in 5+ files. "
            "Changes to these have wide blast radius — refactor with care."
        )

    high_count = security_counts.get("high", 0)
    if high_count > 0:
        s = "s" if high_count != 1 else ""
        recs.append(
            f"{high_count} high-severity security issue{s} detected. "
            "Review before any deployment."
        )

    matched_patterns = {f["pattern_matched"] for f in security_findings}
    if matched_patterns & _SECRET_PATTERN_NAMES:
        recs.append(
            "Hardcoded secrets detected — rotate keys immediately and "
            "move to environment variables."
        )

    if not bob_enrichment_available:
        recs.append(
            "Security findings are regex-only — IBM Bob enrichment was unavailable. "
            "Treat results as preliminary."
        )

    for fallback in _FALLBACK_RECS:
        if len(recs) >= 3:
            break
        recs.append(fallback)

    return recs[:7]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_report(
    repo_summary: dict,
    risk_analysis: dict,
    security_scan: dict,
) -> dict:
    """
    Returns the canonical report stored in RepoState.report:
    {
        "repo_id": str,
        "risk_score": float,         # 0-100, rounded to 1 decimal
        "scores": {
            "coverage_score": float | None,    # None if no_functions_detected
            "complexity_score": float,
            "security_score": float,
        },
        "summary": {
            "total_functions": int,
            "tested_functions": int,
            "untested_count": int,
            "breaking_points_count": int,
            "security_high": int,
            "security_medium": int,
            "security_low": int,
            "no_tests_detected": bool,
            "no_functions_detected": bool,
            "bob_enrichment_available": bool,
        },
        "untested_functions": [...],
        "breaking_points": [...],
        "security_findings": [...],
        "recommendations": list[str],
        "language_breakdown": {...},
        "generated_at": str,         # ISO 8601 UTC
    }

    owner and name are included as convenience fields for rendering.
    """
    total    = risk_analysis["total_functions"]
    tested   = risk_analysis["tested_functions"]
    no_funcs = risk_analysis["no_functions_detected"]
    no_tests = risk_analysis["no_tests_detected"]
    untested = risk_analysis["untested_functions"]
    bps      = risk_analysis["breaking_points"]
    lang_bd  = risk_analysis.get("language_breakdown", {})

    counts   = security_scan["counts"]
    findings = security_scan["findings"]
    bob_ok   = security_scan["bob_enrichment_available"]

    high   = counts["high"]
    medium = counts["medium"]
    low    = counts["low"]

    coverage_score   = _compute_coverage_score(total, tested, no_funcs)
    complexity_score = _compute_complexity_score(bps)
    security_score   = _compute_security_score(high, medium, low)
    risk_score       = _compute_risk_score(coverage_score, complexity_score, security_score)

    recs = _generate_recommendations(
        no_tests_detected=no_tests,
        coverage_score=coverage_score,
        untested_count=len(untested),
        breaking_points=bps,
        security_counts=counts,
        security_findings=findings,
        bob_enrichment_available=bob_ok,
    )

    return {
        "repo_id":    repo_summary["repo_id"],
        "owner":      repo_summary.get("owner", ""),
        "name":       repo_summary.get("name", ""),
        "risk_score": risk_score,
        "scores": {
            "coverage_score":   coverage_score,
            "complexity_score": complexity_score,
            "security_score":   security_score,
        },
        "summary": {
            "total_functions":        total,
            "tested_functions":       tested,
            "untested_count":         len(untested),
            "breaking_points_count":  len(bps),
            "security_high":          high,
            "security_medium":        medium,
            "security_low":           low,
            "no_tests_detected":      no_tests,
            "no_functions_detected":  no_funcs,
            "bob_enrichment_available": bob_ok,
        },
        "untested_functions": untested,
        "breaking_points":    bps,
        "security_findings":  findings,
        "recommendations":    recs,
        "language_breakdown": lang_bd,
        "generated_at":       datetime.now(timezone.utc).isoformat(),
    }


def render_markdown(report: dict) -> str:
    """Render the report as a downloadable Markdown document."""
    scores  = report["scores"]
    summary = report["summary"]

    owner = report.get("owner", "")
    name  = report.get("name", "")
    repo_display = f"{owner}/{name}" if owner and name else report["repo_id"]

    cov_score  = scores["coverage_score"]
    comp_score = scores["complexity_score"]
    sec_score  = scores["security_score"]
    risk_score = report["risk_score"]

    cov_display = f"{cov_score}/100" if cov_score is not None else "N/A"

    total  = summary["total_functions"]
    tested = summary["tested_functions"]
    if summary["no_functions_detected"]:
        tested_line = "Tested: N/A"
    elif cov_score is not None:
        tested_line = f"Tested: {tested} ({cov_score:.1f}%)"
    else:
        tested_line = f"Tested: {tested}"

    high   = summary["security_high"]
    medium = summary["security_medium"]
    low    = summary["security_low"]

    # Warning banners (blockquote style)
    banner_lines: list[str] = []
    if summary["no_tests_detected"]:
        banner_lines.append("> **!! No test files detected !!** — coverage score is 0%.")
    if not summary["bob_enrichment_available"]:
        banner_lines.append("> **!! IBM Bob enrichment unavailable !!** — security findings are regex-only.")
    banner_block = "\n".join(banner_lines) + "\n\n" if banner_lines else ""

    # Recommendations
    recs_text = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(report["recommendations"]))

    # Untested functions table (top 20)
    untested = report["untested_functions"][:20]
    if untested:
        uf_rows = "\n".join(
            f"| `{f['name']}` | {f['path']} | {f['line']} | {f['detection_method']} |"
            for f in untested
        )
        uf_section = (
            "| Function | File | Line | Detection |\n"
            "|---|---|---|---|\n"
            + uf_rows
        )
    else:
        uf_section = "*None detected.*"

    # Breaking points table (top 10)
    bps = report["breaking_points"][:10]
    if bps:
        bp_rows = "\n".join(
            f"| `{b['name']}` | {b['path']} | {b['line']} | {b['fan_out']} |"
            for b in bps
        )
        bp_section = (
            "| Function | File | Line | Fan-Out |\n"
            "|---|---|---|---|\n"
            + bp_rows
        )
    else:
        bp_section = "*None detected.*"

    # Security findings table (top 20)
    sec_findings = report["security_findings"][:20]
    if sec_findings:
        sf_rows = "\n".join(
            f"| {f['severity'].upper()} | {f['pattern_matched']} "
            f"| {f['file_path']} | {f['line']} | {f['description']} |"
            for f in sec_findings
        )
        sf_section = (
            "| Severity | Pattern | File | Line | Description |\n"
            "|---|---|---|---|---|\n"
            + sf_rows
        )
    else:
        sf_section = "*None detected.*"

    return (
        f"# RepoSense Risk Report\n\n"
        f"**Repository:** {repo_display}\n"
        f"**Generated:** {report['generated_at']}\n\n"
        f"## Risk Score: {risk_score}/100\n\n"
        f"| Component | Score | Weight |\n"
        f"|---|---|---|\n"
        f"| Coverage | {cov_display} | 40% |\n"
        f"| Complexity | {comp_score}/100 | 30% |\n"
        f"| Security | {sec_score}/100 | 30% |\n\n"
        f"## Summary\n"
        f"- Total functions: {total}\n"
        f"- {tested_line}\n"
        f"- Untested: {summary['untested_count']}\n"
        f"- Breaking points: {summary['breaking_points_count']}\n"
        f"- Security findings: {high} high · {medium} medium · {low} low\n\n"
        f"{banner_block}"
        f"## Recommendations\n"
        f"{recs_text}\n\n"
        f"## Untested Functions (top 20)\n"
        f"{uf_section}\n\n"
        f"## Breaking Points (top 10)\n"
        f"{bp_section}\n\n"
        f"## Security Findings (top 20)\n"
        f"{sf_section}\n\n"
        f"---\n"
        f"*Report generated by RepoSense — IBM Bob Hackathon 2026*"
    )


# ---------------------------------------------------------------------------
# Verification (run directly: python -m review.report_generator)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Known arithmetic:
    #   total=10, tested=6  → coverage_score  = (6/10)*100 = 60.0
    #   fan_outs=[7,5]      → avg=6.0          → complexity_score = 100-60 = 40.0
    #   high=1,med=2,low=3  → penalty=55       → security_score  = 100-55 = 45.0
    #   risk_score = 60*0.4 + 40*0.3 + 45*0.3 = 24 + 12 + 13.5 = 49.5

    fake_summary = {
        "repo_id": "abc123",
        "owner":   "acme",
        "name":    "testapp",
        "languages": {"python": 5},
    }

    fake_risk = {
        "total_functions":    10,
        "tested_functions":   6,
        "no_tests_detected":  False,
        "no_functions_detected": False,
        "untested_functions": [
            {"name": "bar",  "path": "app.py",   "line": 10, "language": "python", "detection_method": "ast"},
            {"name": "baz",  "path": "app.py",   "line": 20, "language": "python", "detection_method": "ast"},
            {"name": "qux",  "path": "utils.py", "line": 5,  "language": "python", "detection_method": "ast"},
            {"name": "quux", "path": "utils.py", "line": 15, "language": "python", "detection_method": "ast"},
        ],
        "breaking_points": [
            {"name": "process",  "path": "core.py", "line": 1,  "language": "python", "fan_out": 7, "referenced_in": []},
            {"name": "validate", "path": "core.py", "line": 10, "language": "python", "fan_out": 5, "referenced_in": []},
        ],
        "language_breakdown": {
            "python": {"functions": 10, "tested": 6, "best_effort": False},
        },
    }

    fake_sec = {
        "findings": [
            {"file_path": "db.py",     "line": 12, "pattern_matched": "sql_concat",     "severity": "high",   "description": "Possible SQL injection",   "bob_enriched": False},
            {"file_path": "config.py", "line": 5,  "pattern_matched": "generic_secret", "severity": "medium", "description": "Possible hardcoded secret", "bob_enriched": False},
            {"file_path": "app.py",    "line": 3,  "pattern_matched": "insecure_http",  "severity": "low",    "description": "Insecure http:// URL",       "bob_enriched": False},
        ],
        "counts": {"high": 1, "medium": 2, "low": 3},
        "bob_enrichment_available": False,
    }

    report = generate_report(fake_summary, fake_risk, fake_sec)

    assert report["scores"]["coverage_score"]   == 60.0, f"coverage: {report['scores']['coverage_score']}"
    assert report["scores"]["complexity_score"] == 40.0, f"complexity: {report['scores']['complexity_score']}"
    assert report["scores"]["security_score"]   == 45.0, f"security: {report['scores']['security_score']}"
    assert report["risk_score"]                 == 49.5, f"risk_score: {report['risk_score']}"
    print(f"Score check PASSED — risk_score={report['risk_score']}")

    assert report["summary"]["total_functions"]       == 10
    assert report["summary"]["tested_functions"]      == 6
    assert report["summary"]["untested_count"]        == 4
    assert report["summary"]["breaking_points_count"] == 2
    assert report["summary"]["security_high"]         == 1
    assert report["summary"]["security_medium"]       == 2
    assert report["summary"]["security_low"]          == 3
    print("Summary check PASSED")

    assert 3 <= len(report["recommendations"]) <= 7, f"recs count: {len(report['recommendations'])}"
    print(f"Recommendations ({len(report['recommendations'])} items):")
    for r in report["recommendations"]:
        print(f"  - {r}")

    md = render_markdown(report)
    assert md.startswith("# RepoSense Risk Report"), "Markdown must start with the correct header"
    assert "acme/testapp" in md,   "Markdown must contain repo display name"
    assert "49.5/100"    in md,    "Markdown must contain risk score"
    assert "40.0/100"    in md,    "Markdown must contain complexity score"
    assert "45.0/100"    in md,    "Markdown must contain security score"
    assert "60.0/100"    in md,    "Markdown must contain coverage score"
    print("Markdown check PASSED — starts with correct header, contains key values")

    # Edge case: no_functions_detected → coverage_score=None, score uses 0 for coverage
    # complexity=100 (no BPs), security=100 (no findings), risk = 0*0.4 + 100*0.3 + 100*0.3 = 60.0
    fake_risk_empty = {
        "total_functions":    0,
        "tested_functions":   0,
        "no_tests_detected":  True,
        "no_functions_detected": True,
        "untested_functions": [],
        "breaking_points":    [],
        "language_breakdown": {},
    }
    fake_sec_empty = {
        "findings": [],
        "counts":   {"high": 0, "medium": 0, "low": 0},
        "bob_enrichment_available": False,
    }
    report_empty = generate_report(fake_summary, fake_risk_empty, fake_sec_empty)

    assert report_empty["scores"]["coverage_score"] is None, "Expected None for no_functions_detected"
    assert report_empty["scores"]["complexity_score"] == 100.0
    assert report_empty["scores"]["security_score"]   == 100.0
    assert report_empty["risk_score"] == 60.0, f"Expected 60.0, got {report_empty['risk_score']}"
    print(f"Edge case PASSED — no_functions_detected, risk_score={report_empty['risk_score']}")

    md_empty = render_markdown(report_empty)
    assert md_empty.startswith("# RepoSense Risk Report")
    assert "N/A" in md_empty, "N/A must appear when no functions detected"
    print("Edge case markdown PASSED")

    # Edge case: perfect repo — no issues
    fake_risk_perfect = {
        "total_functions":    20,
        "tested_functions":   20,
        "no_tests_detected":  False,
        "no_functions_detected": False,
        "untested_functions": [],
        "breaking_points":    [],
        "language_breakdown": {"python": {"functions": 20, "tested": 20, "best_effort": False}},
    }
    fake_sec_perfect = {
        "findings": [],
        "counts":   {"high": 0, "medium": 0, "low": 0},
        "bob_enrichment_available": True,
    }
    report_perfect = generate_report(fake_summary, fake_risk_perfect, fake_sec_perfect)
    assert report_perfect["risk_score"] == 100.0, f"Expected 100.0, got {report_perfect['risk_score']}"
    assert 3 <= len(report_perfect["recommendations"]) <= 7
    print(f"Perfect repo PASSED — risk_score={report_perfect['risk_score']}")

    print("\nAll verification tests PASSED.")
