# スキル評価の途中経過（2026-09-12）

追加評価はユーザーの指示により停止しました。これは評価途中のチェックポイントです。
全スキルの採用判断を完了したという記録ではありません。

## 実施範囲と結果

対象は共有リポジトリの37スキル（自作20、外部導入17）。削除済みのスキルは対象外です。
モデルは `openai-codex/gpt-5.6-sol`、Pi 0.84.4、隔離Dockerを使用しました。
過去のAstraの結果とは集計を分けています。
ユーザープロンプトと合成fixtureを共通にし、スキル資料の同梱の有無を比較しています。

| 記録 | 件数 | 解釈 |
|---|---:|---|
| 実行済み出力 | 744 | スクリーニング72、本比較648、test-design-review比較24 |
| 入力照合済み | 744 | 実際に渡した入力を照合。試験自体の妥当性は別途確認 |
| 親AIによる暫定採点済み出力 | 546 | 条件を知った非盲検の採点。独立採点ではない |
| 機械検査の失敗 | 11 | 契約の曖昧さ5、成果物の配置と検査の不一致6。スキルの失敗数とは扱わない |
| 新規ケース | 82 | オフライン検査・dry-run済み。修正ケースの実評価は未実施 |
| 独立採点・補足比較の追加実行 | 0 | 提案した追加172呼び出し（比較60、採点最大112）は実施しない |

本比較は原則として典型・境界・非適用の3ケース、それぞれ3反復、あり／なしの2条件です。
少数の合成ケースであり、実サービスの互換性や自律的なスキル選択精度は検証していません。
観測トークンは10,217,233。これは請求額ではなく、品質判断前に費用だけで採否を決めません。

## スキル別の到達点

「暫定採点済み」は合格・採用を意味しません。すべて利用判断の確定前です。

### 親AIによる暫定採点済み（25）

`skill-governance`, `skill-scout`, `docker-worktree-cleanup`, `git-workflow`, `git-worktree-cleanup`, `local-docker-troubleshooting`, `daily-task-triage`, `task-lifecycle`, `notion-workspace-context`, `notion-workspace-maintenance`, `pr-diff-findings`, `pr-review-fix-workflow`, `codebase-design`, `diagnosing-bugs`, `domain-modeling`, `grill-with-docs`, `grilling`, `tdd`, `ponytail`, `ponytail-audit`, `ponytail-review`, `ponytail-debt`, `ponytail-gain`, `ponytail-help`, `japanese-tech-writing`

### 試験条件を補った再比較が未実施（6）

`skill-maintenance`, `async-workflow-operations`, `meeting-agenda`, `test-design-review`, `cognitive-rhythm-writing`, `explain`

### 人手レビューが未実施（6）

`build-experiment-report-site`, `build-implementation-report-site`, `pr-description-writing`, `technical-flow-diagrams`, `html`, `show-me`

人手レビュー用に60組の比較素材を保存済みです。主な比較対象は典型・境界の36組で、残り24組は補助資料です。
52 HTMLの参照先と重複IDは静的確認しましたが、描画・操作・読みやすさの評価はしていません。

## 試験の問題と修正

10ケースを `legacy` にし、理由と `replacement_case` を記載しました。
元の出力と判定履歴は保持し、曖昧な契約による失敗を品質の悪さとして集計しません。

- async-workflow-operations: 指示にない途中成果物の削除を検査が要求していたため、保持を明示。
- skill-maintenance: 配布先ルートからの相対配置を明示。
- test-design-review: helperのメタデータ契約が曖昧だったため、契約を明示。
- meeting-agenda / explain: プロンプトとfixtureの時間・題材の矛盾を解消。
- cognitive-rhythm-writing: 必須の日本語文章スキルを依存資料として追加。修正版は資料一式の効果を測り、このスキル単体の限界効果とは扱わない。

修正版は機械検査の失敗／最小期待出力での成功とdry-runまで確認済みです。
機械検査はファイル保持・状態遷移・出力の存在などを確認するもので、意味の正しさやデザイン品質の代わりにはなりません。

## 再開する場合に残っていること

現時点では実行予定はありません。再開には別途指示が必要です。

- 上記6スキルについて、修正した入力で比較する。
- 発見した問題、誤指摘、見逃し、不要な変更、必要な追加提案を分けて独立確認する。今回の暫定採点は、この5軸を一律に完了したものではない。
- 人手レビュー対象について、両条件の成果物を並べて評価する。
- 品質を確認した後にトークン・時間と合わせて、外部導入スキルは利用可否、自作スキルは利用可否と改善方針を決める。

評価対象はリポジトリの版です。配布済みの版には資料の差分があり、今回の結果を全ランタイムの現行版の保証には使えません。再配布は行っていません。

## 記録の場所

再利用する合成ケース・fixture・verifierは `.agents/evals/` に置きます。
生の入力、出力、トレース、採点、37スキルの判断カード、比較素材はローカルの `all-skill-validation-20260912` 記録に保存し、PRには含めません。
この文書は固定時点の集計であり、稼働中の状態表示や最終的な採用台帳ではありません。
