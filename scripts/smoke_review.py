"""
End-to-end smoke test for the RepoSense risk-review pipeline.

Usage:
    python scripts/smoke_review.py
    python scripts/smoke_review.py --save
"""

import argparse
import os
import sys
import traceback

# Ensure project root is on sys.path regardless of invocation style.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SMOKE_REPO_URL = "https://github.com/psf/requests-html"
_FALLBACK_URL  = "https://github.com/octocat/Hello-World"


def _ascii_box(text: str) -> str:
    bar = "+" + "=" * (len(text) + 4) + "+"
    return f"{bar}\n|  {text}  |\n{bar}"


def main(save: bool) -> None:
    from dotenv import load_dotenv
    load_dotenv()

    from ingestion import github_loader
    from intelligence import context_builder
    from review import risk_analyzer, security_scanner, report_generator

    github_token = os.environ.get("GITHUB_TOKEN") or None

    # --- 1. Load repo ---
    print(f"Loading repo: {SMOKE_REPO_URL}")
    try:
        loader_output = github_loader.load_repo(SMOKE_REPO_URL, github_token=github_token)
    except Exception as exc:
        print(f"Primary repo failed ({exc!r}), falling back to: {_FALLBACK_URL}")
        loader_output = github_loader.load_repo(_FALLBACK_URL, github_token=github_token)

    files = loader_output["files"]
    print(f"Loaded {len(files)} files.")

    # --- 2. Repo summary ---
    print("Building repo summary...")
    summary = context_builder.build_repo_summary(loader_output)

    # --- 3. Risk analysis ---
    print("Running risk analysis...")
    risk_analysis = risk_analyzer.analyze_repo(files)

    # --- 4. Security scan ---
    print("Running security scan...")
    security_scan = security_scanner.scan_security(files)

    # --- 5. Generate report ---
    print("Generating report...")
    report = report_generator.generate_report(summary, risk_analysis, security_scan)

    scores  = report["scores"]
    rpt_sum = report["summary"]

    # --- Risk Score (ASCII-bordered for visual punch) ---
    risk_score = report["risk_score"]
    print()
    print(_ascii_box(f"RISK SCORE:  {risk_score} / 100"))
    print()

    # --- Sub-scores ---
    cov  = scores["coverage_score"]
    comp = scores["complexity_score"]
    sec  = scores["security_score"]
    cov_disp = f"{cov:.1f}" if cov is not None else "N/A"
    print(f"Coverage score  : {cov_disp} / 100  (weight 40%)")
    print(f"Complexity score: {comp:.1f} / 100  (weight 30%)")
    print(f"Security score  : {sec:.1f} / 100  (weight 30%)")
    print()

    # --- Top 3 untested functions ---
    untested = report["untested_functions"][:3]
    print(f"Top 3 untested functions (of {rpt_sum['untested_count']} total):")
    if untested:
        for f in untested:
            print(f"  {f['name']}  |  {f['path']}:{f['line']}")
    else:
        print("  (none detected)")
    print()

    # --- Top 3 breaking points ---
    bps = report["breaking_points"][:3]
    print(f"Top 3 breaking points (of {rpt_sum['breaking_points_count']} total):")
    if bps:
        for b in bps:
            print(f"  {b['name']}  |  {b['path']}  |  fan_out={b['fan_out']}")
    else:
        print("  (none detected)")
    print()

    # --- Top 3 security findings ---
    findings = report["security_findings"][:3]
    sec_total = rpt_sum["security_high"] + rpt_sum["security_medium"] + rpt_sum["security_low"]
    print(f"Top 3 security findings (of {sec_total} total):")
    if findings:
        for f in findings:
            print(f"  [{f['severity'].upper()}]  {f['pattern_matched']}  |  {f['file_path']}:{f['line']}")
    else:
        print("  (none detected)")
    print()

    # --- IBM Bob enrichment + recommendations count ---
    print(f"IBM Bob enrichment available: {rpt_sum['bob_enrichment_available']}")
    print(f"Recommendations             : {len(report['recommendations'])}")
    print()

    # --- Optional Markdown save ---
    if save:
        md = report_generator.render_markdown(report)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        demo_dir = os.path.join(project_root, "demo")
        os.makedirs(demo_dir, exist_ok=True)
        out_path = os.path.join(demo_dir, "sample_report.md")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"Report saved to: {out_path}")
        print()

    print("Smoke test PASSED.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RepoSense review pipeline smoke test.")
    parser.add_argument(
        "--save",
        action="store_true",
        help="Write the rendered Markdown report to ./demo/sample_report.md",
    )
    args = parser.parse_args()

    try:
        main(save=args.save)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
    sys.exit(0)
