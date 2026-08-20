# Agent skill observability

pi と Codex の skill 利用イベントを、prompt や推論本文を保存せずローカルへ記録する。

## 保存先

- `~/.local/share/agent-observability/events/YYYY-MM-DD.jsonl`: 追記専用の正本
- `~/.local/share/agent-observability/live/*.json`: SwiftBar 用の現在状態

保存するのはschema version、agent、model、session ID、project名、skill名とハッシュ、tool種別、検証結果、時刻だけ。
Codex の prompt、tool input、tool response、assistant message は保存しない。

## Reporter

- pi: `pi/extensions/skill-observability.ts` がNodeで直接保存する
- Codex: `codex/skill-observability.py` が同一Pythonプロセス内でrecorderを呼ぶ
- 共通schema: `schema/event.schema.json`

Codex App hook は重複実行を避けるため `hooks.json` に集約し、Herdr hook と共存する。

## 表示

`swiftbar/plugins/agent-skills.10s.py` が30分以内に更新されたlive stateを表示する。
`Open report` は直近30日のJSONLを集計し、日常監視用の`report.html`を開く。caseと比較評価は同時生成される`evals.html`へ分離し、両ページのナビゲーションから移動できる。
レポートとSwiftBarのskill名は実際に読むローカル`SKILL.md`へリンクする。共有skillは`shared · authored/installed`、Codex同梱skillは`codex-system · bundled`と表示する。installed skillのupstream情報は`SOURCE.md`で管理する。
検証率は、schema v2でskillを使った終了済みturnのうち、記録された検証カテゴリ（test・build・diagnostics）の最終結果がすべて成功した割合です。diagnosticsはerror・blocking・timeout・未確認を失敗とし、warningだけなら成功として件数を記録します。検証イベントがないturnは未検証、旧schemaのturnは集計対象外です。skillなしとの因果比較ではありません。

## 比較評価

`agent-observability-eval`はfixtureを一時directoryへ複製し、skillなし／ありを交互に実行する。
agent出力やprompt本文は保存せず、verifier結果、変更file数、変更行数、所要時間だけを`eval-results/*.jsonl`へ記録する。
実行するとmodel利用が発生するため、まずdry-runでplanを確認する。

共有 skill を使った実作業で、既存 case にない客観的な差を再現できる場合は、Pi/Codex の global rule により eval case を継続追加する。追加対象は匿名化した合成 fixture と決定的 verifier に限り、実案件の code や prompt は保存しない。比較評価 run からの再帰追加と、有料評価の自動実行もしない。

```sh
agent-observability-eval .agents/evals/ponytail-cache.json --runs 3 --dry-run
agent-observability-eval .agents/evals/ponytail-cache.json --runs 3 --model <provider/model>
agent-observability-eval .agents/evals/tdd-inventory.json --runs 1 --dry-run
agent-observability-eval .agents/evals/diagnosis-parser.json --runs 1 --dry-run
```

case の整理は削除ではなく、まず分類する。

```sh
agent-observability-audit-evals --cases .agents/evals
```

- `keep`: 3回以上の同一実験条件の control/treatment で、成功率または成功runの変更量に改善あり
- `review`: 実測不足、または treatment が control より悪い
- `retire`: 3回以上の実測で改善がなく、整理候補

`retire` でも自動削除はしない。修正・移行・削除はレビュー後に行う。

## 検証

```sh
python3 agent-observability/test_observability.py
nix run .#build -- work
```
