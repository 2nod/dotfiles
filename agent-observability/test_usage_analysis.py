"""Real-usage evidence must remain traceable without becoming a skill score."""
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from usage_events import aggregate, build_turns, turn_outcome


SCRIPT = Path(__file__).with_name("analyze-usage.py")
spec = importlib.util.spec_from_file_location("analyze_usage", SCRIPT)
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)
NOW = datetime(2026, 1, 20, 12, tzinfo=timezone.utc)
VERSION = "sha256:" + "a" * 64
CATALOG = {"guide": {"source": "authored"}, "check": {"source": "installed"}}


class UsageAnalysisTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "events").mkdir()
        self.journal = self.root / "events/sample.jsonl"
        self.sequence = 0

    def event(self, name, **fields):
        self.sequence += 1
        return {
            "ts": (NOW - timedelta(hours=1) + timedelta(seconds=self.sequence)).isoformat(),
            "schema_version": 2, "agent": "codex", "session_id": "session",
            "agent_id": "root", "turn_id": "turn", "model": "model-a", "event": name,
            **fields,
        }

    def turn(self, *, version=VERSION, other_skill=False, status="passed", **fields):
        events = [self.event("agent_started", **fields),
                  self.event("skill_activated", skill="guide", skill_version=version, invocation="read", **fields)]
        if other_skill:
            events.append(self.event("skill_activated", skill="check", skill_version=VERSION, invocation="read", **fields))
        events.extend([
            self.event("verification_finished", **{
                "verification": "test", "status": status,
                "result_evidence": "unconfirmed" if status == "unknown" else "exit_code", **fields,
            }),
            self.event("agent_end", **fields),
        ])
        return events

    def write(self, events):
        self.journal.write_text("".join(json.dumps(event) + "\n" for event in events))

    def analyze(self, **kwargs):
        return usage.analyze(self.root, now=NOW, catalog=CATALOG, **kwargs)

    def test_cohorts_separate_runtime_model_version_and_preserve_co_use(self):
        self.write([
            *self.turn(turn_id="one"),
            *self.turn(turn_id="two", other_skill=True),
            *self.turn(turn_id="three", model="model-b"),
            *self.turn(turn_id="four", version="sha256:" + "b" * 64),
            *self.turn(turn_id="five", agent="pi"),
        ])
        report = self.analyze()
        self.assertEqual(report["coverage"]["reviewable_turns"], 5)
        self.assertEqual(report['work_summary'], {
            'turns_with_skills': 5,
            'outcomes': {'reported_passed': 5},
            'by_agent': {'codex': 4, 'pi': 1},
            'top_skills': [{'skill': 'guide', 'turns': 5}, {'skill': 'check', 'turns': 1}],
        })
        guide = [row for row in report["cohorts"] if row["skill"] == "guide"]
        self.assertEqual(len(guide), 4)
        most_used = guide[0]
        self.assertEqual(most_used["turns"], 2)
        self.assertEqual(most_used["turns_with_other_skills"], 1)
        self.assertEqual(most_used["work_verification"], {"reported_passed": 2})
        self.assertEqual(most_used["usefulness"], "not_assessed")
        filtered = self.analyze(skill="check")
        self.assertEqual(len(filtered["cohorts"]), 1)
        candidate = filtered["review_candidates"][0]
        self.assertEqual({s["name"] for s in candidate["skills"]}, {"guide", "check"})
        self.assertIn("multiple_skills_in_turn", candidate["review_reasons"])

    def test_missing_and_mixed_metadata_is_not_backfilled(self):
        events = self.turn()
        events.insert(2, self.event("skill_activated", skill="guide", invocation="read"))
        events.insert(3, self.event("tool_started", model="model-b"))
        events.extend(self.turn(turn_id="without-version", version=None, model=None))
        self.write(events)
        report = self.analyze()
        self.assertEqual(report["data_quality"]["read_activations_without_version"], 2)
        for row in report["cohorts"]:
            self.assertIsNone(row["skill_version"])
            self.assertIsNone(row["model"])
        mixed = next(c for c in report["review_candidates"] if c["turn_id"] == "turn")
        self.assertEqual(mixed["observed_models"], ["model-a", "model-b"])
        self.assertEqual(mixed["skills"][0]["observed_versions"], [VERSION])
        self.assertTrue(mixed["skills"][0]["reads_without_version"])

    def test_results_distinguish_unconfirmed_failure_and_unsupported_old_success(self):
        self.write([
            *self.turn(turn_id="failed", status="failed"),
            *self.turn(turn_id="pending", status="unknown"),
            *self.turn(turn_id="old", result_evidence=None),
        ])
        report = self.analyze()
        candidates = {c["turn_id"]: c for c in report["review_candidates"]}
        self.assertEqual(candidates["pending"]["work_verification"], "unverified")
        self.assertEqual(candidates["failed"]["work_verification"], "reported_failed")
        self.assertIn("historical_verification_without_evidence_kind", candidates["old"]["review_reasons"])
        self.assertEqual(report["review_candidates"][0]["turn_id"], "failed")
        self.assertEqual(report["data_quality"]["unconfirmed_verification_results"], 1)

    def test_evidence_lines_are_verifiable_and_private_fields_do_not_escape(self):
        events = self.turn(prompt="private prompt", output="private output")
        self.write(events)
        before = self.journal.read_bytes()
        report = self.analyze()
        candidate = report["review_candidates"][0]
        for ref in candidate["evidence"]:
            line = self.journal.read_text().splitlines()[ref["line"] - 1]
            self.assertEqual(ref["path"], str(self.journal))
            self.assertEqual(ref["sha256"], hashlib.sha256(line.encode()).hexdigest())
        review = usage.review_template(candidate)
        self.assertEqual(review["assessment"]["contribution"], "unassessed")
        self.assertEqual(review["conversation_evidence"], [])
        self.assertNotIn("private prompt", json.dumps(review))
        self.assertNotIn("private output", json.dumps(report))
        self.assertEqual(self.journal.read_bytes(), before)

    def test_bad_rows_are_reported_and_valid_evidence_survives(self):
        self.write(self.turn())
        bad = ["not JSON", "[]", json.dumps({"ts": "2026-01-20T11:00:00", "event": "agent_end"}),
               json.dumps(self.event("skill_activated", skill=["guide"])),
               json.dumps(self.event("verification_finished", status=["passed"]))]
        with self.journal.open("a") as journal:
            journal.write("\n".join(bad) + "\n")
        (self.root / "events/unreadable.jsonl").write_bytes(b"\xff")
        report = self.analyze()
        self.assertEqual(report["coverage"]["reviewable_turns"], 1)
        self.assertEqual(report["data_quality"]["invalid_rows_or_files"], 6)
        self.assertEqual(report["input_errors"][0]["line"], 5)

    def test_missing_boundaries_and_legacy_are_visible(self):
        events = self.turn(turn_id="start-outside")
        events[0]["ts"] = (NOW - timedelta(days=31)).isoformat()
        events.extend(self.turn(turn_id="no-end")[:-1])
        events.extend(self.turn(turn_id="legacy", schema_version=1))
        self.write(events)
        report = self.analyze()
        candidates = {c["turn_id"]: c for c in report["review_candidates"]}
        self.assertIn("missing_turn_start", candidates["start-outside"]["review_reasons"])
        self.assertEqual(candidates["no-end"]["work_verification"], "no_end")
        self.assertEqual(candidates["legacy"]["work_verification"], "legacy")

    def test_interleaved_turns_and_actors_do_not_exchange_results(self):
        events = [
            self.event("agent_started", turn_id="one"),
            self.event("skill_activated", turn_id="one", skill="guide"),
            self.event("agent_started", turn_id="two"),
            self.event("skill_activated", turn_id="two", skill="check"),
            self.event("agent_end", turn_id="one"),
            self.event("verification_finished", turn_id="one", verification="test", status="failed"),
            self.event("verification_finished", turn_id="two", verification="test", status="unknown"),
            self.event("agent_end", turn_id="two"),
            *self.turn(turn_id="one", agent_id="worker"),
        ]
        turns = build_turns(events)
        self.assertEqual(len(turns), 3)
        self.assertEqual([turn_outcome(t) for t in turns], ["検証失敗", "未検証", "検証済み"])
        stats = aggregate(turns)
        self.assertEqual((stats["guide"].uses, stats["guide"].failed, stats["guide"].verified), (2, 1, 1))
        self.assertEqual((stats["check"].unverified, stats["check"].failed), (1, 0))

    def test_pi_without_turn_ids_uses_observed_starts(self):
        self.write([*self.turn(agent="pi", turn_id=None),
                    *self.turn(agent="pi", turn_id=None, status="failed")])
        report = self.analyze()
        self.assertEqual(report["coverage"]["reviewable_turns"], 2)
        self.assertEqual(report["data_quality"]["activations_without_turn_id"], 2)
        self.assertEqual({c["turn_id"] for c in report["review_candidates"]}, {"1", "2"})
        self.assertTrue(all(c["turn_id_inferred"] for c in report["review_candidates"]))

    def test_cli_limit_review_template_and_symlink(self):
        events = [*self.turn(turn_id="one"), *self.turn(turn_id="two")]
        for index, event in enumerate(events):
            event["ts"] = (datetime.now(timezone.utc) - timedelta(minutes=1) + timedelta(seconds=index)).isoformat()
        self.write(events)
        link = self.root / "agent-observability-analyze-usage"
        link.symlink_to(SCRIPT.resolve())

        def run(*args):
            return subprocess.run([sys.executable, str(link), "--root", str(self.root), *args],
                                  text=True, capture_output=True)

        result = run("--limit", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["candidates_truncated"])
        self.assertEqual(len(report["review_candidates"]), 1)
        self.assertEqual(report['work_summary']['turns_with_skills'], 2)
        self.assertEqual(report["cohorts"][0]["turns"], 2)
        candidate_id = report["review_candidates"][0]["id"]
        result = run("--review-template", candidate_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["observation"]["id"], candidate_id)
        self.assertEqual(run("--days", "0").returncode, 2)
        self.assertEqual(run("--review-template", "missing").returncode, 2)

    def test_cli_prepares_all_groups_before_limit_and_leaves_case_answers_unfilled(self):
        events = [*self.turn(turn_id='success'), *self.turn(turn_id='failure', status='failed')]
        for index, event in enumerate(events):
            event['ts'] = (datetime.now(timezone.utc) - timedelta(minutes=1) + timedelta(seconds=index)).isoformat()
            if event['event'] == 'skill_activated':
                event['skill'] = 'ponytail'
            event['prompt'] = 'PRIVATE_PROMPT'
        self.write(events)
        cases = self.root / 'cases'
        cases.mkdir()
        (cases / 'example.json').write_text(json.dumps({
            'id': 'example', 'skill': 'ponytail', 'scenario': 'typical', 'evaluation': {'status': 'ready'}}))
        command = [sys.executable, str(SCRIPT), '--root', str(self.root), '--cases', str(cases), '--limit', '1']
        run = subprocess.run([*command, '--prepare-cases'], capture_output=True, text=True, check=True)
        result = json.loads(run.stdout)
        snapshot = json.loads((self.root / 'eval-candidates.json').read_text())
        self.assertEqual(result['case_preparation']['state'], 'updated')
        self.assertEqual(result['evaluation_candidate_count'], 2)
        self.assertEqual(len(result['evaluation_candidates']), 1)
        self.assertEqual(len(snapshot['evaluation_candidates']), 2)
        group = result['evaluation_candidates'][0]
        self.assertEqual(group['related_cases'][0]['id'], 'example')
        run = subprocess.run([*command, '--case-proposal', group['id']], capture_output=True, text=True, check=True)
        proposal = json.loads(run.stdout)
        self.assertEqual(proposal['status'], 'needs_context_review')
        self.assertTrue(all(value is None for value in proposal['observations'][0]['design'].values()))
        self.assertEqual(proposal['observations'][0]['observation']['id'], group['examples'][0])
        self.assertTrue(proposal['observations'][0]['observation']['evidence'])
        self.assertNotIn('PRIVATE_PROMPT', json.dumps(snapshot) + run.stdout)
        review = proposal['observations'][0]
        evidence = review['observation']['evidence']
        review.update(reviewer={'kind': 'ai', 'name': 'sample'},
                      conversation_evidence=[{**evidence[0], 'role': 'request'}, {**evidence[-1], 'role': 'result'}],
                      result={'outcome': 'recovered', 'summary': 'Repaired and checked.'},
                      design={'action': 'no_case', 'reason': 'Already covered by the regression.',
                              'next_action': 'Keep the current check.'})
        review['assessment'].update(context='real_work', reason='Inspected source and final result.')
        review_path = self.root / 'review.json'
        review_path.write_text(json.dumps(review))
        subprocess.run([*command, '--save-review', str(review_path)], capture_output=True, text=True, check=True)
        refresh = subprocess.run([*command, '--prepare-cases'], capture_output=True, text=True, check=True)
        refreshed = json.loads(refresh.stdout)
        self.assertEqual(refreshed['case_review_summary'], {'reviewed': 1, 'pending': 1})
        self.assertEqual(refreshed['evaluation_candidates'][0]['reviewed_work_count'], 1)
        opened = subprocess.run([*command, '--case-proposal', group['id']], capture_output=True, text=True, check=True)
        reopened = json.loads(opened.stdout)
        self.assertEqual(reopened['status'], 'reviewed')
        self.assertEqual(reopened['reviewed_work'][0]['result']['outcome'], 'recovered')
        self.assertEqual(reopened['observations'][0]['design']['action'], 'no_case')
        self.assertEqual(reopened['observations'][0]['observation']['work_verification'], 'reported_failed')
        (cases / 'broken.json').write_text('{}')
        run = subprocess.run(command, capture_output=True, text=True, check=True)
        broken = json.loads(run.stdout)
        self.assertTrue(broken['case_catalog_errors'])
        self.assertIsNone(broken['evaluation_candidates'][0]['missing_scenarios'])


if __name__ == "__main__":
    unittest.main()
