"""Read-only reconciliation of source bundles, discovered bundles and decisions."""
import json
from pathlib import Path
from urllib.parse import unquote, urlparse
from eval_contracts import tree_version


def deployment_state(source, location):
    if not source.is_file():
        return '管理元に存在しません（履歴のみ）'
    if not location:
        return '探索対象の配置先に見つかりません'
    parsed = urlparse(location[0])
    if parsed.scheme != 'file':
        return '配置先の版を確認できません'
    deployed = Path(unquote(parsed.path))
    try:
        if tree_version(source.parent) == tree_version(deployed.parent) and deployed.is_file():
            return '探索した配置先と管理元の版が一致'
    except (OSError, ValueError):
        return '配置先を読み取れません'
    return '探索した配置先と管理元の版が不一致'


def collect_rounds(root, status):
    records = []
    for directory in sorted((root / 'eval-loops').glob('*')):
        if not directory.is_dir():
            continue
        plan, decision = {}, {}
        for name, destination in [('plan.json', plan), ('decision.json', decision)]:
            try:
                value = json.loads((directory / name).read_text())
                if isinstance(value, dict):
                    destination.update(value)
            except (OSError, ValueError):
                pass
        try:
            state = status(directory)
        except Exception as error:
            state = {'state': 'invalid', 'errors': [str(error)]}
        records.append({'directory': directory, 'skill': plan.get('skill'),
                        'state': state, 'decision': decision, 'plan': plan})
    return records


def decision_state(records):
    """Do not guess recency from filenames or silently prefer conflicting records."""
    valid = [r for r in records if r['state'].get('state') == 'decided' and r['decision']]
    if not valid:
        return '判断材料不足', []
    actions = {r['decision'].get('action') for r in valid}
    if len(actions) != 1:
        return '有効な判断が競合・要確認', valid
    action = next(iter(actions))
    labels = {'keep': '継続判断あり（記録の適用範囲内）', 'disable': '無効化判断あり（配置は別途確認）',
              'adopt': '修正版の採用判断あり（配置は別途確認）', 'revise': '改善継続', 'hold': '判断保留'}
    return labels.get(action, '判断材料不足'), valid
