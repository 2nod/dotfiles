#!/usr/bin/env python3
"""Classify eval cases without deleting them."""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
from collections import defaultdict
from typing import cast


def results(root: pathlib.Path) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for path in (root / "eval-results").glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and isinstance(item.get("case"), str):
                grouped[item["case"]].append(cast(dict[str, object], item))
    return grouped


def latest_experiment(observed: list[dict[str, object]]) -> list[dict[str, object]]:
    experiment_ids = {
        str(item["experiment_id"])
        for item in observed
        if isinstance(item.get("experiment_id"), str)
    }
    if not experiment_ids:
        return observed
    groups = [
        [item for item in observed if item.get("experiment_id") == experiment_id]
        for experiment_id in experiment_ids
    ]
    return max(groups, key=lambda group: max(str(item.get("ts", "")) for item in group))


def median(observed: list[dict[str, object]], key: str) -> float | None:
    values = [
        value for item in observed if isinstance((value := item.get(key)), (int, float))
    ]
    try:
        return float(statistics.median(values)) if values else None
    except statistics.StatisticsError:
        return None


def classify(
    case_path: pathlib.Path,
    observed: list[dict[str, object]],
    min_runs: int,
) -> tuple[str, str]:
    try:
        case = json.loads(case_path.read_text(encoding="utf-8"))
        if not isinstance(case, dict):
            raise ValueError("case must be an object")
        for key in ("id", "skill", "skill_path", "fixture", "prompt", "verifiers"):
            if not case.get(key):
                raise ValueError(f"missing {key}")
        fixture = (case_path.parent / str(case["fixture"])).resolve()
        skill = (case_path.parent / str(case["skill_path"])).resolve()
        if not fixture.is_dir() or not skill.is_file():
            return "review", "broken: fixture or skill path is missing"
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return "review", f"broken: {exc}"

    control = [item for item in observed if item.get("variant") == "control"]
    treatment = [item for item in observed if item.get("variant") == "treatment"]
    if min(len(control), len(treatment)) < min_runs:
        return "review", f"need {min_runs} control and treatment runs"
    control_rate = sum(bool(item.get("success")) for item in control) / len(control)
    treatment_rate = sum(bool(item.get("success")) for item in treatment) / len(
        treatment
    )
    if treatment_rate > control_rate:
        return "keep", "treatment improves success rate"
    if treatment_rate < control_rate:
        return "review", "treatment underperforms control"
    successful_control = [item for item in control if bool(item.get("success"))]
    successful_treatment = [item for item in treatment if bool(item.get("success"))]
    improved_metrics = [
        key
        for key in ("changed_lines", "classes_added")
        if (control_value := median(successful_control, key)) is not None
        and (treatment_value := median(successful_treatment, key)) is not None
        and treatment_value < control_value
    ]
    if improved_metrics:
        return "keep", f"treatment reduces {', '.join(improved_metrics)}"
    return "retire", "no measured advantage after sufficient runs"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases", type=pathlib.Path, default=pathlib.Path(".agents/evals")
    )
    parser.add_argument("--results", type=pathlib.Path, default=None)
    parser.add_argument("--min-runs", type=int, default=3)
    args = parser.parse_args()
    cases_dir = args.cases.expanduser().resolve()
    root = (
        (args.results or pathlib.Path.home() / ".local/share/agent-observability")
        .expanduser()
        .resolve()
    )
    observed = results(root)
    report = []
    for case_path in sorted(cases_dir.glob("*.json")):
        try:
            case_id = str(
                json.loads(case_path.read_text(encoding="utf-8")).get(
                    "id", case_path.stem
                )
            )
        except (OSError, json.JSONDecodeError, AttributeError):
            case_id = case_path.stem
        case_results = latest_experiment(observed.get(case_id, []))
        control_runs = sum(item.get("variant") == "control" for item in case_results)
        treatment_runs = sum(
            item.get("variant") == "treatment" for item in case_results
        )
        status, reason = classify(case_path, case_results, max(1, args.min_runs))
        report.append(
            {
                "case": case_id,
                "status": status,
                "reason": reason,
                "runs": {"control": control_runs, "treatment": treatment_runs},
                "path": str(case_path),
            }
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
