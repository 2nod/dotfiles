# Dotfiles Skill Workflow

dotfiles の shared skill を配置・公開・検証するときに読む。

## 自作 Skill

1. `.agents/skills/<category>/<skill-name>/SKILL.md` を作る。
2. 必要なら `.agents/skills/<category>/<skill-name>/references/` に詳細・判断材料・長い手順を分ける。
3. 成果物として生成する型がある場合は `.agents/skills/<category>/<skill-name>/templates/` に雛形を置く。
4. `SKILL.md` から使う template 名を明示する。例: `templates/bug-report.md` を issue body の構造として使う。
5. agent 横断で整理しやすいように、frontmatter には必要に応じて `metadata.tags` と `metadata.related_skills` を書く。
6. `.agents/README.md` に skill ごとの一覧は追加しない。`SKILL.md` の frontmatter と `find` 結果を source of truth にする。
7. `claude/CLAUDE.md` など agent 固有 instructions には、skill ごとの一覧を増やさない。agent 固有の discovery 制約がある場合だけ最小限の補足を書く。

## 責務の置き場所

skill 管理の文書と agent 実行時の指示を混ぜない。
`skill-maintenance` は skill を作成・更新・install・整理するための workflow に限定する。

- skill 全体の方針: `agent-management/skill-governance` に書く。
- skill の作成、配置、metadata、templates、installed skill の操作手順: `skill-maintenance` とその `references/` に書く。
- skill を通常利用するときの会話ルール: `codex/AGENTS.md`, `claude/CLAUDE.md` など、その agent が実際に読む agent-specific instruction に書く。
- shared skill 全体の入口や source of truth の案内: `.agents/README.md` に短く書く。

たとえば「skill を使うときは会話で skill 名を示す」という runtime behavior は `skill-maintenance` に書かない。
それは skill を作る手順ではなく、agent が対話中に従う実行時ルールだから。
Codex / Claude Code は、それぞれの dotfiles 配下に agent-specific instruction を置き、Home Manager で実際の読み込み先へ link する。
Cursor Agent は global runtime rule を dotfiles から安全に同期できる公式ファイル形式が確認できるまで、runtime rule 管理の対象にしない。

`references/` と `templates/` は役割で分ける。

- `references/`: agent が読んで判断する説明、workflow、checklist、背景情報。
- `templates/`: agent がコピー・展開して実際の成果物にする雛形。issue body、ADR、調査メモ、handoff、spike verdict など。
- `scripts/`: agent が実行する補助スクリプト。
- `assets/`: 画像、サンプルデータ、固定リソース。

## Installed Skill

installed skill の方針は `agent-management/skill-governance` に従う。
third-party skill は wrapper command で `.agents/installed-skills` に入れる。

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
ローカル向けに template を変えたい場合は installed skill を編集せず、`.agents/skills/<category>/<skill-name>` に自作 wrapper skill を作る。

## 即時公開

Home Manager は `.agents/skills` と `.agents/installed-skills` の `SKILL.md` を持つ directory を、configured agent の skills directory に publish する。
すぐ使いたい場合は Codex / Cursor Agent / Claude Code などの skills directory に symlink を張る。
外部 skill directory を直接読める agent では、per-skill symlink を増やさず `.agents/skills` と `.agents/installed-skills` を直接読む運用を優先する。

## 検証

skill を追加・更新したら、まず次の最小検証を行う。

```sh
rg --files .agents | rg '(^|/)SKILL\.md$'
rg -n '^(name|description):' .agents/skills .agents/installed-skills
.agents/bin/check-skill-triggers
git diff --cached --stat
git status --short
```

`SKILL.md` が `references/`, `templates/`, `scripts/`, `assets/` を参照している場合は、参照先が存在することも確認する。
shell 設定や補助 script を変更した場合は、対象 shell の構文検査や代表コマンドも実行する。

公開 path を確認する。

```sh
find -L ~/.codex/skills ~/.cursor/skills ~/.claude/skills -maxdepth 4 -name SKILL.md -print
```

外部 skill directory 設定を持つ agent では、dotfiles の `.agents/skills` と `.agents/installed-skills` が読み込み対象に含まれていることを確認する。

Home Manager helper を評価する。

```sh
export dotfilesDir="$(git rev-parse --show-toplevel)"
nix eval --no-write-lock-file --impure --raw --expr \
  'let pkgs = import <nixpkgs> {}; lib = pkgs.lib; dotfilesDir = builtins.getEnv "dotfilesDir"; agentSkills = import ./nix/modules/home/programs/agent-skills.nix { inherit lib dotfilesDir; }; in agentSkills.linkCommands "/tmp/agent-skills-target"'
```

新規 file / directory は Nix flake から見えるように `git add` する。commit はユーザーの明示許可があるまでしない。
