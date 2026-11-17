import pathlib
import re
import sys

text = (pathlib.Path(sys.argv[1]) / 'guide.md').read_text()
assert text.startswith('# 集計レポートを出力する\n')
assert '```' not in text and '<!--' not in text
lines = [re.sub(r'^(?:\d+\. |[-*] )', '', line.strip()) for line in text.splitlines() if line.strip() and not line.startswith('#')]
prerequisite = '出力前に対象期間と列の指定を確認する。'
execute = '出力処理を実行する。'
result = '出力先のファイル名を確認する。'
assert sorted(lines) == sorted([prerequisite, execute, result]), 'Keep exactly the original three sentences.'
assert lines.index(prerequisite) < lines.index(execute) < lines.index(result), 'Prerequisite must precede execution and its result check.'
print('Prerequisite, execution, and result check are ordered correctly; all original sentences retained.')
