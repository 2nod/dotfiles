# 新規 Skill の要件

skill を新規作成・更新するときに確認する。

## 必須要件

- `SKILL.md` に `name` と `description` の frontmatter がある。
- `description` は「いつ使うか」が分かる trigger 文になっている。
- skill directory は `<category>/<skill-name>` の 2 segment で公開できる。
- `skill-name` は lowercase hyphen-case にする。
- 個人環境の絶対パスを書かない。dotfiles 内は repo root 相対で書く。
- 自作 skill と installed skill で同じ公開 path を使わない。
- 成果物の雛形がある場合は `templates/` に置き、`SKILL.md` から template 名を明示する。
- agent 横断の整理用に、必要なら `metadata.tags` と `metadata.related_skills` を書く。
- 日本語で自作 `SKILL.md`、`references/`、`templates/` を書くときは、`writing/japanese-tech-writing` も併用し、冗長さ、LLM っぽい表現、論理の曖昧さを点検する。

例:

```yaml
metadata:
  tags: [github, review, workflow]
  related_skills:
    - software-development/test-driven-development
```

## 自作 `SKILL.md` の文字量目安

自作 skill の `SKILL.md` は常時読まれる入口なので、目安は本文 800-1200 字程度、長くても 1500 字以内に収める。

1500 字を超えそうな場合は、詳細を `references/` に分ける。特に次は reference に置く。

- 長い返信フォーマット
- review checklist
- コマンド例が多い手順
- domain 固有の詳細ルール
- 過去事例に強く依存する説明

成果物として生成する型は `references/` ではなく `templates/` に置く。特に次は template に置く。

- issue body
- ADR
- handoff document
- spike README / verdict
- 調査レポート
- PR description

## 避けること

- `README.md` や `QUICK_REFERENCE.md` など、skill 実行に不要な補助文書を増やす。
- 特定ケースに寄った判断を汎用ルールとして書く。
- `SKILL.md` に reference と同じ内容を重複して書く。
- 起動済み agent に即時反映される前提で説明する。
- Codex など特定 agent だけに閉じた書き方にする。原則として Codex / Cursor Agent / Claude Code などから読める shared skill として書く。

## Installed Skill の要件

installed skill の全体方針は `agent-management/skill-governance` に従う。
更新・install 作業では、少なくとも次を確認する。

- third-party 由来の `SKILL.md` と同梱 directory を、upstream 追跡可能な形で置いている。
- `SOURCE.md` に repository、source path、pinned commit、raw URL、install command などが残っている。
- ローカル挙動を変えたい場合、installed skill の本文ではなく自作 wrapper skill で扱っている。
