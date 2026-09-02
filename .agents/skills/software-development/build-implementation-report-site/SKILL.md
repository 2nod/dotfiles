---
name: build-implementation-report-site
description: 製品コード、設定、APIやDB契約、運用スクリプトを実装または修正したとき、完了前にレビュー判断用の実装・検証レポートをHTMLで作るために使う。「実装して」「修正して」「回帰テストやローカルE2Eまで」という通常の実装依頼でも必ず使う。「実装レポート」「検証レポート」「コード差分と検証結果を図解して」という依頼でも使う。調査、回答、docsだけの変更、生成物更新だけの作業では使わない。
metadata:
  tags: [implementation-report, site, pull-request, review, visualization]
  related_skills:
    - software-development/build-experiment-report-site
    - software-development/git-workflow
    - software-development/pr-review-fix-workflow
    - software-development/technical-flow-diagrams
---

# 実装・検証レポート作成

実装を知らないレビュワーが、変更領域、コード、検証結果、残る判断を対応づけて読めるHTMLを作る。
レポートは実装タスクの完了条件であり、製品リポジトリとPRには含めない。
比較実験の仮説、条件、ケース別結果、再現手順は `software-development/build-experiment-report-site` に置き、このレポートには結論と参照先を置く。

## 完了条件と保存先

- 実装と必要な検証を終えた後、最終回答の前にレポートを作成または更新する。
- 既定の保存先は `$CODEX_HOME/visualizations/<日付>/<task-id>/<report-name>/index.html` とする。利用できない環境では、製品リポジトリ外の一時ディレクトリを使う。
- レポート、画像、検証用HTMLを製品リポジトリへ置かない。`git add`、commit、push、PR対象にしない。
- 最終回答ではレポートの絶対パスまたはURLを示す。
- 小さな変更は一画面の短縮版でよい。該当しない章を空のまま残さない。

## 作業手順

1. baseと変更後のSHA、trackedとuntrackedの差分、設計、実装、テスト、計測成果物を確認する。
2. 差分を責務ごとの実装領域へ重複なく分類する。各領域に、変更内容、目的、主要コード、差分量と全体比、対応する図を置く。差分比は工数やリスクではないと明記する。
3. レビュー主張を、H（人間判断）、P（根拠が閉じた確認済み）、U（未確認）の三つへ分け、`H1`、`P1`、`U1`のようにIDを付ける。Uには確認を閉じる条件を書く。
4. `templates/report-outline.md` を使う。00を索引兼レビュー結論とし、実装領域、H/P/U、詳細章を対応表で結ぶ。01以降は00の根拠として、目的、フロー、契約、コード責務、検証、外部境界を展開する。
5. 保証する範囲と保証しない範囲を全章で同じ表現にする。推定、実測、設定値、上限を混同しない。
6. 図は実装領域と本文から参照できる位置に置く。必要なら `software-development/technical-flow-diagrams` を使う。
7. HTMLを実ブラウザで開き、リンク、ID重複、横溢れ、デスクトップとモバイルの表示を確認する。

## 品質境界

レポートを作業日誌として追記せず、確定した設計と検証結果から組み直す。
比較実験の詳細は関連skillへ分け、製品仕様として長期保守する内容だけを製品docsへ別途反映する。
公開する場合は専用ソースを使い、commit、push、公開の前にユーザーの明示許可を得る。

## 参照

- 構成を作るときは [templates/report-outline.md](templates/report-outline.md) を使う。
- 初稿前に [references/failure-patterns.md](references/failure-patterns.md) を読む。
- 完了前に [references/review-checklist.md](references/review-checklist.md) で監査する。
