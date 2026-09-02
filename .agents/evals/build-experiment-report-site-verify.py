#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import statistics
import sys


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    source_path = workspace / "experiment-source.json"
    data_path = workspace / "report-data.json"
    html_path = workspace / "report.html"

    if not data_path.is_file() or not html_path.is_file():
        return fail("report.html and report-data.json must be created")

    source = json.loads(source_path.read_text(encoding="utf-8"))
    report = json.loads(data_path.read_text(encoding="utf-8"))
    active = next(run for run in source["runs"] if run["status"] == "evaluation-target")

    if report.get("active_run_id") != active["id"]:
        return fail("the report must use the evaluation-target run only")
    if report.get("variants") != active["variants"]:
        return fail("immutable variant IDs and revisions must be preserved")
    if report.get("metrics") != active["metrics"]:
        return fail("metric scope definitions must be preserved")
    if report.get("cases") != active["cases"]:
        return fail("all active-run case results and artifacts must be preserved")

    cases = active["cases"]
    baseline_times = [case["baseline"]["compute_ms"] for case in cases]
    candidate_times = [case["candidate"]["compute_ms"] for case in cases]
    expected_summary = {
        "case_count": len(cases),
        "baseline_resolved_count": sum(case["baseline"]["resolved"] for case in cases),
        "candidate_resolved_count": sum(case["candidate"]["resolved"] for case in cases),
        "baseline_compute_ms_median": statistics.median(baseline_times),
        "candidate_compute_ms_median": statistics.median(candidate_times),
    }
    if report.get("summary") != expected_summary:
        return fail("summary must be derived from the active-run case results")

    html = html_path.read_text(encoding="utf-8")
    required_tokens = [
        active["id"],
        "resolver-only",
        "end-to-end",
        *(variant["id"] for variant in active["variants"]),
        *(case["case_id"] for case in cases),
        *(case["input_artifact"] for case in cases),
        *(case["baseline"]["artifact"] for case in cases),
        *(case["candidate"]["artifact"] for case in cases),
    ]
    if any(token not in html for token in required_tokens):
        return fail("HTML must expose every active-run ID, scope, case, and artifact")

    superseded_artifacts = [
        result["artifact"]
        for run in source["runs"]
        if run["status"] == "superseded"
        for case in run["cases"]
        for result in (case["baseline"], case["candidate"])
    ]
    if any(artifact in html for artifact in superseded_artifacts):
        return fail("superseded-run artifacts must not be mixed into the active comparison")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
