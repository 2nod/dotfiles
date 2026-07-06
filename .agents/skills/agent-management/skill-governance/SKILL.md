---
name: skill-governance
description: shared agent skill 全体の方針、責務分離、installed skill の provenance、SOURCE.md の役割、wrapper skill と agent-specific instruction の使い分けを判断するときに使う。skill 管理ルールの置き場所に迷ったとき、または skill-maintenance の責務を広げすぎないよう整理するときに使う。
metadata:
  tags: [skills, governance, agents]
---

# Skill Governance

shared skill 全体の方針を整理する。
作業手順ではなく、配置と責務の境界を扱う。

## ディレクトリの責務

- `.agents/skills/`: この repo で自作する skill を置く。
- `.agents/installed-skills/`: third-party 由来の skill を upstream 追跡可能な形で置く。
- agent-specific instruction: agent の実行時ルールを置く。

`.agents/README.md` は、この領域の役割と参照先を示す入口に限定する。
個別 skill の一覧、詳細な authoring rule、install 手順、runtime rule は README に置かない。

## 自作 skill

自作 skill は `.agents/skills/<category>/<skill-name>` に置く。
`SKILL.md` は入口に絞り、詳細な checklist、判断材料、長い手順は `references/` に分ける。
成果物の雛形は `templates/` に置く。

日本語で `SKILL.md`、`references/`、`templates/` を書くときは、`writing/japanese-tech-writing` も併用する。

## Installed skill

installed skill は upstream の内容を追跡しやすい形で保存する。
third-party 由来の `SKILL.md`、`templates/`, `scripts/`, `assets/` は原則として upstream の内容をそのまま置く。
ローカル都合で本文を分割、要約、再構成しない。

upstream の挙動をローカル向けに変えたい場合は、installed skill を編集しない。
現行の deploy と trigger check は、同じ公開 path を持つ自作 skill と installed skill を許可しない。
そのため guardrail を追加したい場合は、まず agent-specific instruction に置くか、別名の自作 wrapper skill を作る。

同じ公開 path で installed skill を shadow する設計は、bundle、trigger check、agent ごとの skill discovery の優先順位を実装してから許可する。
それまでは、同じ `<category>/<skill-name>` を `.agents/skills` と `.agents/installed-skills` の両方に置かない。

## SOURCE.md

`SOURCE.md` は provenance 専用にする。
書いてよい内容は、repository、source path、pinned commit、raw URL、install command など、取得元を追跡するための情報に限る。

`SOURCE.md` に次の内容を書かない。

- ローカルの安全補足
- 定期実行時の制約
- agent ごとの runtime rule
- wrapper としての振る舞い

一般的な点検観点は scout/checklist skill に置く。
ローカル挙動の変更は自作 wrapper skill に置く。
agent 全体の実行時ルールは agent-specific instruction に置く。
