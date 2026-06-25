---
name: skill-maintenance
description: ユーザーが「skill化して」「skillに追加して」「この手順をskillにして」「global/private skillとして残して」と依頼したときに使う。dotfiles の .agents 配下で、作成した skill と install した skill を整理し、Codex / Cursor Agent / Claude Code から読めるようにする。
---

# Skill Maintenance

dotfiles repo の shared agent skills を作成・更新・install するときに使う。パスは dotfiles repo root からの相対パスで扱う。

## 配置ルール

- 自作 skill は `.agents/skills/<category>/<skill-name>` に置く。
- install した third-party skill は `.agents/installed-skills/<category>/<skill-name>` に置く。
- agent への公開 path は `<category>/<skill-name>` にする。`installed-skills` は公開 path に出さない。
- `<category>/<skill-name>` は 2 segment にする。例: `software-development/pr-review-fix-workflow`, `planning/grill-me`。
- 同じ公開 path を `.agents/skills` と `.agents/installed-skills` の両方で使わない。

## 自作 Skill を追加する

1. 目的と trigger 文を確認し、短い hyphen-case の `skill-name` と用途 category を決める。
2. `.agents/skills/<category>/<skill-name>/SKILL.md` を作る。
3. `SKILL.md` は `name` と `description` の frontmatter を必ず持つ。
4. 本文はその skill を実行するために必要な最小限の手順に絞る。
5. `.agents/README.md` の Available Skills に、必要なら 1 行追加する。
6. `claude/CLAUDE.md` は `.agents/README.md` を source of truth として参照する。原則として skill ごとの一覧は `claude/CLAUDE.md` に増やさない。
7. 即時利用したい場合は Codex / Cursor / Claude Code の skills directory に symlink を張る。
8. Nix flake から見えるように、新規 file / directory は `git add` する。commit はユーザーの明示許可があるまでしない。

## Installed Skill を追加する

third-party skill を入れる場合は wrapper を使う。

```sh
.agents/bin/install-skill \
  --target <category>/<skill-name> \
  --repo <owner>/<repo> \
  --path <path/to/skill>
```

`--url` 形式も使える。

```sh
.agents/bin/install-skill \
  --target <category>/<skill-name> \
  --url https://github.com/<owner>/<repo>/tree/<ref>/<path/to/skill>
```

wrapper は `.agents/installed-skills/<category>/<skill-name>` に install し、Codex / Cursor / Claude Code へ即時 symlink を張る。

## 検証

- `find -L ~/.codex/skills ~/.cursor/skills ~/.claude/skills -maxdepth 4 -name SKILL.md -print` で公開 path を確認する。
- 対象 skill の `SKILL.md` を symlink 経由で読めることを確認する。
- Home Manager helper の評価は dotfiles repo root で次を実行する。

```sh
export dotfilesDir="$(git rev-parse --show-toplevel)"
nix eval --no-write-lock-file --impure --raw --expr \
  'let pkgs = import <nixpkgs> {}; lib = pkgs.lib; dotfilesDir = builtins.getEnv "dotfilesDir"; agentSkills = import ./nix/modules/home/programs/agent-skills.nix { inherit lib dotfilesDir; }; in agentSkills.linkCommands "/tmp/agent-skills-target"'
```

## 注意

- `claude/settings.json` など、今回の skill 追加と無関係な dirty file は触らない。
- repository instruction が commit / push 前の確認を求める場合、必ずユーザーに確認する。
- すでに起動している agent は skill 一覧を起動時に読んでいることがある。反映されない場合は agent の再起動を案内する。
