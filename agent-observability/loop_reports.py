"""Local evidence review and deterministic round summaries; never invokes a model."""
import html
import json
from pathlib import Path

from eval_contracts import reviewed_result


def round_results(directory, plan):
    rows = []
    for entry in plan['cases']:
        case = json.loads(Path(entry['path']).read_text())
        path = directory / (case['id'] + '.jsonl')
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def select_result(directory, plan, case, run, variant):
    matches = [r for r in round_results(directory, plan)
               if (r.get('case'), r.get('run'), r.get('variant')) == (case, run, variant)]
    if len(matches) != 1:
        raise ValueError('Expected exactly one saved result for case/run/variant')
    return matches[0]


def review_template(row):
    return {'artifact_version': row['artifact_version'], 'reviewer': '',
            'criteria': [{'id': c['id'], 'pass': None, 'evidence': '',
                          'criterion': c.get('criterion', '')} for c in row['rubric']]}


def save_review(row, source):
    """Validate scores and fingerprint with the same gate as decisions, then persist."""
    if row.get('failure_kind') != 'passed':
        raise ValueError('Execution failed; review cannot override execution failure')
    target = Path(row['artifacts']) / 'review.json'
    if target.exists():
        existing = json.loads(target.read_text())
        if existing != review_template(row):
            raise ValueError('Review already exists; inspect it before explicitly editing it')
    review = json.loads(source.read_text())
    # reviewed_result verifies both the complete bundle digest and every rubric item.
    result = reviewed_result(row, review)
    if type(result.get('success')) is not bool:
        raise ValueError('Review incomplete, rubric mismatch, or artifact fingerprint changed')
    target.write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n')
    return result


def report(directory, plan, state):
    rows = [reviewed_result(row) for row in round_results(directory, plan)]
    variants = ('control', 'treatment', 'candidate') if plan.get('candidate') else ('control', 'treatment')
    expected = len(plan['cases']) * plan['runs'] * len(variants)
    summary = []
    queue = []
    for row in rows:
        if row.get('success') is None:
            queue.append({k: row.get(k) for k in ('case', 'run', 'variant', 'artifacts')})
    for variant in variants:
        group = [row for row in rows if row['variant'] == variant]
        item = {'variant': variant, 'observed': len(group),
                'passed': sum(r.get('success') is True for r in group),
                'failed': sum(r.get('success') is False for r in group),
                'ungraded': sum(r.get('success') is None for r in group)}
        for key in ('total_tokens', 'duration_seconds'):
            values = [r[key] for r in group if isinstance(r.get(key), (int, float))]
            item[key] = {'observed': len(values), 'sum': sum(values) if values else None,
                         'min': min(values) if values else None, 'max': max(values) if values else None}
        summary.append(item)
    efficiency_ready = state['state'] in ('needs-decision', 'decided') and len(rows) == expected and all(r.get('success') is True for r in rows)
    data = {'efficiency_comparison_ready': efficiency_ready, 'state': state, 'expected_results': expected, 'observed_results': len(rows),
            'summary': summary, 'review_queue': queue, 'results': rows}
    # Kept outside artifact directories, so reporting never invalidates a review hash.
    (directory / 'report.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    e = html.escape
    parts = [f'<h1>{e(plan["skill"])} comparison</h1>',
             f'<p>State: {e(state["state"])}. Results: {len(rows)} / {expected}. Next: {e(state["next_action"])}.</p>',
             '<p>Unreviewed results are pending. Time includes runner and verifier overhead. Tokens are not currency. No automatic adoption.</p>',
             '<p>効率比較：' + ('品質ゲート通過。事前に定めた削減幅と比較してください。' if efficiency_ready else '保留。未採点・不合格・条件不一致がある間、時間やトークンだけで採用しません。') + '</p>',
             '<p><a href="report.json">Full data and review queue</a></p>',
             '<table><tr><th>Case / run / variant</th><th>Result</th><th>Evidence</th></tr>']
    for row in rows:
        label = 'pass' if row.get('success') is True else 'fail' if row.get('success') is False else 'pending review'
        artifact = Path(row['artifacts'])
        links = ' / '.join(f'<a href="{e(path.resolve().as_uri())}">{e(name)}</a>'
                           for name, path in [('trace', artifact / 'trace.jsonl'),
                                              ('artifacts', artifact / 'index.html'),
                                              ('review', artifact / 'review.json')]
                           if path.is_file())
        scores = '<ul>' + ''.join('<li>' + e(k) + ': ' + ('合格' if v['pass'] else '不合格') + ' — ' + e(v['evidence']) + '</li>' for k, v in row.get('quality_scores', {}).items()) + '</ul>'
        parts.append(f'<tr><td>{e(str(row["case"]))} / {row["run"]} / {e(row["variant"])}</td><td>{label}{scores}</td><td>{links}</td></tr>')
    parts.append('</table>')
    (directory / 'report.html').write_text('<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Skill comparison</title><style>body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:1rem}table{width:100%;table-layout:fixed;border-collapse:collapse}td,th{border:1px solid #aaa;padding:.6rem;overflow-wrap:anywhere}</style><body>' + ''.join(parts) + '</body></html>')
    return {'report': str(directory / 'report.html'), 'expected': expected,
            'observed': len(rows), 'ungraded': len(queue), 'state': state['state']}
