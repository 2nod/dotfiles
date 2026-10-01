# Shared Agent Skills

`.agents` は、複数の agent から使う shared skill を dotfiles で管理するための領域である。

この README は、この領域の役割と主要な参照先だけを示す。
個別 skill の一覧、authoring rule、install 手順、runtime rule はここに置かない。

## 構成

- `.agents/skills/`: この repo で自作する skill。
- `.agents/installed-skills/`: third-party 由来の installed skill。
- `.agents/bin/`: skill 管理用の補助 command。

## 参照先

- skill 全般の方針: `agent-management/skill-governance`
- skill の作成、更新、install、検証手順: `agent-management/skill-maintenance`
- 実行時の agent-specific rule: `codex/AGENTS.md`, `claude/CLAUDE.md` など

## Source Of Truth

skill の発見と発火条件は、各 skill の `SKILL.md` frontmatter を source of truth にする。
この README には skill ごとの手書き一覧を持たない。

本文・同梱ファイルの正本は、自作が `.agents/skills/`、外部由来が
`.agents/installed-skills/`。編集・更新はこの2箇所で行い、Nix が同じ bundle を
各 agent へ配布する。配布先は直接編集しない。

| Reader | 配布先 | 形式 |
| --- | --- | --- |
| Codex / ローカル Cursor | `~/.agents/skills/` | Nix 生成物へのリンク |
| Claude Code | `~/.config/claude/skills/dotfiles-shared-skills/` | 生成した plugin へのリンク |

Cursor 専用の重複配布は行わない。Cloud Agents への同期が必要になった場合だけ、
`~/.cursor/skills/` への配布を別途設定する。

Codex は配布先の `~/.agents/skills` を利用する。dotfiles 内で作業すると正本の
`.agents/skills` も検出されるため、`nix/modules/home/programs/codex.nix` が原本側の
`SKILL.md` を列挙して `skills.config` で無効化し、二重読み込みを防ぐ。
正本の変更は `nix run .#switch -- <profile>` で配布した後に通常利用へ反映される。

```sh
find .agents/skills .agents/installed-skills -mindepth 2 -maxdepth 4 -name SKILL.md -print
```
