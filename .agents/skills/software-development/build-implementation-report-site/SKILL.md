---
name: build-implementation-report-site
description: PRや大きな実装差分について、実コード、処理フロー、変更前後、実測結果、レビュー観点をHTMLまたはSiteへまとめるときに使う。ユーザーが「実装レポートをsiteにして」「レビュー用の説明サイトを作って」「コード差分と検証結果を図解して」と依頼した場合に発火する。
metadata:
  tags: [implementation-report, site, pull-request, review, visualization]
  related_skills:
    - software-development/git-workflow
    - software-development/pr-review-fix-workflow
---

# 実装レポートSite作成

実装を知らないレビュワーが、変更理由から証拠まで一方向に読めるSiteを作る。
見栄えより先に、コードと計測結果から説明の根拠を固定する。

## 作業手順

1. baseと変更後のSHA、差分、設計、実装、テスト、計測成果物を確認する。
2. レポートで保証する内容と保証しない内容を分ける。推定、実測、設定値、上限、通常の目安を混同しない。
3. `templates/report-outline.md` を使い、全体像、処理フロー、実装対応、検証、レビュー観点の順に情報を配置する。
4. 実行順に沿って、分岐、ループ、早期終了、計画と適用を図示する。
5. 変更前後は標語だけで済ませず、変わった責務または関数を示す。全ファイルは列挙しない。
6. 計測は分母と計数範囲を併記する。初回処理と追加処理、ケース合計とケースあたり、通常値と安全上限を分ける。
7. Siteをビルドし、表示テスト、lint、デスクトップとモバイルの実表示を確認する。

## 表現の基準

- マクロからミクロへ進む。結論、全体フロー、分岐詳細、実コード、証拠の順を崩さない。
- 実行コストが違う処理を視覚的に分ける。
- 実行目的と実行条件を分ける。「確認する」だけでなく、何を満たしたときに実行するかを書く。
- 内部語は見出しにせず、文脈なしで通じる日本語を定義する。
- 図中の番号は、実装上の識別子または本文で参照する順序に限る。説明の都合だけで架空のphase番号を付けない。
- 色は意味の区別にだけ使い、矢印、余白、見出し階層で流れを示す。

## 成果物の扱い

レポートSiteのソースと検証画像は、製品リポジトリの恒久docsへ無条件に入れない。
製品仕様として長期保守する内容だけをdocsに残し、一時成果物は`tmp`、公開用Siteは専用ソースリポジトリへ分ける。
commit、push、Site公開は対象リポジトリの手順に従い、ユーザーの明示許可を得てから行う。

## 参照

- 構成を作るときは [templates/report-outline.md](templates/report-outline.md) を使う。
- 初稿前に [references/failure-patterns.md](references/failure-patterns.md) を読む。
- 公開前の監査では [references/review-checklist.md](references/review-checklist.md) を読む。
