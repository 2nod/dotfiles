# Dotfiles Skill Workflow

dotfiles の shared skill を配置・公開・検証するときに読む。

## 自作 Skill

1. `.agents/skills/<category>/<skill-name>/SKILL.md` を作る。
2. 必要なら `.agents/skills/<category>/<skill-name>/references/` に詳細を分ける。
3. `.agents/README.md` に skill ごとの一覧は追加しない。`SKILL.md` の frontmatter と `find` 結果を source of truth にする。
4. `claude/CLAUDE.md` も skill ごとの一覧は増やさない。

## Installed Skill

third-party skill は wrapper で `.agents/installed-skills` に入れる。
installed skill は upstream の内容を追跡しやすくするため、`SKILL.md` を原則そのまま保存する。
trigger や本文を整理したい場合でも、分割・要約・編集は避ける。
必要なローカル補足は `SOURCE.md` など別ファイルに置き、upstream 由来の `SKILL.md` と混ぜない。
参照元 URL、repo、path、取得元が分かる情報を必ず残す。

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

手動で追加した installed skill も、出典は各 skill の `SOURCE.md` に残し、`.agents/README.md` に skill ごとの一覧は追加しない。

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
