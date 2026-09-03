---
name: build-experiment-report-site
description: 実装案、設定値、モデルなどの比較実験を、仮説、固定条件、ケース別結果、計測時間、再現手順が追えるHTMLまたはSiteへまとめるときに使う。「実験レポート」「比較結果のSite」「パラメータ探索」「全ケース比較」で発火する。コード差分と最終設計の説明が主目的なら build-implementation-report-site を使う。
metadata:
  tags: [experiment-report, benchmark, reproducibility, site, visualization]
  related_skills:
    - software-development/build-implementation-report-site
    - software-development/technical-flow-diagrams
---

# 実験レポートSite作成

第三者が根拠を追跡し、同じ条件で再実行できるSiteを作る。
本文より先に、実験条件と機械可読な結果を確定する。

## 実装レポートとの境界

- 実験レポートは、条件、比較対象、指標の変化を扱う。
- 実装レポートは、コードの責務と処理フローの変化を扱う。
- 両方が必要なら、比較の詳細は実験レポート、結論と参照先は実装レポートに置く。

## 作業手順

1. [references/experiment-contract.md](references/experiment-contract.md) を使い、問い、仮説、判定基準、比較対象、条件、変数、指標を定義する。
2. 比較対象に不変のIDを付け、commit SHA、設定、環境、外部サービスの版を記録する。「旧版」「現在」「main」だけで識別しない。
3. fixture、フォント、rendererなどの固定条件を変えた場合は、新しい実行IDで記録する。
4. ケース別結果をJSONやCSVへ保存し、集計、表、画像説明をそこから生成する。HTMLへ数値を手入力しない。
5. 時間と回数に計測範囲、単位、分母、集計方法を付ける。計算、外部I/O、wall-clock、初回、追加処理を混ぜない。
6. [templates/report-outline.md](templates/report-outline.md) を使い、実験契約、結果、ケース比較、解釈、制約、再現手順の順に構成する。
7. 全ケースの入力、基準、候補を同じ条件で並べ、終了段階、変更量、品質、回数、時間を示す。
8. 分布、最悪値、未解決、悪化を確認し、[references/failure-patterns.md](references/failure-patterns.md) と [references/review-checklist.md](references/review-checklist.md) で公開前に監査する。

## 成果物の扱い

生データ、ログ、画像、Siteを相互に追跡できるIDで結ぶ。
一時的な結果を製品仕様として扱わず、恒久docsには確定した知見と再現条件を分けて残す。
commit、push、Site公開は対象リポジトリの手順に従い、ユーザーの明示許可を得てから行う。
