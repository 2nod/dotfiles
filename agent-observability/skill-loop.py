#!/usr/bin/env python3
"""Evidence gates for skill improvement. State is local; no automatic adoption."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from comparison_checks import efficiency_passes

from eval_contracts import (
    REPO,
    contract_version,
    load_catalog,
    reviewed_result,
    tree_version,
)


def read(path):
    return json.loads(path.read_text())


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def required(obj, keys, prefix, errors):
    if not isinstance(obj, dict):
        errors.append(f"{prefix}: object required")
        return
    for key in keys:
        if not isinstance(obj.get(key), str) or not obj[key].strip():
            errors.append(f"{prefix}.{key}: 記録が必要")


def human_review_errors(decision, measurements):
    review = decision.get("human_review", {})
    errors = []
    required(review, ["reviewer", "evidence", "conclusion"], "human_review", errors)
    if not isinstance(review, dict):
        return errors
    if review.get("kind") != "human" or review.get("action") != decision.get("action"):
        errors.append("human_review: 対象の採否について人手の比較レビューが必要")
    expected = {row.get("artifact_version") for pair in measurements for row in pair.values()}
    versions = review.get("artifact_versions")
    if (not expected or None in expected or not isinstance(versions, list)
            or any(not isinstance(v, str) for v in versions) or set(versions) != expected):
        errors.append("human_review: 比較した全成果物の版を記録してください")
    return errors


def validate(plan, stage="plan"):
    if not isinstance(plan, dict):
        return ["plan: object required"]
    errors = []
    required(plan, ["skill", "purpose", "model", "scope", "reviewer"], "plan", errors)
    if plan.get("mode") not in ("screen", "validate"):
        errors.append("mode: screen または validate")
    runs = plan.get("runs")
    if type(runs) is not int or runs < (3 if plan.get("mode") == "validate" else 1):
        errors.append("runs: screen は1以上、validate は3以上")
    cases = plan.get("cases", [])
    if not isinstance(cases, list) or not cases:
        return errors + ["cases: 1件以上必要"]
    seen, scenarios, loaded = set(), set(), []
    for entry in cases:
        if not isinstance(entry, dict):
            errors.append("case: object required")
            continue
        required(
            entry,
            ["path", "contract_version", "alignment", "verifier_evidence"],
            "case",
            errors,
        )
        try:
            path = pathlib.Path(entry["path"])
            case = read(path)
            if case["id"] in seen:
                errors.append("case: 重複")
            seen.add(case["id"])
            if case["skill"] != plan.get("skill"):
                errors.append("case: 対象skillが異なる")
            if case.get("evaluation", {}).get("status") != "ready" or not case.get(
                "rubric"
            ):
                errors.append("case: 目的別rubricを持つreadyケースが必要")
            if contract_version(case, path) != entry.get("contract_version"):
                errors.append(f"{case['id']}: 評価条件が更新済み。新しい計画を作成")
            if entry.get("holdout") and plan.get("lineage"):
                fixture_hash = tree_version((path.parent / case["fixture"]).resolve())
                if fixture_hash in plan["lineage"].get("exposed_fixtures", []):
                    errors.append(f"{case['id']}: previously used fixture cannot be a holdout")
            scenarios.add(case.get("scenario"))
            loaded.append((entry, case))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"case: {exc}")
    invocations = {case.get("invocation", "explicit") for _, case in loaded}
    if len(invocations) > 1 or invocations - {"explicit", "catalog"}:
        errors.append("invocation: 明示注入とカタログ選択を別の計画に分けてください")
    if plan.get("invocation") is not None and invocations != {plan["invocation"]}:
        errors.append("invocation: 計画とケースの呼び出し方法が不一致")
    candidate = plan.get("candidate")
    if candidate:
        if load_catalog().get(plan.get("skill"), {}).get("source") == "installed":
            errors.append("candidate: installed skills are usage-only")
        try:
            path = pathlib.Path(candidate["path"])
            if not path.is_file() or tree_version(path.parent) != candidate["version"]:
                errors.append("candidate: 内容が更新済み、または存在しない")
        except (KeyError, TypeError, OSError) as exc:
            errors.append(f"candidate: {exc}")
        required(
            plan.get("diagnosis", {}),
            ["cause", "evidence", "change"],
            "diagnosis",
            errors,
        )
        extraction = plan.get("script_review", {})
        if not isinstance(extraction, dict) or extraction.get("decision") not in ("extract", "defer"):
            errors.append("script_review.decision: extract または defer")
        required(extraction, ["reason"], "script_review", errors)
        if isinstance(extraction, dict) and extraction.get("decision") == "extract":
            required(extraction, ["input_output", "failure", "idempotence", "verification"], "script_review", errors)
    efficiency = plan.get("efficiency")
    if efficiency is not None:
        if not isinstance(efficiency, dict):
            errors.append("efficiency: object required")
        else:
            if efficiency.get("metric") not in ("total_tokens", "duration_seconds"):
                errors.append("efficiency.metric: total_tokens or duration_seconds")
            threshold = efficiency.get("minimum_reduction")
            if type(threshold) not in (int, float) or not 0 < threshold < 1:
                errors.append("efficiency.minimum_reduction: fraction strictly between 0 and 1")
            required(efficiency, ["quality_evidence", "rationale"], "efficiency", errors)
    if plan.get("mode") == "validate":
        if not {"typical", "boundary", "negative"} <= scenarios:
            errors.append("validate: typical / boundary / negative が必要")
        if candidate and not any(isinstance(e, dict) and e.get("holdout") is True for e in cases):
            errors.append("validate: 修正に使っていないholdoutが必要")
    cost = len(cases) * (runs if type(runs) is int else 0) * (3 if candidate else 2)
    if (
        type(plan.get("max_calls")) is not int
        or cost > plan["max_calls"]
        or plan["max_calls"] <= 0
    ):
        errors.append(f"max_calls: 必要呼び出し数 {cost} を満たす上限が必要")
    if stage == "plan" or errors:
        return errors
    # The launcher freezes the reviewed plan before the first model call.
    root = pathlib.Path(plan["_directory"])
    try:
        frozen = read(root / "started.json")
        if frozen != {k: v for k, v in plan.items() if k != "_directory"}:
            errors.append("plan: 実行開始後に計画が変更された")
    except (OSError, ValueError):
        errors.append("started.json: 実行記録がない")
    all_pairs = []
    measurements = []
    conditions = set()
    for entry, case in loaded:
        try:
            items = [
                reviewed_result(json.loads(line))
                for line in (root / f"{case['id']}.jsonl").read_text().splitlines()
            ]
            expected = {
                (run, variant)
                for run in range(1, runs + 1)
                for variant in ("control", "treatment", "candidate")[
                    : 3 if candidate else 2
                ]
            }
            keys = [(x.get("run"), x.get("variant")) for x in items]
            if set(keys) != expected or len(keys) != len(expected):
                errors.append(f"{case['id']}: 比較組の欠落または重複")
                continue
            if len({x.get("experiment_id") for x in items}) != 1 or not items[0].get(
                "experiment_id"
            ):
                errors.append(f"{case['id']}: experiment_id が混在または不明")
            for item in items:
                conditions.add(
                    (item.get("model"), item.get("agent"), item.get("agent_version"))
                )
                if item.get("rubric") != case["rubric"]:
                    errors.append(f"{case['id']}: 採点基準が不一致")
                if (
                    item.get("case") != case["id"]
                    or item.get("model") != plan["model"]
                    or item.get("contract_version") != entry["contract_version"]
                    or item.get("invocation", "explicit") != case.get("invocation", "explicit")
                ):
                    errors.append(f"{case['id']}: 対象または実行条件が不一致")
                if candidate and item.get("candidate_version") != candidate["version"]:
                    errors.append(f"{case['id']}: 修正版の版が不一致")
                if item.get("failure_kind") in (
                    "timeout",
                    "agent_failed",
                    "verifier_error",
                ):
                    errors.append(f"{case['id']}: 環境エラーの解消が必要")
                if type(item.get("success")) is not bool:
                    errors.append(f"{case['id']}: 成果物とtraceの証拠付き採点が未完了")
            for run in range(1, runs + 1):
                measurements.append({x["variant"]: x for x in items if x["run"] == run})
                all_pairs.append(
                    {x["variant"]: x.get("success") for x in items if x["run"] == run}
                )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"{case['id']}: {exc}")
    if len(conditions) != 1 or any(not all(c) for c in conditions):
        errors.append("model / agent / agent_version: 条件混在または不明")
    if stage == "review" or errors:
        return errors
    decision = read(root / "decision.json")
    required(
        decision,
        ["action", "reason", "evidence", "reviewer", "limitations", "next_check"],
        "decision",
        errors,
    )
    action = decision.get("action")
    if action not in ("keep", "revise", "disable", "hold", "adopt"):
        errors.append("decision.action: keep / revise / disable / hold / adopt")
    if action in ("keep", "disable", "adopt") and plan["mode"] != "validate":
        errors.append("screenから採用、継続、無効化は判断できない")
    if action in ("keep", "adopt", "disable") and load_catalog().get(plan.get("skill"), {}).get("human_review_required"):
        errors.extend(human_review_errors(decision, measurements))
    if action == "adopt":
        if not candidate:
            errors.append("adopt: 修正版が必要")
        elif not all(p.get("candidate") is True for p in all_pairs) or not (
            any(p.get("treatment") is False for p in all_pairs)
            or efficiency_passes(efficiency, measurements)
        ):
            errors.append("adopt: 全ケース達成と現行に対する改善の証拠が必要")
    if action == "keep" and (
        not all(p.get("treatment") is True for p in all_pairs)
        or not any(p.get("control") is False for p in all_pairs)
    ):
        errors.append("keep: 全ケース達成と無効条件に対する改善の証拠が必要")
    if action == "disable":
        required(
            decision, ["alternative", "exceptions", "rollback"], "decision", errors
        )
        if not all(p.get("control") is True for p in all_pairs):
            errors.append("disable: skillなしでの目的達成が必要")
    return errors


def launch(plan, directory):
    errors = validate(plan)
    if errors:
        raise ValueError("\n".join(errors))
    # Exclusive create reserves the entire call budget. Interrupted runs never auto-retry.
    write_new(directory / "started.json", plan)
    for entry in plan["cases"]:
        case = read(pathlib.Path(entry["path"]))
        command = [
            sys.executable,
            str(REPO / "agent-observability/evaluate-skill.py"),
            entry["path"],
            "--model",
            plan["model"],
            "--runs",
            str(plan["runs"]),
        ]
        if plan.get("candidate"):
            command += ["--candidate", plan["candidate"]["path"]]
        with (
            (directory / f"{case['id']}.jsonl").open("x") as out,
            (directory / f"{case['id']}.stderr").open("x") as err,
        ):
            result = subprocess.run(
                command,
                stdout=out,
                stderr=err,
                timeout=plan["runs"] * (3 if plan.get("candidate") else 2) * 360 + 120,
            )
        if result.returncode:
            raise ValueError(f"{case['id']}: runner失敗。自動再実行せずログを確認")
    write_new(directory / "completed.json", {"cases": len(plan["cases"])})



def status(directory):
    """Derive the next action from evidence, without model calls or state writes."""
    plan = read(directory / "plan.json")
    errors = validate(plan)
    state, action = "ready", "run"
    if errors:
        state, action = "needs-plan", "repair-plan"
    elif (directory / "started.json").exists():
        plan["_directory"] = str(directory)
        if not (directory / "completed.json").exists():
            state, action = "execution-incomplete", "inspect-logs-no-retry"
        else:
            errors = validate(plan, "review")
            state, action = "needs-review", "review-artifacts-and-trace"
            if not errors:
                if not (directory / "decision.json").exists():
                    state, action = "needs-decision", "record-decision"
                else:
                    errors = validate(plan, "decision")
                    state, action = ("needs-decision", "repair-decision") if errors else ("decided", "next-round-or-stop")
    return {"directory": str(directory), "skill": plan.get("skill"),
            "state": state, "next_action": action, "errors": errors,
            "planned_calls": len(plan.get("cases", [])) * (plan.get("runs") if type(plan.get("runs")) is int else 0) * (3 if plan.get("candidate") else 2),
            "model_execution": "explicit-run-only"}


def next_round(directory, destination, candidate=None):
    """Create an editable, unstarted draft; never copy results or author judgments."""
    if status(directory)["state"] != "decided":
        raise ValueError("next: previous round must pass review and decision gates")
    plan = read(directory / "plan.json")
    catalog = load_catalog()
    if candidate and catalog.get(plan["skill"], {}).get("source") == "installed":
        raise ValueError("next: installed skills are usage-only; do not attach a local candidate")
    exposed = set(plan.get("lineage", {}).get("exposed_fixtures", []))
    for entry in plan["cases"]:
        path = pathlib.Path(entry["path"])
        case = read(path)
        exposed.add(tree_version((path.parent / case["fixture"]).resolve()))
        entry["contract_version"] = contract_version(case, path)
        entry["holdout"] = False
    plan["lineage"] = {"parent": str(directory), "exposed_fixtures": sorted(exposed),
                       "parent_decision": read(directory / "decision.json")}
    plan.update(mode="screen", runs=1, diagnosis={}, script_review={})
    plan.pop("efficiency", None)
    if candidate:
        candidate = candidate.resolve()
        if not candidate.is_file():
            raise ValueError("candidate must be an existing SKILL.md file")
        plan["candidate"] = {"path": str(candidate), "version": tree_version(candidate.parent)}
    else:
        plan["candidate"] = None
    plan["max_calls"] = len(plan["cases"]) * (3 if candidate else 2)
    plan["scope"] = ""
    # A draft is deliberately not executable until purpose/scope and diagnosis are reviewed.
    destination.mkdir(parents=True, exist_ok=False)
    write_new(destination / "plan.json", plan)
    return status(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "check", "run", "status", "next", "report", "review-template", "review"])
    parser.add_argument("directory", type=pathlib.Path)
    parser.add_argument("--skill")
    parser.add_argument("--case")
    parser.add_argument("--run", type=int)
    parser.add_argument("--variant", choices=["control", "treatment", "candidate"])
    parser.add_argument("--review-file", type=pathlib.Path)
    parser.add_argument("--to", type=pathlib.Path)
    parser.add_argument("--candidate", type=pathlib.Path)
    parser.add_argument("--model")
    parser.add_argument("--invocation", choices=["explicit", "catalog"], default="explicit")
    parser.add_argument(
        "--stage", choices=["plan", "review", "decision"], default="plan"
    )
    args = parser.parse_args()
    try:
        directory = args.directory.expanduser().resolve()
        if args.command in ("report", "review-template", "review"):
            from loop_reports import report, select_result, review_template, save_review
            plan = read(directory / "plan.json")
            if args.command == "report":
                output = report(directory, plan, status(directory))
            else:
                row = select_result(directory, plan, args.case, args.run, args.variant)
                if args.command == "review-template":
                    output = review_template(row)
                else:
                    if not args.review_file:
                        raise ValueError("review requires --review-file")
                    output = save_review(row, args.review_file)
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0
        if args.command == "status":
            print(json.dumps(status(directory), ensure_ascii=False, indent=2))
            return 0
        if args.command == "next":
            if not args.to:
                raise ValueError("next requires --to <new directory>")
            print(json.dumps(next_round(directory, args.to.expanduser().resolve(), args.candidate), ensure_ascii=False, indent=2))
            return 0
        if args.command == "init":
            if not args.model:
                raise ValueError("init requires an explicit --model")
            catalog = load_catalog()
            if args.skill not in catalog:
                raise ValueError("--skill に台帳のskill名を指定")
            cases = []
            for path in sorted((REPO / ".agents/evals").glob("*.json")):
                case = read(path)
                if (
                    case.get("skill") == args.skill
                    and case.get("evaluation", {}).get("status") == "ready"
                    and case.get("invocation", "explicit") == args.invocation
                    and (not args.case or case.get("id") == args.case)
                ):
                    cases.append(
                        {
                            "path": str(path),
                            "contract_version": contract_version(case, path),
                            "alignment": "",
                            "verifier_evidence": "",
                            "holdout": False,
                        }
                    )
            if not cases:
                raise ValueError("No ready cases match skill / invocation / case")
            write_new(
                directory / "plan.json",
                {
                    "schema": 1,
                    "skill": args.skill,
                    "purpose": catalog[args.skill]["purpose"],
                    "scope": "",
                    "reviewer": "",
                    "mode": "screen",
                    "model": args.model,
                    "invocation": args.invocation,
                    "runs": 1,
                    "max_calls": 2 * len(cases),
                    "cases": cases,
                    "candidate": None,
                    "diagnosis": {},
                    "script_review": {},
                },
            )
            print(f"{directory}/plan.json を記入して check を実行")
            return 0
        plan = read(directory / "plan.json")
        if args.command == "run":
            launch(plan, directory)
            return 0
        plan["_directory"] = str(directory)
        errors = validate(plan, args.stage)
        print(
            json.dumps(
                {"stage": args.stage, "ok": not errors, "errors": errors},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if errors else 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(
            json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
