---
name: skill-maintenance
description: ユーザーが「skill化して」「skillに追加して」「この手順をskillにして」「global/private skillとして残して」と依頼したときに使う。dotfiles の .agents 配下で、作成した skill と install した skill を整理し、Codex / Cursor Agent / Claude Code から読めるようにする。
---

# Skill Maintenance

dotfiles repo の shared agent skills を作成・更新・install するときに使う。パスは repo root からの相対パスで扱う。

## 基本方針

1. 自作 skill は `.agents/skills/<category>/<skill-name>` に置く。
2. installed skill は `.agents/installed-skills/<category>/<skill-name>` に置く。
3. 公開 path は `<category>/<skill-name>` の 2 segment にする。
4. 自作 skill の `SKILL.md` は最小限に保ち、詳細・例・フォーマットは `references/` に分ける。
5. installed skill は upstream の `SKILL.md` を原則そのまま置き、分割・要約・編集しない。
6. installed skill には参照元を `SOURCE.md` に残す。
7. 新規 file / directory は Nix flake から見えるように `git add` する。commit はユーザーの明示許可までしない。

## 参照

- 自作 skill の `description` や本文を書く・直すときは、先に `writing/japanese-tech-writing` も読む。
- 新規 skill の要件と文字量目安は [references/skill-requirements.md](references/skill-requirements.md) を読む。
- install / symlink / 検証手順が必要なときは [references/dotfiles-workflow.md](references/dotfiles-workflow.md) を読む。
