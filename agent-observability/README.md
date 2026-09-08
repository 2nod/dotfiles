# Agent skill observability

日常の利用記録と、合成ケースによるskill比較評価を扱う。
改善作業は下記の「改善ループ」から始める。

## 比較評価の実行環境

モデル利用は明示指定した実行に限る。計画・採点・レポート作成はモデルを起動しない。
Piの認証はホストに置き、評価対象のread/write/edit/bashはDockerで実行する。
組み込みツールを無効にし、ホストのbind mountを使わず、合成fixtureと対象skillの同梱資料だけをコピーする。
コンテナはnetworkなし、root filesystem読み取り専用、非root、capabilityなし。
出力、メモリ、PID、時間に上限を設け、verifierは成果物をコピーした別コンテナで実行する。

事前にローカルDocker、Pi、コードで固定したNodeイメージを用意し、隔離テストを通す。
イメージの自動pullはしない。
現在の固定イメージは `node@sha256:0d9e9a8dcd5a83ea737ed92227a6591a31ad70c8bb722b0c51aff7ae23a88b6a`。
新しい環境では、このdigestを明示して事前に `docker pull` する。
別イメージへの更新は隔離テストを通し、新しい評価条件として計画を作る。

```sh
SKILL_EVAL_OFFLINE_DOCKER=1 PYTHONPYCACHEPREFIX=/tmp/skill-eval-pycache \
  python3 -m unittest discover -s agent-observability -p 'test_*.py' -v
```

Dockerを指定しない通常のテストは隔離テストをskipする。
テストはモデルを呼ばない。実Piの読み込み確認も認証・推論promptなしで終了する。
依頼された実評価だけ `SKILL_EVAL_ISOLATED_RUN=1` を付ける。
この環境変数は運用の明示指定であり、隔離を提供するのはコンテナ実装である。

skillの同梱ディレクトリ以外の参照資料は自動コピーしない。
readはUTF-8テキスト、editは一意な完全一致を扱う。
画像、外部サービス、複数ターンが目的に不可欠なケースは、この環境での合成入力だけで検証完了にしない。
旧ホスト実行とコンテナ実行の結果は混ぜない。

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
verifier結果と実行条件を`eval-results/*.jsonl`へ、合成fixtureの成果物とtraceを`eval-artifacts/`へ保存する。
実行するとmodel利用が発生するため、まずdry-runでplanを確認する。

共有 skill を使った実作業で、既存 case にない客観的な差を再現できる場合は、Pi/Codex の global rule により eval case を継続追加する。追加対象は匿名化した合成 fixture と決定的 verifier に限り、実案件の code や prompt は保存しない。比較評価 run からの再帰追加と、有料評価の自動実行もしない。

```sh
agent-observability-eval .agents/evals/ponytail-cache.json --runs 3 --dry-run
SKILL_EVAL_ISOLATED_RUN=1 agent-observability-eval .agents/evals/ponytail-cache.json --allow-legacy --runs 3 --model <provider/model>
agent-observability-eval .agents/evals/tdd-inventory.json --runs 1 --dry-run
agent-observability-eval .agents/evals/diagnosis-parser.json --runs 1 --dry-run
```

case の整理は削除ではなく、まず分類する。

```sh
agent-observability-audit-evals --cases .agents/evals
```

現在の目的別判定と移行方針は後述する。旧ケースのkeep/review/retireによる整理基準は廃止した。

## 検証

```sh
python3 agent-observability/test_observability.py
nix run .#build -- work
```

## 目的別評価への移行（schema 2）

共有40 skillの目的と評価する証拠は `.agents/eval-catalog.json` に置く。
旧28ケースは `evaluation.status=legacy` とし、各定義に目的とのずれを記録した。
過去の記録を削除せず、skill採否の根拠から除外する。
上記の旧 `keep/review/retire` と「変更行数が減れば改善」の基準は廃止した。

新しいケースは `evaluation.status=ready`、`scenario`、目的別 `rubric` を持つ。
全共有skillに目的別ケースを用意し、正常系で実際の成果物を作るケースと負例を追加する。
TDD、原因調査、最小実装は実コードを検証する。外部サービス依存のskillは捕捉済み合成入力に限定し、実操作や対話継続の効果を測ったとは扱わない。
境界例と不足する負例、実測は未評価として台帳に残す。
すべてのskillを採点済みと見なさない。

### 実行と採点

```sh
agent-observability-eval .agents/evals/purpose-tdd-red-green.json --runs 3 --dry-run
SKILL_EVAL_ISOLATED_RUN=1 agent-observability-eval .agents/evals/purpose-tdd-red-green.json --runs 3 --model <provider/model>
# 修正版のdirectoryには参照ファイルも含める
SKILL_EVAL_ISOLATED_RUN=1 agent-observability-eval .agents/evals/purpose-tdd-red-green.json --runs 3 --model <provider/model> --candidate /path/to/candidate/SKILL.md
agent-observability-audit-evals --skills
agent-observability-audit-evals --changes
agent-observability-report
```

実行はモデル利用を伴う。モデル指定を必須とし、dry-runでは呼び出さない。
旧ケースは明示的な `--allow-legacy` に限り探索実行できるが採否には使わない。
各run内でcontrol/treatment/candidateを順序交代して実行する。
`--no-context-files`、`--no-extensions`などで通常の追加指示の流入を抑え、対象skill本文だけを明示注入する。
これは単体の効果評価であり、発火精度、他skillとの相互作用、Codexでの効果を測らない。
ツール実行は上記のコンテナに隔離する。合成fixture専用に使う。

`eval-artifacts/<experiment>/<run>-<variant>/`へ次を保存する。

- before/afterの成果物、changes.diff
- trace.jsonl（ツール実行順を含むPi JSON出力）、stderr.txt、case.json
- index.html（生成HTMLもエスケープした文字列として表示）
- review.json（目的別採点票）

日常の利用イベントはこれまで通りpromptや出力を保存しない。
評価runに限って、匿名化した合成入力とその生成物を保存する。
実案件や秘密情報をfixtureへ入れない。
verifierの実行前に成果物を保存し、verifier自身の変更をagentの成果として数えない。
出力を変更しない正しい作業も許容する。

機械verifierの成功は結果ゲートであり、目的の達成を意味しない。
review.jsonのreviewerを記入し、各criterionのpassをtrue/falseにして、traceの行や成果物の箇所をevidenceに記入する。
可能ならvariantを伏せて独立に採点する。現在の画面はblind採点を強制しない。
未記入、証拠なし、成果物改変、ハッシュ不一致は採点待ちとする。
失敗した実行を人手採点で成功に上書きしない。

結果にはモデル、Pi版、skill directory、fixture、case、verifier、runnerのfingerprintを残す。
元のskillにない別skillへの依存は自動注入しない。必要な場合は別の統合評価として設計する。
古い条件、重複run、欠けたペア、環境エラーを成功率へ混ぜない。
3ペアは初期の信号を見る下限であり、統計的な効果の確定ではない。
無効化を自動決定しない。判断は各roundのdecision.jsonに根拠とともに記録する。

`--changes`は前回の台帳、条件、評価状態との差を返し、`skill-monitor.json`を更新する。
初回は基準登録。変化がなければchangesは空。
定期監視はこのコマンドとレポート生成までとし、有料比較やskillの自動変更は行わない。

## 改善ループ

方法の正本は [目的別評価の方針](../.agents/skills/agent-management/skill-governance/references/purpose-evaluation.md)。
効果を見てskillを改良する作業では、単独のevalコマンドではなく次の入口を使う。
低レベルの `evaluate-skill.py` は既存実験と探索用途のため残すが、直接実行しただけでは改善ループの完了にならない。

```sh
python3 agent-observability/skill-loop.py init ~/.local/share/agent-observability/eval-loops/test-design-001 --skill test-design-review
# 生成された plan.json を記入する
python3 agent-observability/skill-loop.py check ~/.local/share/agent-observability/eval-loops/test-design-001
# ユーザーが依頼した有料評価の範囲内で実行する
SKILL_EVAL_ISOLATED_RUN=1 python3 agent-observability/skill-loop.py run ~/.local/share/agent-observability/eval-loops/test-design-001
# 各artifactのreview.jsonを証拠付きで採点する
python3 agent-observability/skill-loop.py check ~/.local/share/agent-observability/eval-loops/test-design-001 --stage review
# decision.json を記入する
python3 agent-observability/skill-loop.py check ~/.local/share/agent-observability/eval-loops/test-design-001 --stage decision
```

`init` はモデルを呼ばず、既存readyケースと現在の評価条件を記録する。
`scope` に実環境、複数ターン、発火などの測れない範囲も書く。
`reviewer` は採点者とAI/人、blind/non-blindの区別。
各caseの `alignment` は目的との対応、`verifier_evidence` は未修正fixtureの失敗、最小修正と別の正解の成功を確認したログを記録する。
変更不要の負例では、正しい出力と誤った指摘をどう区別するかを示す。
これらの文章の意味は人またはAIによるレビューが必要であり、非空チェックは意味の正しさを保証しない。

初期値は `mode: screen`、`runs: 1`。
必要呼び出し数はケース数 × runs × 2（修正版ありは3）で、`max_calls` 以下にする。
上限はこの計画だけに適用し、金額や他の計画の呼び出し数は制御しない。
開始時に `started.json` を排他的に作成するため、同じ保存先の二重実行は拒否する。
中断時も予約を残し、自動再開しない。stderrと部分結果を確認して、新しい計画に残りの作業と既消費分を記録する。
保存した計画と内容が異なる場合、reviewチェックは失敗する。

修正時は別の計画を作り、`candidate` を `{"path":"/absolute/candidate/SKILL.md","version":"sha256:..."}` にする。
versionは `eval_contracts.tree_version(candidate_directory)` で取得する。
`diagnosis` の `cause`、`evidence`、`change` と、`script_review` の `decision`（extract/defer）、`reason`、`input_output`、`failure`、`idempotence`、`verification` を記入する。
候補の採用には `mode: validate`、通常/境界/負例、各3回以上、少なくとも1件の `holdout: true` を必要とする。
採用条件は品質改善、または後述の事前指定した効率改善。どちらも全候補結果の品質合格が必要。

`decision.json` の必須項目は `action`（keep/revise/disable/hold/adopt）、`reason`、`evidence`、`reviewer`、`limitations`、`next_check`。
disableには `alternative`、`exceptions`、`rollback` も必要。
checkは0が条件充足、1が不足で、JSONに理由を返す。
採否を台帳に書くこと、配置を変更すること、モデルを呼ぶ権限を付与することは行わない。
実行前のcheckはplan段階、結果採点後はreview段階、採否記録後はdecision段階を使う。
途中の保留理由はdecision.jsonに残してよいが、未採点などがある間はdecisionチェックも失敗し、改善ループの完了と扱わない。


### 状態を確認して次のラウンドへ進む

`python3 agent-observability/skill-loop.py status <round>` は証拠から現在地と次の作業をJSONで返す。
`needs-plan` は計画修正、`ready` は実行可能、`execution-incomplete` はログ確認（自動再試行不可）、`needs-review` は成果物とtraceの採点、`needs-decision` は採否記録、`decided` は次ラウンドまたは終了を表す。
statusは読取り専用で、モデルを起動しない。実行途中と異常終了はどちらもexecution-incompleteと表示し、プロセス稼働を推測しない。

前ラウンドがreviewとdecisionを通過したら、次を実行する。

```sh
python3 agent-observability/skill-loop.py next <previous-round> --to <new-round> --candidate <candidate/SKILL.md>
```

候補なしの利用比較は `--candidate` を省略する。
installed skillにはローカル候補を付けない。
既存ディレクトリへは上書きしない。
次の計画はparentの判断と既使用fixtureの内容hashを引き継ぐが、実行結果と採点は引き継がない。
目的との対応、scope、原因、script化判断を記入してcheckを通すまで実行できない。
前ラウンドと祖先で使ったfixtureをholdoutにするとplanチェックで拒否する。
内容を変えた類似fixtureの独立性までは機械判定できないため、採点者が確認する。

運用はstatusで次の作業を確認し、run、成果物とtraceの採点、decision記録、check、nextの順に進める。
効率改善も下記の検証と明示的な判断が必要であり、自動採用しない。
定期実行やモデル起動、台帳反映、runtimeへの配置変更はこの状態表示から自動実行されない。

### 採点と比較レポート

```sh
python3 agent-observability/skill-loop.py report <round>
python3 agent-observability/skill-loop.py review-template <round> --case <case-id> --run 1 --variant treatment > /tmp/skill-review.json
# 成果物とtraceを読み、reviewer・各pass・evidenceを記入する
python3 agent-observability/skill-loop.py review <round> --case <case-id> --run 1 --variant treatment --review-file /tmp/skill-review.json
python3 agent-observability/skill-loop.py check <round> --stage review
python3 agent-observability/skill-loop.py report <round>
```

reportはround内のreport.htmlとreport.jsonを更新する。
JSONには条件別の品質合否、使用量・時間の合計と範囲、未採点一覧、全結果を保存する。
成果物は変えないため、レポート更新で採点hashは変わらない。
HTMLのstateとcheckのエラーを先に確認する。未採点や欠落を成功として扱わない。
reviewはrunnerが作る空の採点票を完成させる。既存の記入済み採点は上書きしない。
訂正する場合は既存のreview.jsonを読み、理由をevidenceへ記録して明示編集し、checkとreportを再実行する。
機械ゲートは証拠の意味を採点しない。AIによる採点でも実ファイルを読んで根拠を残す。

### 効率改善を採用判断に使う

screenで品質が同点でも、効率改善の候補として次の独立ケースを用意できる。
候補を見ていないケースを含むvalidateで各3回以上実行する。
開始前のplan.jsonに次を記入する。結果を見て閾値を下げる場合は別の計画が必要。

```json
"efficiency": {
  "metric": "total_tokens",
  "minimum_reduction": 0.2,
  "quality_evidence": "新規テストが必要な例、既存契約の保持、独立holdoutをrubricが検出する根拠",
  "rationale": "運用上20%削減を採用に値する最低幅とする理由"
}
```

metricはtotal_tokensまたはduration_seconds。minimum_reductionは0より大きく1未満の削減率。
全比較ペアで現行と候補が品質合格し、すべてのペアで指定幅以上の削減を達成した場合にadoptが可能になる。
平均だけの改善、欠損計測、品質不合格、screenだけの結果では採用できない。
時間にはrunnerとverifierの処理が含まれ、tokenは請求額ではない。
小規模な反復は将来の全用途の品質同等性を保証しない。limitationsとnext_checkに適用範囲と再確認条件を残す。
共有台帳は目的と評価設計を管理し、ローカルの実測パスや採否をコミットしない。
