"""Retain contextual results and case designs without changing observed outcomes."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from eval_contracts import contract_version
from usage_cases import save_private_json


def has_text(value):
    return isinstance(value, str) and bool(value.strip())


def observation_version(work):
    fields = ('id', 'agent', 'started_at', 'ended_at', 'skills', 'observed_models', 'work_verification')
    value = {key: work.get(key) for key in fields}
    # Replicated homes can add locations for the same content without changing the work.
    value['evidence'] = sorted({r['sha256'] for r in work.get('evidence', [])})
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def check_evidence(refs):
    by_path = {}
    for ref in refs:
        if (not isinstance(ref, dict) or not isinstance(ref.get('path'), str)
                or type(ref.get('line')) is not int or ref['line'] < 1
                or not re.fullmatch('[a-f0-9]{64}', str(ref.get('sha256', '')))):
            raise ValueError('evidence requires path, positive line and sha256')
        if not Path(ref['path']).is_absolute():
            raise ValueError('evidence path must be absolute')
        previous = by_path.setdefault(ref['path'], {}).setdefault(ref['line'], ref['sha256'])
        if previous != ref['sha256']:
            raise ValueError('conflicting evidence references')
    for path, wanted in by_path.items():
        with Path(path).open() as stream:
            for number, line in enumerate(stream, 1):
                if number in wanted:
                    if hashlib.sha256(line.rstrip('\r\n').encode()).hexdigest() != wanted.pop(number):
                        raise ValueError('context evidence changed')
                if not wanted:
                    break
        if wanted:
            raise ValueError('context evidence missing')


def validate_review(review, work):
    if review['observation']['id'] != work['id']:
        raise ValueError('review belongs to another work item')
    if review.get('observation_version') != observation_version(work):
        raise ValueError('observation changed; review current evidence')
    if not work.get('ended_at'):
        raise ValueError('work has no end record')
    reviewer = review['reviewer']
    if reviewer.get('kind') not in ('ai', 'human') or not has_text(reviewer.get('name')):
        raise ValueError('identify the reviewer')
    assessment = review['assessment']
    if assessment.get('context') not in ('real_work', 'evaluation_setup', 'test', 'unknown') or not has_text(assessment.get('reason')):
        raise ValueError('record context and reasoning')
    refs = review['conversation_evidence']
    if not isinstance(refs, list) or any(not isinstance(r, dict) for r in refs) or not {'request', 'result'} <= {r.get('role') for r in refs}:
        raise ValueError('request and result evidence are required')
    check_evidence(refs)
    result, design = review['result'], review['design']
    if result.get('outcome') not in ('completed', 'recovered', 'blocked', 'excluded', 'insufficient_evidence') or not has_text(result.get('summary')):
        raise ValueError('record the contextual result')
    if design.get('action') not in ('reuse_case', 'add_case', 'no_case', 'needs_evidence') or not all(has_text(design.get(k)) for k in ('reason', 'next_action')):
        raise ValueError('record the design decision and next action')
    if design['action'] in ('reuse_case', 'add_case'):
        if not all(has_text(design.get(k)) for k in ('problem', 'expected_behavior')):
            raise ValueError('case design requires problem and expected behavior')
        link = design['case']
        path = Path(link['path'])
        if not path.is_absolute():
            raise ValueError('case path must be absolute')
        case = json.loads(path.read_text())
        if (case.get('evaluation', {}).get('status') != 'ready' or not case.get('rubric')
                or not case.get('verifiers') or case.get('skill') not in {s['name'] for s in work['skills']}):
            raise ValueError('link a ready case for an observed skill')
        if link.get('contract_version') != contract_version(case, path):
            raise ValueError('case design changed; check the linked case again')
        if not has_text(link.get('verification_evidence')):
            raise ValueError('record verifier evidence and its limits')


def save_review(root, review, observations):
    identifier = review['observation']['id']
    work = next((w for w in observations if w['id'] == identifier), None)
    if work is None or not re.fullmatch('[a-f0-9]{20}', identifier):
        raise ValueError('work not found in the selected window')
    validate_review(review, work)
    record = {**review, 'observation': {k: v for k, v in work.items() if k != 'case_review'},
              'reviewed_at': datetime.now(timezone.utc).isoformat()}
    return save_private_json(root / 'case-reviews' / (identifier + '.json'), record)


def attach_reviews(root, observations):
    counts = Counter()
    for work in observations:
        path = root / 'case-reviews' / (work['id'] + '.json')
        if not path.exists():
            counts['pending'] += 1
            continue
        try:
            review = json.loads(path.read_text())
            validate_review(review, work)
            work['case_review'] = {'state': 'reviewed', 'path': str(path),
                                   'reviewer': review['reviewer'], 'reviewed_at': review['reviewed_at'],
                                   'result': review['result'], 'design': review['design']}
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            work['case_review'] = {'state': 'needs_review', 'path': str(path), 'reason': str(error)}
        counts[work['case_review']['state']] += 1
    return dict(counts)
