# 新規 Skill の要件

skill を新規作成・更新するときに確認する。

## 必須要件

- `SKILL.md` に `name` と `description` の frontmatter がある。
- `description` は「いつ使うか」が分かる trigger 文になっている。
- `description` は Agent Skills 仕様上 1-1024 characters に収める。実用上は数文から短い段落程度にする。
- `description` には「何をする skill か」と「どんな依頼で使うか」を入れる。発火条件は本文ではなく `description` に書く。
- skill directory は `<category>/<skill-name>` の 2 segment で公開できる。
- `skill-name` は lowercase hyphen-case にする。
- 個人環境の絶対パスを書かない。dotfiles 内は repo root 相対で書く。
- 自作 skill と installed skill で同じ公開 path を使わない。

## 自作 `SKILL.md` 本文の文字量目安

自作 skill の `SKILL.md` 本文は、core workflow と読むべき reference の案内に絞る。
Agent Skills 仕様の progressive disclosure に合わせ、本文は 5000 tokens 未満、500 行未満に保つ。
日本語で `description` や本文を書く場合は、`writing/japanese-tech-writing` を使って文意、論理、冗長さを点検する。

本文が 100 行を超えそうな場合や、詳細ルールを毎回読む必要がない場合は、詳細を `references/` に分ける。
特に次は reference に置く。

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

## Installed Skill の要件

- third-party 由来の `SKILL.md` は、原則として upstream の内容をそのまま保存する。
- `SKILL.md` を分割、要約、再構成しない。更新時に upstream との差分を追いにくくなるため。
- 参照元 URL、repo、path、raw URL などを `SOURCE.md` に残す。
- ローカル補足が必要な場合は、upstream の `SKILL.md` とは別ファイルに書く。

## 根拠

- Agent Skills specification: `description` は 1-1024 characters、本文は 5000 tokens 未満かつ 500 行未満が推奨。https://agentskills.io/specification
- Agent Skills optimizing descriptions: `description` は数文から短い段落程度にし、何をするかよりもユーザー意図と発火条件を明確にする。https://agentskills.io/skill-creation/optimizing-descriptions
- Claude Code skills docs: skill body は発火後に読み込まれるため、本文は簡潔にし、詳細は supporting files に分ける。https://code.claude.com/docs/en/skills
