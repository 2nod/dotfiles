---
name: skill-scout
description: shared skillの棚卸し、定期的な見直し、実作業や外部動向に基づく改善候補の調査を依頼されたときに使う。
metadata:
  tags: [skills, audit, agents, maintenance]
  related_skills:
    - agent-management/skill-maintenance
---

# Skill Scout

依頼範囲のskillを調べ、根拠のある改善候補を優先順に示す。
対象と利用するモデル、runtimeを確認し、未指定の全環境へ調査を広げない。

## 調べる範囲

対象の名前とdescription、関連する作業履歴から始める。
問題に関係する本文と参照資料を読む。
全体の棚卸しを依頼された場合はinventoryを列挙し、詳細を読む候補を絞る。
外部調査は依頼された話題と関連する公式資料を優先し、出典とローカルへの適用理由を添える。

指示の整理には [スキルと指示の見直し](../skill-governance/references/skill-review.md)、具体的な点検には [audit-checklist.md](references/audit-checklist.md) の該当箇所を使う。
保存済み評価の採否を扱うときだけ、目的別評価と該当roundの証拠を確認する。

## 結果と次の作業

調査だけの依頼は、対象箇所、理由、最小の対処、確認方法をチャットで返す。
詳細な棚卸しには [skill-scout-report.md](templates/skill-scout-report.md) の必要な項目を使い、空欄や関係のない節を残さない。
日本語の文書を作成、推敲する場合はjapanese-tech-writingを使う。

修正も依頼されている場合は、skill-maintenanceで編集と検証まで進める。
既に許可された編集を一律に「要承認」として止めない。
installed skillにはupstream更新、別名wrapper、出典補完を提案し、本文を直接編集しない。
有料評価と配布はその操作への依頼がある範囲で行う。
定期監視は、新しい問題、判断に必要な変化、完了や失敗があるときだけ通知する。
