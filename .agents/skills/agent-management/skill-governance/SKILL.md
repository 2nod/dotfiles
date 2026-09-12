---
name: skill-governance
description: shared skillの責務、配置、provenance、wrapperとruntime指示の境界、見直しと採否の方針を判断するときに使う。
metadata:
  tags: [skills, governance, agents]
---

# Skill Governance

shared skillの配置と責務、見直しの方針を決める。
棚卸しはskill-scout、依頼された作成や修正はskill-maintenanceで進める。

## 配置と出典

- 自作skillは `.agents/skills/<category>/<skill-name>`、upstream由来は `.agents/installed-skills/<category>/<skill-name>` に置く。
- installed skillの本文と同梱資料はupstreamの内容を保持する。ローカル向けの挙動はagent固有の指示か別名wrapperへ置く。
- 同じ公開pathでのshadowingは、bundle、trigger check、discoveryの優先順位を実装するまで使わない。
- `SOURCE.md` はrepository、source path、pinned commit、raw URLなどのprovenance専用とし、運用指示を混ぜない。
- `.agents/README.md` は領域の入口に留める。skillの一覧はfrontmatter、実行時のルールは各agentの指示を正本とする。

## 必要な方針を読む

- 指示の重複、過剰な手順、発火条件、モデル更新に伴う見直しには [スキルと指示の見直し](references/skill-review.md) を使う。
- 比較結果から継続、改善、採用、無効化を判断するときは [目的別評価の方針](references/purpose-evaluation.md) を使う。

変更理由と検証した範囲を残す。
文書を短くしたことや静的検査の成功だけで、skillの効果を実証したとは扱わない。
