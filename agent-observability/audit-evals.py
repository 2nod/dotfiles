#!/usr/bin/env python3
"""Audit purpose-aligned evidence. Never disable skills or retire cases automatically."""

from __future__ import annotations
import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from eval_contracts import (
    load_catalog,
    skill_summary,
    case_verdict,
    contract_version,
    reviewed_result,
)


def results(root):
    observed = []
    for path in sorted((root / "eval-results").glob("*.jsonl")):
        for line in path.read_text().splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict):
                observed.append(reviewed_result(item))
    return observed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[1] / ".agents/evals",
    )
    parser.add_argument(
        "--results",
        type=pathlib.Path,
        default=pathlib.Path(
            os.environ.get(
                "AGENT_OBSERVABILITY_DIR",
                str(pathlib.Path.home() / ".local/share/agent-observability"),
            )
        ),
    )
    parser.add_argument("--catalog", type=pathlib.Path)
    parser.add_argument("--min-runs", type=int, default=3)
    parser.add_argument(
        "--skills",
        action="store_true",
        help="Show all skills, coverage, purpose and script candidates",
    )
    parser.add_argument(
        "--changes",
        action="store_true",
        help="Persist a snapshot and print meaningful changes only; implies --skills",
    )
    args = parser.parse_args()
    cases = {}
    broken = []
    for path in sorted(args.cases.glob("*.json")):
        try:
            case = json.loads(path.read_text())
            cases[case["id"]] = case
        except (OSError, ValueError, KeyError, TypeError) as exc:
            broken.append({"case": path.stem, "status": "hold", "reason": str(exc)})
    observed = results(args.results)
    if args.skills or args.changes:
        report = skill_summary(load_catalog(args.catalog), cases, observed, args.cases)
        if broken:
            report.append(
                {"skill": "invalid-cases", "recommendation": "hold", "cases": broken}
            )
    else:
        report = broken
        for id, case in cases.items():
            try:
                version = contract_version(case, args.cases / (id + ".json"))
            except (OSError, KeyError, TypeError):
                version = "invalid"
            items = [r for r in observed if r.get("case") == id]
            status, reason, count = case_verdict(
                case, items, max(1, args.min_runs), version
            )
            report.append(
                {"case": id, "status": status, "reason": reason, "pairs": count}
            )
    if args.changes:
        state = args.results / "skill-monitor.json"
        current = {r["skill"]: r for r in report}
        # Include file fingerprints: changed skill content invalidates prior evidence even without new results.
        from eval_contracts import tree_version

        for name, row in current.items():
            if row.get("path"):
                path = (
                    args.catalog or args.cases.parent / "eval-catalog.json"
                ).parent / row["path"]
                row["version"] = tree_version(path.parent)
        try:
            previous = json.loads(state.read_text())
        except (OSError, ValueError):
            previous = {}
        changed = [
            {"skill": name, "before": previous.get(name), "after": current.get(name)}
            for name in sorted(previous.keys() | current.keys())
            if previous.get(name) != current.get(name)
        ]
        state.parent.mkdir(parents=True, exist_ok=True)
        temporary = state.with_suffix(".tmp")
        temporary.write_text(json.dumps(current, ensure_ascii=False, indent=2))
        temporary.replace(state)
        report = {"initial_snapshot": not bool(previous), "changes": changed}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
