# Agent Instructions

Shared skills are managed in the dotfiles repository:

`~/dotfiles/.agents`

When the user names a skill, or when a task clearly matches a skill description, read the matching `SKILL.md` and follow it for that turn. The skill description is the primary trigger signal.

When using a skill, briefly state which skill is being used and why. Keep it to one short line, for example: `Using skill: <category>/<skill-name> — <one short phrase>`.

Use `~/dotfiles/.agents/README.md` as the source of truth for the current shared skill list and management workflow.

## 実装完了時の検証レポート

製品コード、設定、APIやDB契約、運用スクリプトを実装または修正した場合は、軽微な変更を除き、最終回答の前に `software-development/build-implementation-report-site` を使って実装・検証レポートを作成または更新する。

- レポートと検証画像は製品リポジトリ外へ保存する。
- レポートを `git add`、commit、push、PRへ含めない。
- 最終回答にレポートの絶対パスまたはURLを示す。
- 軽微な変更の判断は同skillの「作成要否」に従う。省略時も必要な検証を行い、最終回答に変更内容と検証結果を短く示す。
- 明示的なレポート依頼がなければ、軽微な変更、調査、回答、docsだけの変更、生成物更新だけの作業は対象外とする。
