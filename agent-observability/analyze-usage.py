#!/usr/bin/env python3
"""Find evidence to review in real usage logs; do not infer skill usefulness."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_contracts import load_catalog
from usage_events import build_turns, parse_time, turn_outcome
from usage_input import read_usage
from usage_cases import case_candidates, load_cases, save_candidates
from usage_reviews import attach_reviews, observation_version, save_review


VERSION = re.compile(r"sha256:[0-9a-f]{64}\Z")
OUTCOMES = {
    "検証済み": "reported_passed", "検証失敗": "reported_failed",
    "未検証": "unverified", "終了記録なし": "no_end", "旧形式": "legacy",
}
def read_events(root, days, now):
    data = read_usage(root, days, now)
    return data["events"], data["errors"]


def observed_version(events, skill):
    activations = [e for e in events if e.get("event") == "skill_activated" and e.get("skill") == skill]
    versions = sorted({e["skill_version"] for e in activations
                       if isinstance(e.get("skill_version"), str) and VERSION.fullmatch(e["skill_version"])})
    missing_reads = any(e.get("invocation") == "read" and not VERSION.fullmatch(str(e.get("skill_version", "")))
                        for e in activations)
    return (versions[0] if len(versions) == 1 and not missing_reads else None), versions, missing_reads


def analyze(root, *, days=30, now=None, catalog=None, skill=None, source="auto", cases_dir=None):
    now = now or datetime.now(timezone.utc)
    catalog = catalog if catalog is not None else load_catalog()
    data = read_usage(root, days, now, source)
    events, errors = data["events"], data["errors"]
    turns = build_turns(events)
    activations = [e for e in events if e.get("event") == "skill_activated"]
    verifications = [e for e in events if e.get("event") == "verification_finished"]
    quality = {
        "invalid_rows_or_files": len(errors),
        "analysis_limit_rows": len(data["limitations"]),
        "skill_evidence": dict(Counter(e.get("skill_evidence", "legacy") for e in activations)),
        "branch_observations_excluded": sum(bool(e.get("branch_unverified")) for e in events),
        "read_activations_without_version": sum(
            e.get("invocation") == "read" and not VERSION.fullmatch(str(e.get("skill_version", "")))
            for e in activations
        ),
        "activations_without_turn_id": sum(not e.get("turn_id") for e in activations),
        "unmapped_skill_names": sorted({str(e.get("skill")) for e in activations if e.get("skill") not in catalog}),
        "verification_results_without_evidence_kind": sum(not e.get("result_evidence") for e in verifications),
        "unconfirmed_verification_results": sum(e.get("status") == "unknown" for e in verifications),
    }
    cohorts, candidates = {}, []
    for turn in turns:
        selected = turn.skills & {skill} if skill else turn.skills
        if not selected:
            continue
        models = sorted({str(e["model"]) for e in turn.observations if e.get("model")})
        model = models[0] if len(models) == 1 else None
        outcome = OUTCOMES[turn_outcome(turn)]
        versions = {name: observed_version(turn.observations, name) for name in sorted(turn.skills)}
        reasons = []
        if not turn.start_observed:
            reasons.append("missing_turn_start")
        if not turn.ended:
            reasons.append("missing_turn_end")
        if model is None:
            reasons.append("unknown_or_mixed_model")
        if any(versions[name][0] is None for name in selected):
            reasons.append("unknown_or_mixed_skill_version")
        if any(name not in catalog for name in selected):
            reasons.append("skill_not_in_current_catalog")
        if len(turn.skills) > 1:
            reasons.append("multiple_skills_in_turn")
        if "failed" in turn.verification_status.values():
            reasons.append("verification_failed")
        if any(e.get("status") == "unknown" for e in turn.observations if e.get("event") == "verification_finished"):
            reasons.append("verification_result_unconfirmed")
        if any(not e.get("result_evidence") for e in turn.observations if e.get("event") == "verification_finished"):
            reasons.append("historical_verification_without_evidence_kind")
        evidence = [ref for e in turn.observations if e.get("event") in {
            "agent_started", "skill_activated", "verification_finished", "agent_end",
        } for ref in e.get("_evidence", [e["_source"]] if "_source" in e else [])]
        evidence = list({json.dumps(ref, sort_keys=True): ref for ref in evidence}.values())
        identity = [turn.agent, turn.session_id, turn.agent_id,
                    None if turn.turn_id_inferred else turn.turn_id, turn.started.isoformat()]
        candidate = {
            "id": hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:20],
            "agent": turn.agent, "model": model, "observed_models": models,
            "session_id": turn.session_id, "agent_id": turn.agent_id, "turn_id": turn.turn_id,
            "turn_id_inferred": turn.turn_id_inferred,
            "started_at": turn.started.isoformat(), "ended_at": turn.ended.isoformat() if turn.ended else None,
            "skills": [{"name": name, "version": versions[name][0], "observed_versions": versions[name][1],
                        "reads_without_version": versions[name][2]}
                       for name in sorted(turn.skills)],
            "work_verification": outcome, "review_reasons": reasons or ["sample_for_content_review"],
            "evidence": evidence,
            "usefulness": "not_assessed",
        }
        candidates.append(candidate)
        for name in selected:
            version, observed, missing_reads = versions[name]
            # Multiple versions are kept separate from missing versions.
            key = (name, turn.agent, tuple(models), tuple(observed), missing_reads)
            row = cohorts.setdefault(key, {
                "skill": name, "source": catalog.get(name, {}).get("source", "unmapped"),
                "agent": turn.agent, "model": model, "observed_models": models,
                "skill_version": version, "observed_versions": observed, "reads_without_version": missing_reads,
                "turns": 0, "turns_with_other_skills": 0,
                "work_verification": Counter(), "example_ids": [], "usefulness": "not_assessed",
            })
            row["turns"] += 1
            row["turns_with_other_skills"] += len(turn.skills) > 1
            row["work_verification"][outcome] += 1
            if len(row["example_ids"]) < 3:
                row["example_ids"].append(candidate["id"])
    # This orders review work, not the value or quality of a skill.
    candidates.sort(key=lambda item: (
        "verification_failed" in item["review_reasons"],
        "verification_result_unconfirmed" in item["review_reasons"],
        parse_time(item["started_at"]), item["id"],
    ), reverse=True)
    latest = parse_time(events[-1]["ts"]) if events else None
    skill_turns = Counter(name for candidate in candidates for name in
                          {row["name"] for row in candidate["skills"]})
    review_summary = attach_reviews(root, [work for work in candidates if work['ended_at']
        and work['work_verification'] != 'legacy' and any(s['name'] in catalog for s in work['skills'])])
    cases, case_errors = load_cases(cases_dir or Path(__file__).resolve().parents[1] / '.agents/evals')
    proposals = case_candidates(candidates, catalog, cases, skill)
    if case_errors:
        for proposal in proposals:
            proposal['missing_scenarios'] = None
    return {
        "schema_version": 1,
        "generated_at": now.isoformat(), "window_start": (now - timedelta(days=days)).isoformat(),
        "event_root": str(root), "selected_skill": skill,
        "source": data["source"], "collection": data["collection"],
        "coverage": {
            "events": len(events), "skill_activations": len(activations),
            "observed_turns": len(turns), "reviewable_turns": len(candidates),
            "latest_event_at": latest.isoformat() if latest else None,
            "hours_since_latest_event": round((now - latest).total_seconds() / 3600, 1) if latest else None,
            "agents": dict(Counter(str(e.get("agent", "unknown")) for e in events)),
        },
        "data_quality": quality, "input_errors": errors,
        "input_error_counts": dict(Counter(e["reason"] for e in errors)),
        "input_limitations": data["limitations"],
        "input_limitation_counts": dict(Counter(e["reason"] for e in data["limitations"])),
        "work_summary": {
            "turns_with_skills": len(candidates),
            "outcomes": dict(Counter(candidate["work_verification"] for candidate in candidates)),
            "by_agent": dict(Counter(candidate["agent"] for candidate in candidates)),
            "top_skills": [{"skill": name, "turns": count} for name, count in
                           sorted(skill_turns.items(), key=lambda item: (-item[1], item[0]))[:5]],
        },
        "cohorts": sorted(cohorts.values(), key=lambda row: (-row["turns"], row["skill"], row["agent"], str(row["model"]))),
        "review_candidates": candidates,
        "evaluation_candidates": proposals,
        "case_catalog_errors": case_errors,
        "case_review_summary": review_summary,
        "limitations": [
            "Events identify reported activity, not whether a skill was appropriate or caused an outcome.",
            "Read the original conversation and user feedback before assessing usefulness; prompts are not collected here.",
            "Reported historical verification success may lack exit-status evidence; missing fields are not reconstructed.",
            "Skill versions hash SKILL.md only, not the complete bundle or references.",
            "Native usage totals require a confirmed skill read; requests and explicit mentions are reported separately.",
            "Forked histories with unverified origins are excluded from skill usage totals.",
            "Collection health distinguishes source freshness from activity; incomplete parsing can still miss activity.",
        ],
    }


def review_template(candidate):
    template = {
        "schema_version": 1, "observation": candidate, "observation_version": observation_version(candidate),
        "expected_review_version": None,
        "reviewer": {"kind": "", "name": ""},
        "conversation_evidence": [],
        "assessment": {
            "context": "unassessed", "applicability": "unassessed", "contribution": "unassessed",
            "reason": "", "alternative_explanations": [],
        },
        "improvement": {
            "hypothesis": "", "skill_section": "", "expected_behavior": "",
            "synthetic_case": "", "next_action": "",
        },
        "result": {"outcome": None, "summary": None},
        "design": {"action": None, "reason": None, "problem": None, "expected_behavior": None,
                   "case": None, "next_action": None},
    }
    path = candidate.get('case_review', {}).get('path')
    if path:
        raw = Path(path).read_bytes()
        try:
            previous = json.loads(raw)
        except (ValueError, UnicodeError):
            previous = None
        if isinstance(previous, dict):
            template.update(previous)
        template.update(observation=candidate, observation_version=observation_version(candidate),
                        expected_review_version=hashlib.sha256(raw).hexdigest())
    return template


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(os.environ.get(
        "AGENT_OBSERVABILITY_DIR", str(Path.home() / ".local/share/agent-observability"))))
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--skill")
    parser.add_argument("--source", choices=("auto", "native", "legacy"), default="auto")
    parser.add_argument("--limit", type=int, default=10, help="Maximum work and evaluation candidates displayed; counts and saved snapshot remain complete")
    parser.add_argument("--all-errors", action="store_true", help="Include every input error reference (default: first 50)")
    parser.add_argument("--review-template", metavar="ID", help="Print an unscored review record for a candidate ID")
    parser.add_argument("--cases", type=Path, help="Local evaluation case directory")
    parser.add_argument("--prepare-cases", action="store_true", help="Refresh the local, unassessed evaluation-candidate snapshot")
    parser.add_argument("--case-proposal", metavar="ID", help="Print evidence and design fields for an evaluation candidate")
    parser.add_argument("--save-review", type=Path, help="Validate and save a completed work review, result and case design")
    args = parser.parse_args()
    if args.days < 1 or args.limit < 1:
        parser.error("--days and --limit must be positive")
    root = args.root.expanduser().resolve()
    if not (root / "events").is_dir() and not (root / "usage.sqlite3").exists():
        parser.error("no saved usage data: " + str(root))
    if sum(bool(value) for value in (args.review_template, args.case_proposal, args.save_review)) > 1:
        parser.error("choose one of --review-template, --case-proposal or --save-review")
    result = analyze(root, days=args.days, skill=args.skill, source=args.source, cases_dir=args.cases)
    input_failed = result["source"] == "native" and result["collection"]["state"] in {"unreadable", "not_started"}
    if args.save_review:
        try:
            path = save_review(root, json.loads(args.save_review.expanduser().read_text()), result['review_candidates'])
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            parser.error(str(error))
        print(json.dumps({'state': 'saved', 'path': str(path)}, ensure_ascii=False))
        return 0
    if args.prepare_cases and not input_failed:
        try:
            path = save_candidates(root, result)
            result['case_preparation'] = {'state': 'updated', 'path': str(path)}
        except OSError as error:
            result['case_preparation'] = {'state': 'failed', 'reason': type(error).__name__}
    if args.case_proposal:
        candidate = next((c for c in result['evaluation_candidates'] if c['id'] == args.case_proposal), None)
        if candidate is None:
            parser.error('evaluation candidate not found in this window and skill selection')
        result = {
            'schema_version': 1, 'status': candidate['status'], 'candidate': candidate,
            'source': result['source'], 'window_start': result['window_start'], 'generated_at': result['generated_at'],
            'observations': [review_template(work) for work in result['review_candidates'] if work['id'] in candidate['examples']],
            'reviewed_work': [work['case_review'] for work in result['review_candidates'] if work['id'] in candidate['reviewed_examples']],
            'admission_checks': ['Review original context: real work, evaluation setup, or expected red test?',
                                 'Check related cases for the same behavior; matching skill names do not establish coverage.',
                                 'Use a synthetic fixture without private code, prompts, credentials, network or clock dependencies.',
                                 'Verify original fails, minimal fix and another valid solution pass; then run eval --dry-run.'],
        }
    elif args.review_template:
        candidate = next((c for c in result["review_candidates"] if c["id"] == args.review_template), None)
        if candidate is None:
            parser.error("candidate not found in this window and skill selection")
        result = review_template(candidate)
    else:
        result["candidates_truncated"] = len(result["review_candidates"]) > args.limit
        result["review_candidates"] = result["review_candidates"][:args.limit]
        result['evaluation_candidate_count'] = len(result['evaluation_candidates'])
        result['evaluation_candidates'] = result['evaluation_candidates'][:args.limit]
        result["input_errors_truncated"] = not args.all_errors and len(result["input_errors"]) > 50
        if not args.all_errors:
            result["input_errors"] = result["input_errors"][:50]
            result["input_limitations_truncated"] = len(result["input_limitations"]) > 50
            result["input_limitations"] = result["input_limitations"][:50]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if input_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
