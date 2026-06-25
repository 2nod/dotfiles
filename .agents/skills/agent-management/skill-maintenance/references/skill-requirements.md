# 新規 Skill の要件

skill を新規作成・更新するときに確認する。

## 必須要件

- `SKILL.md` に `name` と `description` の frontmatter がある。
- `description` は「いつ使うか」が分かる trigger 文になっている。
- skill directory は `<category>/<skill-name>` の 2 segment で公開できる。
- `skill-name` は lowercase hyphen-case にする。
- 個人環境の絶対パスを書かない。dotfiles 内は repo root 相対で書く。
- 自作 skill と installed skill で同じ公開 path を使わない。

## `SKILL.md` の文字量目安

`SKILL.md` は常時読まれる入口なので、目安は本文 800-1200 字程度、長くても 1500 字以内に収める。

1500 字を超えそうな場合は、詳細を `references/` に分ける。特に次は reference に置く。

- 長い返信フォーマット
- review checklist
- コマンド例が多い手順
- domain 固有の詳細ルール
- 過去事例に強く依存する説明

## 避けること

- `README.md` や `QUICK_REFERENCE.md` など、skill 実行に不要な補助文書を増やす。
- 特定ケースに寄った判断を汎用ルールとして書く。
- `SKILL.md` に reference と同じ内容を重複して書く。
- 起動済み agent に即時反映される前提で説明する。
