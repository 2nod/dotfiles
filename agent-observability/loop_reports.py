"""Local evidence review and deterministic round summaries; never invokes a model."""
import html
import json
from pathlib import Path

from eval_contracts import reviewed_result
from comparison_checks import comparison_pairs, efficiency_quality_ready, efficiency_passes


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
    pairs = comparison_pairs(rows)
    baseline, target = ('treatment', 'candidate') if plan.get('candidate') else ('control', 'treatment')
    efficiency_ready = (state['state'] in ('needs-decision', 'decided')
                        and len(rows) == expected
                        and efficiency_quality_ready(pairs, baseline, target))
    threshold_met = (efficiency_passes(plan.get('efficiency'), pairs)
                     if efficiency_ready and plan.get('candidate') and plan.get('efficiency') else None)
    decision = None
    decision_error = None
    if (directory / 'decision.json').exists():
        try:
            decision = json.loads((directory / 'decision.json').read_text())
            if not isinstance(decision, dict):
                raise ValueError('decision must be an object')
        except (ValueError, OSError) as exc:
            decision, decision_error = None, str(exc)
    context = {key: plan.get(key) for key in ('skill', 'purpose', 'scope', 'model', 'reviewer', 'mode', 'runs', 'invocation', 'diagnosis', 'candidate', 'efficiency')}
    context['conditions'] = [dict(zip(('model', 'agent', 'agent_version', 'runtime_image', 'invocation'), values))
                             for values in sorted({tuple(str(row.get(key) or 'unknown') for key in ('model', 'agent', 'agent_version', 'runtime_image', 'invocation')) for row in rows})]
    context['cases'] = [{key: entry.get(key) for key in ('path', 'contract_version', 'alignment', 'holdout')} for entry in plan['cases']]
    context['reviewers'] = sorted({row['reviewer'] for row in rows if row.get('reviewer')})
    decision_valid = state['state'] == 'decided' and decision is not None and decision_error is None
    data = {'efficiency_comparison_ready': efficiency_ready, 'state': state, 'expected_results': expected, 'observed_results': len(rows),
            'summary': summary, 'review_queue': queue, 'results': rows,
            'context': context, 'comparison': {'baseline': baseline, 'target': target, 'threshold_met': threshold_met},
            'decision': decision, 'decision_valid': decision_valid, 'decision_error': decision_error}
    # Kept outside artifact directories, so reporting never invalidates a review hash.
    (directory / 'report.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    (directory / 'report.md').write_text(markdown_report(data))
    e = html.escape
    parts = [f'<h1>{e(plan["skill"])} comparison</h1>',
             f'<p>State: {e(state["state"])}. Results: {len(rows)} / {expected}. Next: {e(state["next_action"])}.</p>',
             '<p>Unreviewed results are pending. Time includes runner and verifier overhead. Tokens are not currency. No automatic adoption.</p>',
             '<p>効率比較：' + ('品質ゲート通過。事前に定めた削減幅と比較してください。' if efficiency_ready else '保留。未採点・不合格・条件不一致がある間、時間やトークンだけで採用しません。') + '</p>',
             '<p><a href="report.md">判断用Markdown</a> / <a href="report.json">Full data and review queue</a></p>',
             '<h2>条件と判断</h2><pre>' + e(json.dumps({'context': context, 'decision': decision, 'decision_valid': decision_valid, 'errors': state.get('errors', []), 'decision_error': decision_error, 'comparison': data['comparison']}, ensure_ascii=False, indent=2)) + '</pre>',
             '<h2>同じ入力の比較</h2>' + paired_html(pairs, variants),
             '<table><tr><th>Case / run / variant</th><th>Result</th><th>Evidence</th></tr>']
    for row in rows:
        label = 'pass' if row.get('success') is True else 'fail' if row.get('success') is False else 'pending review'
        artifact = Path(row['artifacts'])
        links = ' / '.join(f'<a href="{e(path.resolve().as_uri())}">{e(name)}</a>'
                           for name, path in [('trace', artifact / 'trace.jsonl'),
                                              ('artifacts', artifact / 'index.html'),
                                              ('review', artifact / 'review.json')]
                           if path.is_file())
        behavior = '<pre>' + e(json.dumps(row.get('behavior_checks'), ensure_ascii=False, indent=2)) + '</pre>' if row.get('behavior_checks') is not None else ''
        scores = '<ul>' + ''.join('<li>' + e(k) + ': ' + ('合格' if v['pass'] else '不合格') + ' — ' + e(v['evidence']) + '</li>' for k, v in row.get('quality_scores', {}).items()) + '</ul>'
        parts.append(f'<tr><td>{e(str(row["case"]))} / {row["run"]} / {e(row["variant"])}</td><td>{label}{scores}{behavior}</td><td>{links}</td></tr>')
    parts.append('</table>')
    (directory / 'report.html').write_text('<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Skill comparison</title><style>body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:1rem}table{width:100%;table-layout:fixed;border-collapse:collapse}td,th{border:1px solid #aaa;padding:.6rem;overflow-wrap:anywhere}</style><body>' + ''.join(parts) + '</body></html>')
    return {'report': str(directory / 'report.html'), 'expected': expected,
            'observed': len(rows), 'ungraded': len(queue), 'state': state['state'],
            'markdown': str(directory / 'report.md')}


def evidence_links(row):
    root = Path(row['artifacts'])
    candidates = [('input', root / 'input.json'), ('before', root / 'before'),
                  ('after', root / 'after'), ('trace', root / 'trace.jsonl'),
                  ('review', root / 'review.json')]
    return [(label, path.resolve().as_uri()) for label, path in candidates if path.exists()]


def paired_html(pairs, variants):
    e = html.escape
    cells = ['<table><tr><th>Case / run</th>' + ''.join('<th>' + e(v) + '</th>' for v in variants) + '</tr>']
    for pair in pairs:
        first = next(iter(pair.values()))
        cells.append('<tr><td>' + e(str(first.get('case'))) + ' / ' + e(str(first.get('run'))) + '</td>')
        for variant in variants:
            row = pair.get(variant)
            links = ' / '.join('<a href="' + e(url, quote=True) + '">' + e(label) + '</a>' for label, url in evidence_links(row)) if row else 'missing'
            cells.append('<td>' + links + '</td>')
        cells.append('</tr>')
    return ''.join(cells) + '</table>'


def markdown_report(data):
    """A derived decision summary; never a second, hand-maintained score ledger."""
    def cell(value):
        if value is None:
            return '未記録'
        text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
        return html.escape(text).replace('|', '&#124;').replace('\n', '<br>').replace('`', '&#96;')
    context, state = data['context'], data['state']
    decision = data.get('decision') or {}
    lines = ['# スキル比較の判断記録', '',
             '保存済みのplan、結果、採点、decisionから生成。直接編集せず正本を更新して再生成する。', '',
             '## 問いと条件', '',
             '| 項目 | 記録 |', '|---|---|']
    for key in ('skill', 'purpose', 'scope', 'model', 'mode', 'runs', 'invocation', 'diagnosis', 'candidate', 'reviewers'):
        lines.append('| ' + key + ' | ' + cell(context.get(key)) + ' |')
    lines += ['', '| モデル | Agent | Version | Runtime image | 呼び出し方法 |', '|---|---|---|---|---|']
    for condition in context['conditions']:
        lines.append('| ' + ' | '.join(cell(condition.get(key)) for key in ('model', 'agent', 'agent_version', 'runtime_image', 'invocation')) + ' |')
    lines += ['', '## 判断と不足する証拠', '',
              '- 状態: ' + cell(state.get('state')),
              '- 記録した判断: ' + cell(decision.get('action')),
              '- decision検査: ' + ('通過' if data['decision_valid'] else '未確定'),
              '- 次の作業: ' + cell(state.get('next_action'))]
    for key in ('reason', 'evidence', 'reviewer', 'limitations', 'next_check', 'human_review'):
        lines.append('- ' + key + ': ' + cell(decision.get(key)))
    for error in [*state.get('errors', []), *([data['decision_error']] if data.get('decision_error') else [])]:
        lines.append('- 未解決: ' + cell(error))
    lines += ['', '## 同じ入力の比較', '', '| Case / run | 条件 | 結果 | 根拠 | Skillの版 / 依存の版 | 成果物の版 |', '|---|---|---|---|---|---|']
    for row in sorted(data['results'], key=lambda r: (str(r.get('case')), r.get('run', 0), str(r.get('variant')))):
        links = ' / '.join('[' + label + '](' + url + ')' for label, url in evidence_links(row))
        outcome = '合格' if row.get('success') is True else '不合格' if row.get('success') is False else '未採点'
        lines.append('| ' + cell(row.get('case')) + ' / ' + cell(row.get('run')) + ' | ' + cell(row.get('variant')) + ' | ' + outcome + ' | ' + links + ' | ' + cell(row.get('skill_version')) + ' / ' + cell(row.get('dependency_versions')) + ' | ' + cell(row.get('artifact_version')) + ' |')
        if row.get('behavior_checks') is not None:
            lines.append('| | 行動検証 | ' + ('合格' if row['behavior_checks']['passed'] else '不合格') + ' | ' + cell(row['behavior_checks']) + ' | | |')
        for key, score in row.get('quality_scores', {}).items():
            lines.append('| | ' + cell(key) + ' | ' + ('合格' if score['pass'] else '不合格') + ' | ' + cell(score['evidence']) + ' | | |')
    lines += ['', '## 効率と適用範囲', '',
              '- 比較対象: ' + cell(data['comparison']['baseline']) + ' → ' + cell(data['comparison']['target']),
              '- 比較対象の品質: ' + ('合格' if data['efficiency_comparison_ready'] else '保留'),
              '- 事前の効率条件: ' + cell(context.get('efficiency')),
              '- 効率条件の達成: ' + cell(data['comparison']['threshold_met']),
              '', '| 条件 | 結果数 | 合格 | 不合格 | 未採点 | トークン合計 / 計測数 | 秒合計 / 計測数 |', '|---|---:|---:|---:|---:|---:|---:|']
    for item in data['summary']:
        values = [cell(item[key]) for key in ('variant', 'observed', 'passed', 'failed', 'ungraded')]
        values += [cell(item[key]['sum']) + ' / ' + cell(item[key]['observed']) for key in ('total_tokens', 'duration_seconds')]
        lines.append('| ' + ' | '.join(values) + ' |')
    lines += ['', '| ケース | 条件hash | 目的との対応 | Holdout |', '|---|---|---|---|']
    for case in context['cases']:
        lines.append('| ' + ' | '.join(cell(case.get(key)) for key in ('path', 'contract_version', 'alignment', 'holdout')) + ' |')
    lines += ['',
              '効率条件の達成だけで採用しない。未採点、条件変更、欠落、人手レビューの不足はdecisionの検査で扱う。',
              'トークンは請求額ではない。計測したモデルと実行条件の範囲に限る。', '',
              '[計画](plan.json) / [全結果](report.json)' + (' / [判断の正本](decision.json)' if data.get('decision') is not None else ''), '']
    return '\n'.join(lines)
