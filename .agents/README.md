# Shared Agent Skills

`.agents` は、複数の agent から使う shared skill を dotfiles で管理するための領域である。

この README は、この領域の役割と主要な参照先だけを示す。
個別 skill の一覧、authoring rule、install 手順、runtime rule はここに置かない。

## 構成

- `.agents/skills/`: この repo で自作する personal skill。runtime routing の優先 entrypoint。
- `.agents/installed-skills/`: third-party 由来の installed skill。personal wrapper skill から参照する upstream 保管庫。
- `.agents/bin/`: skill 管理用の補助 command。

## 参照先

- skill 全般の方針: `agent-management/skill-governance`
- skill の作成、更新、install、検証手順: `agent-management/skill-maintenance`
- 実行時の agent-specific rule: `codex/AGENTS.md`, `claude/CLAUDE.md` など

## Source Of Truth

skill の発見と発火条件は、`.agents/skills` の各 `SKILL.md` frontmatter を優先 source of truth にする。
この README には skill ごとの手書き一覧を持たない。

```sh
find .agents/skills .agents/installed-skills -mindepth 2 -maxdepth 4 -name SKILL.md -print
```
