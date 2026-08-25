#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import sys


SUMMARY = {
    "foundation_checks": {
        "checkpointless_boot": True,
        "deterministic_artifact": True,
        "updated_policy_rerollout": True,
        "fallback": True,
        "seed_split": True,
    },
    "initial_mean_reward": 0.0,
    "final_mean_reward": 0.0,
    "baseline_mean_reward": 0.0,
    "candidate_gate": {
        "not_below_baseline": True,
        "strictly_better_than_initial": False,
    },
}


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    summary_path = workspace / "summary.json"
    if json.loads(summary_path.read_text(encoding="utf-8")) != SUMMARY:
        return fail("immutable summary.json was changed")

    decision_path = workspace / "decision.json"
    if not decision_path.is_file():
        return fail("decision.json is missing")
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    if decision.get("foundation_decision") != "accept":
        return fail("verified loop foundation must be accepted")
    if decision.get("candidate_decision") != "reject":
        return fail("flat-reward candidate must be rejected")
    if decision.get("next_change") != "opponent":
        return fail("the only next factor must be opponent")
    if set(decision) != {"foundation_decision", "candidate_decision", "next_change"}:
        return fail("decision contains speculative fields")

    allowed = {"summary.json", "decision.json"}
    extras = {path.name for path in workspace.iterdir()} - allowed
    if extras:
        return fail(f"extra scaffolding was added: {sorted(extras)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
