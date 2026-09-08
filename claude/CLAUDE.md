# Agent Instructions

Shared skills are managed in the dotfiles repository:

`~/dotfiles/.agents`

When the user names a skill, or when a task clearly matches a skill description, read the matching `SKILL.md` and follow it for that turn. The skill description is the primary trigger signal.

When using a skill, briefly state which skill is being used and why. Keep it to one short line, for example: `Using skill: <category>/<skill-name> — <one short phrase>`.

Use `~/dotfiles/.agents/README.md` as the source of truth for the current shared skill list and management workflow.

## 実装・実験レポート

HTMLまたはSite形式のレポートをユーザーが明示的に依頼した場合だけ、実装は `software-development/build-implementation-report-site`、比較実験は `software-development/build-experiment-report-site` を使う。

- 通常の実装・修正・テスト・実験の依頼だけではHTMLレポートを作らない。
- 必要な検証を行い、結果と未検証事項をチャットで簡潔に伝える。再確認に必要なログを残す。
- 明示依頼で作るレポートと画像は製品リポジトリ外へ保存し、stage・commit・push・PRへ含めない。最終回答に保存先を示す。
