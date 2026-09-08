---
name: build-experiment-report-site
description: ユーザーが比較実験のHTMLレポートまたはSiteを明示的に依頼したときに使う。仮説、固定条件、ケース別結果、計測時間、再現手順をまとめる。実験の実行、パラメータ探索、結果の質問だけでは使わない。
metadata:
  tags: [experiment-report, benchmark, reproducibility, site, visualization]
  related_skills:
    - writing/html
    - software-development/build-implementation-report-site
    - software-development/technical-flow-diagrams
---

# 実験レポートSite作成

`writing/html` をHTML作成の共通基盤として使い、第三者が実験結果を画像、可視化、指標から理解し、根拠を追跡して同じ条件で再実行できるSiteを作る。
本文より先に、実験条件と機械可読な結果を確定する。

## 作成要否

ユーザーがHTMLレポートまたはSiteを明示的に依頼したときだけ使う。実験・比較・結果報告の依頼だけではHTMLを作らず、チャットで結果と限界を伝え、必要な実測ログを保存する。

## Skillの階層

- `writing/html` は、静的HTML、共通デザインシステム、目次、図、コード、数式、印刷を扱う表示基盤である。
- このskillは、実験契約、機械可読な結果、比較方法、指標、再現手順を扱う。
- 内容の順序、データの正本、保存と公開の判断はこのskillを優先し、HTMLの部品と表現は `writing/html` に従う。
- HTMLを作る前に `writing/html/design-system/component-samples.html` を確認し、同梱の `document.css` と必要なアセットを使う。ページ固有のCSSは可視化の配置調整に限る。

## 実装レポートとの境界

- 実験レポートは、条件、比較対象、指標の変化を扱う。
- 実装レポートは、コードの責務と処理フローの変化を扱う。
- 両方が必要なら、比較の詳細は実験レポート、結論と参照先は実装レポートに置く。

## 作業手順

1. [references/experiment-contract.md](references/experiment-contract.md) を使い、問い、仮説、判定基準、比較対象、条件、変数、指標を定義する。
2. 比較対象に不変のIDを付け、該当するsource revisionまたはartifact digest、設定、環境、外部サービスの版を記録する。「旧版」「現在」「main」だけで識別しない。
3. 入力、fixture、評価器、実行環境などの固定条件を変えた場合は、新しい実行IDで記録する。
4. ケース別結果をJSONやCSVへ保存し、集計、表、グラフ、画像キャプションを同じresultから生成する。HTMLへ数値や可視化データを手入力しない。
5. 時間と回数に計測範囲、単位、分母、集計方法を付ける。計算、外部I/O、wall-clock、初回、追加処理を混ぜない。
6. [templates/report-outline.md](templates/report-outline.md) で実験契約、結果、ケース比較、解釈、制約、再現手順を組み立て、`writing/html` でHTMLへ実装する。
7. 全ケースを機械可読なresultへ保持し、Siteから検索、フィルター、詳細表示などで到達可能にする。本文では分布、最悪、悪化、代表ケースを優先し、小規模な実験、明示要求、画像品質が主題の場合は全ケースの入力、基準、候補を並置する。画像または適切な可視化と指標を対応付け、結果の差が読み取れる形で示す。
8. 分布、最悪値、未解決、悪化を確認し、[references/failure-patterns.md](references/failure-patterns.md) と [references/review-checklist.md](references/review-checklist.md) で公開前に監査する。

## 成果物の扱い

生データ、ログ、画像、Siteを相互に追跡できるIDで結ぶ。
一時的な結果を製品仕様として扱わず、恒久docsには確定した知見と再現条件を分けて残す。
commit、push、Site公開は対象リポジトリの手順に従い、ユーザーの明示許可を得てから行う。
