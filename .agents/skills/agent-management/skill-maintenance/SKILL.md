---
name: skill-maintenance
description: ユーザーが「skill化して」「skillに追加して」「この手順をskillにして」「global/private skillとして残して」と依頼したときに使う。dotfiles の .agents 配下で、作成した skill、install した skill、installed skill の SOURCE.md provenance（pinned commit / raw URL）を整理し、Codex / Cursor Agent / Claude Code から読めるようにする。
metadata:
  tags: [skills, dotfiles, maintenance, agents]
---

# Skill Maintenance

dotfiles repo の shared agent skills を作成・更新・install するときに使う。パスは repo root からの相対パスで扱う。

## 基本方針

1. 自作 skill は `.agents/skills/<category>/<skill-name>` に置く。
2. installed skill は `.agents/installed-skills/<category>/<skill-name>` に置く。
3. 公開 path は `<category>/<skill-name>` の 2 segment にする。
4. 自作 skill の `SKILL.md` は最小限に保ち、詳細・例・判断材料は `references/` に分ける。
5. 成果物の雛形は `templates/` に分け、`SKILL.md` から使う template 名を明示する。
6. installed skill は upstream の `SKILL.md` と同梱 directory（`templates/`, `scripts/`, `assets/` など）を原則そのまま置き、分割・要約・編集しない。
7. installed skill には参照元を `SOURCE.md` に残す。
8. 新規 file / directory は Nix flake から見えるように `git add` する。commit はユーザーの明示許可までしない。

## 参照

- 新規 skill の要件と文字量目安は [references/skill-requirements.md](references/skill-requirements.md) を読む。
- install / symlink / 検証手順が必要なときは [references/dotfiles-workflow.md](references/dotfiles-workflow.md) を読む。

## 配布の完了条件

配置案を確認するときも、配布元と各agentのskill名の集合と同梱内容が一致することを完了条件に含める。件数やリンクの存在だけでは完了にしない。
配布後は [scripts/check_inventory.py](scripts/check_inventory.py) で欠落、余分なskill、内容差分を検査する。使い方は配布手順の「検証」を参照する。

## 修正時の評価

skillの効果を評価して改善するときは、[改善ループの実行規約](../skill-governance/references/purpose-evaluation.md)を読み、`agent-observability/skill-loop.py` のinit、check、runを使う。
目的とケースの対応を確認してから計画を記入し、各段階のcheckが失敗したら不足を解消する。
修正案には決定論的処理のscript化を検討した記録を付ける。
採否と根拠は各roundのdecision.jsonへ記録し、checkを通す。共有台帳には目的と評価設計を残す。
本文だけの誤字修正など、効果比較が不要な変更へ有料評価を広げない。
