"""Prepare review leads from observed work, never infer a case oracle or skill effect."""
from collections import Counter
from datetime import datetime
import hashlib
from itertools import zip_longest
import json
import os
from pathlib import Path
import tempfile


SIGNALS = {
    'verification_failed': '検証失敗の記録',
    'verification_unconfirmed': '検証結果が未確認',
    'verification_passed': '検証成功の記録',
    'usage_observed': '通常の利用記録',
}


def load_cases(directory):
    cases, errors = [], []
    if not directory.is_dir():
        return [], [{'file': str(directory), 'reason': 'directory_unavailable'}]
    for path in sorted(directory.glob('*.json')):
        try:
            case = json.loads(path.read_text())
            if not isinstance(case['id'], str) or not isinstance(case['skill'], str):
                raise ValueError('case id and skill must be strings')
            scenario = case.get('scenario')
            if scenario is not None and not isinstance(scenario, str):
                raise ValueError('case scenario must be a string')
            cases.append({'id': case['id'], 'skill': case['skill'], 'path': str(path.resolve()),
                          'scenario': scenario,
                          'design_status': case.get('evaluation', {}).get('status', 'unknown')})
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            errors.append({'file': path.name, 'reason': type(error).__name__})
    return cases, errors


def case_candidates(observations, catalog, cases, selected_skill=None):
    groups = {}
    for work in observations:
        if not work.get('ended_at') or work['work_verification'] == 'legacy':
            continue
        reasons = work['review_reasons']
        signal = ('verification_failed' if 'verification_failed' in reasons else
                  'verification_unconfirmed' if 'verification_result_unconfirmed' in reasons else
                  'verification_passed' if work['work_verification'] == 'reported_passed' else 'usage_observed')
        names = {s['name'] for s in work['skills']} & catalog.keys()
        if selected_skill:
            names &= {selected_skill}
        for name in names:
            groups.setdefault((name, signal), []).append(work)
    buckets = {signal: [] for signal in SIGNALS}
    for (skill, signal), works in sorted(groups.items()):
        works.sort(key=lambda work: (datetime.fromisoformat(work['started_at']), work['id']), reverse=True)
        related = [case for case in cases if case['skill'] == skill]
        designed = {c['scenario'] for c in related if c['design_status'] == 'ready'}
        group = {
            'id': hashlib.sha256(json.dumps([skill, signal]).encode()).hexdigest()[:20],
            'skill': skill, 'signal': signal, 'label': SIGNALS[signal],
            'status': 'needs_context_review', 'case_match': 'unassessed',
            'work_count': len(works), 'latest_at': works[0]['started_at'],
            'examples': [work['id'] for work in works[:3]],
            'agents': dict(Counter(work['agent'] for work in works)),
            'models': sorted({m for work in works for m in work['observed_models']}),
            'co_used_work_count': sum(len(work['skills']) > 1 for work in works),
            'missing_version_work_count': sum('unknown_or_mixed_skill_version' in work['review_reasons'] for work in works),
            'related_cases': related,
            'missing_scenarios': sorted(set(catalog[skill].get('required_scenarios',
                                        ['typical', 'boundary', 'negative'])) - designed),
        }
        buckets[signal].append(group)
    for bucket in buckets.values():
        bucket.sort(key=lambda group: (datetime.fromisoformat(group['latest_at']), group['id']), reverse=True)
    # Include ordinary examples; a persistent historical failure must not fill the entire shortlist.
    return [group for row in zip_longest(*buckets.values()) for group in row if group is not None]


def save_candidates(root, analysis):
    """Refresh derived local metadata atomically; never overwrite authored reviews/cases."""
    payload = {key: analysis[key] for key in
               ('generated_at', 'window_start', 'source', 'selected_skill', 'evaluation_candidates', 'case_catalog_errors')}
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = root / 'eval-candidates.json'
    with tempfile.NamedTemporaryFile(mode='w', dir=root, prefix='.eval-candidates-', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    return path
