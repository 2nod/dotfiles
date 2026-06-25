# Dotfiles Skill Workflow

dotfiles の shared skill を配置・公開・検証するときに読む。

## 自作 Skill

1. `.agents/skills/<category>/<skill-name>/SKILL.md` を作る。
2. 必要なら `.agents/skills/<category>/<skill-name>/references/` に詳細を分ける。
3. `.agents/README.md` の Available Skills に、人間向けの 1 行説明を追加する。
4. `claude/CLAUDE.md` は `.agents/README.md` を source of truth として参照する。原則として skill ごとの一覧は増やさない。

## Installed Skill

third-party skill は wrapper で `.agents/installed-skills` に入れる。

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

## 即時公開

Home Manager は `.agents/skills` と `.agents/installed-skills` の `SKILL.md` を持つ directory を publish する。すぐ使いたい場合は Codex / Cursor / Claude Code の skills directory に symlink を張る。

## 検証

公開 path を確認する。

```sh
find -L ~/.codex/skills ~/.cursor/skills ~/.claude/skills -maxdepth 4 -name SKILL.md -print
```

Home Manager helper を評価する。

```sh
export dotfilesDir="$(git rev-parse --show-toplevel)"
nix eval --no-write-lock-file --impure --raw --expr \
  'let pkgs = import <nixpkgs> {}; lib = pkgs.lib; dotfilesDir = builtins.getEnv "dotfilesDir"; agentSkills = import ./nix/modules/home/programs/agent-skills.nix { inherit lib dotfilesDir; }; in agentSkills.linkCommands "/tmp/agent-skills-target"'
```

新規 file / directory は Nix flake から見えるように `git add` する。commit はユーザーの明示許可があるまでしない。
