"""Review drafts must preserve other writers, source ownership and pending work."""
import copy
from datetime import timedelta
import hashlib
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest

from test_usage_analysis import usage
from test_usage_collection import NOW, codex, codex_start, codex_end, command, claude, pi
from usage_reviews import attach_reviews, save_review
from usage_store import collect


def native_work(root, runtime='codex'):
    logs = root / 'logs'
    logs.mkdir()
    if runtime == 'codex':
        rows = []
        for turn in ('turn-one', 'turn-two'):
            rows += codex_start(turn=turn) + [
                codex('response_item', {'type': 'message', 'role': 'user', 'content': 'Repair the sample.'}),
                command('read-' + turn, 'cat /skills/guide/SKILL.md', turn=turn),
                codex('response_item', {'type': 'message', 'role': 'assistant', 'content': 'Checked the repair.'}),
                codex_end(turn)]
        # Overlap the turns so timestamp bounds alone cannot reject the other request.
        rows = rows[:6] + rows[7:] + [rows[6]]
        request, result, other_request, other_result = 4, 6, 10, 12
    elif runtime == 'claude-code':
        rows = [claude('user', 'Repair the sample.', 'request'),
                claude('assistant', [{'type': 'tool_use', 'id': 'read', 'name': 'Read',
                                      'input': {'file_path': '/skills/guide/SKILL.md'}}], 'call'),
                claude('user', [{'type': 'tool_result', 'tool_use_id': 'read', 'content': 'Guide',
                                 'is_error': False}], 'output'),
                claude('assistant', 'Checked the repair.', 'progress'),
                claude('assistant', 'Finished.', 'reply', stop_reason='end_turn')]
        request, result, other_request, other_result = 1, 4, None, None
    else:
        rows = [{'type': 'session', 'id': 'pi-session', 'cwd': '/work/sample'},
                pi('user', 'Repair the sample.', 'request'),
                pi('assistant', [{'type': 'toolCall', 'id': 'read', 'name': 'read',
                                  'arguments': {'path': '/skills/guide/SKILL.md'}}], 'call', 'request'),
                pi('toolResult', 'Guide', 'output', 'call', toolCallId='read', isError=False),
                pi('assistant', 'Checked the repair.', 'progress', 'output'),
                pi('assistant', 'Finished.', 'reply', 'progress', stopReason='stop')]
        request, result, other_request, other_result = 2, 5, None, None
    for n, row in enumerate(rows):
        row['timestamp'] = (NOW - timedelta(hours=1) + timedelta(seconds=n)).isoformat()
    path = logs / 'session.jsonl'
    lines = [json.dumps(row) for row in rows]
    path.write_text('\n'.join(lines) + '\n')
    collect(root, {runtime: [str(logs)]})
    observations = usage.analyze(root, now=NOW, catalog={'guide': {}})['review_candidates']
    observed = min(observations, key=lambda work: work['started_at'])

    def refs(request_line, result_line):
        return [{'path': str(path), 'line': n, 'sha256': hashlib.sha256(lines[n - 1].encode()).hexdigest(),
                 'role': role} for role, n in [('request', request_line), ('result', result_line)]]

    review = usage.review_template(observed)
    review.update(reviewer={'kind': 'ai', 'name': 'first'},
                  conversation_evidence=refs(request, result),
                  assessment={'context': 'real_work', 'reason': 'Read the request and result.'},
                  result={'outcome': 'recovered', 'summary': 'Repair checked.'},
                  design={'action': 'no_case', 'reason': 'Covered by an existing regression.',
                          'next_action': 'Keep the regression.'})
    other_refs = refs(other_request, other_result) if other_request else None
    return observed, review, other_refs


def reopen(root, observed):
    current = copy.deepcopy(observed)
    attach_reviews(root, [current])
    return usage.review_template(current)


def competing_save(root, observed, review, barrier, output):
    barrier.wait(timeout=10)
    try:
        save_review(Path(root), review, [observed])
        output.put('saved')
    except ValueError as error:
        output.put(str(error))


class ReviewIntegrityTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_stale_draft_cannot_erase_a_human_correction(self):
        observed, first, _ = native_work(self.root)
        path = save_review(self.root, first, [observed])
        stale = reopen(self.root, observed)
        correction = copy.deepcopy(stale)
        correction['reviewer'] = {'kind': 'human', 'name': 'second'}
        correction['result'] = {'outcome': 'blocked', 'summary': 'Acceptance check remains blocked.'}
        save_review(self.root, correction, [observed])
        preserved = path.read_bytes()
        for old in (first, stale):
            with self.assertRaisesRegex(ValueError, 'review changed'):
                save_review(self.root, old, [observed])
            self.assertEqual(path.read_bytes(), preserved)
        latest = reopen(self.root, observed)
        latest['result']['summary'] = 'Rechecked the outstanding acceptance check.'
        save_review(self.root, latest, [observed])
        self.assertEqual(json.loads(path.read_text())['result']['summary'], latest['result']['summary'])

    def test_two_processes_cannot_both_save_the_same_revision(self):
        observed, review, _ = native_work(self.root)
        ctx = multiprocessing.get_context('spawn')
        barrier, output = ctx.Barrier(2), ctx.Queue()
        processes = [ctx.Process(target=competing_save, args=(str(self.root), observed, review, barrier, output))
                     for _ in range(2)]
        try:
            for process in processes:
                process.start()
            outcomes = [output.get(timeout=20) for _ in processes]
            self.assertEqual(outcomes.count('saved'), 1, outcomes)
            self.assertEqual(sum('review changed' in outcome for outcome in outcomes), 1, outcomes)
        finally:
            for process in processes:
                process.join(timeout=10)
                if process.is_alive():
                    process.terminate()
                    process.join()
            output.close()

    def test_context_from_a_different_file_or_turn_is_rejected(self):
        observed, review, other_refs = native_work(self.root)
        with self.subTest('same file, different turn'):
            wrong = copy.deepcopy(review)
            wrong['conversation_evidence'] = other_refs
            with self.assertRaisesRegex(ValueError, 'outside the observed work'):
                save_review(self.root, wrong, [observed])
        with self.subTest('unrelated file, even with copied identities and hashes'):
            unrelated = self.root / 'unrelated.jsonl'
            unrelated.write_bytes(Path(review['conversation_evidence'][0]['path']).read_bytes())
            wrong = copy.deepcopy(review)
            wrong['conversation_evidence'] = [{**ref, 'path': str(unrelated)} for ref in wrong['conversation_evidence']]
            with self.assertRaisesRegex(ValueError, 'outside the observed work'):
                save_review(self.root, wrong, [observed])
        self.assertFalse((self.root / 'case-reviews' / (observed['id'] + '.json')).exists())

    def test_native_context_lines_remain_valid_for_each_runtime(self):
        for runtime in ('codex', 'claude-code', 'pi'):
            with self.subTest(runtime=runtime), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                observed, review, _ = native_work(root, runtime)
                save_review(root, review, [observed])
                self.assertEqual(attach_reviews(root, [observed]), {'reviewed': 1})

    def test_legacy_review_and_changed_observation_can_be_reopened_and_corrected(self):
        observed, review, _ = native_work(self.root)
        path = save_review(self.root, review, [observed])
        # Old files have no revision field. Their complete contents still identify the version.
        legacy = json.loads(path.read_text())
        legacy.pop('expected_review_version', None)
        path.write_text(json.dumps(legacy))
        observed['work_verification'] = 'reported_failed'
        self.assertEqual(attach_reviews(self.root, [observed]), {'needs_review': 1})
        correction = reopen(self.root, observed)
        self.assertEqual(correction['result'], review['result'])
        self.assertEqual(correction['design'], review['design'])
        self.assertEqual(correction['observation_version'], usage.observation_version(observed))
        save_review(self.root, correction, [observed])
        self.assertEqual(attach_reviews(self.root, [observed]), {'reviewed': 1})


if __name__ == '__main__':
    unittest.main()
