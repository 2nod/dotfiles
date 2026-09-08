## Skills

These skills are discovered at startup from multiple local sources. Each entry includes a name, description, and file path so you can open the source for full instructions.

- skill-creator: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Codex's capabilities with specialized knowledge, workflows, or tool integrations. (file: /Users/tsuno/.config/codex/skills/.system/skill-creator/SKILL.md)
- skill-installer: Install Codex skills into $CODEX_HOME/skills from a curated list or a GitHub repo path. Use when a user asks to list installable skills, install a curated skill, or install a skill from another repo (including private repos). (file: /Users/tsuno/.config/codex/skills/.system/skill-installer/SKILL.md)
- Discovery: Available skills are listed in project docs and may also appear in a runtime "## Skills" section (name + description + file path). These are the sources of truth; skill bodies live on disk at the listed paths.
- Trigger rules: If the user names a skill (with `$SkillName` or plain text) OR the task clearly matches a skill's description, you must use that skill for that turn. Multiple mentions mean use them all. Do not carry skills across turns unless re-mentioned.
- Missing/blocked: If a named skill isn't in the list or the path can't be read, say so briefly and continue with the best fallback.
- How to use a skill (progressive disclosure):
  1) After deciding to use a skill, open its `SKILL.md`. Read only enough to follow the workflow.
  2) If `SKILL.md` points to extra folders such as `references/`, load only the specific files needed for the request; don't bulk-load everything.
  3) If `scripts/` exist, prefer running or patching them instead of retyping large code blocks.
  4) If `assets/` or templates exist, reuse them instead of recreating from scratch.
- Description as trigger: The YAML `description` in `SKILL.md` is the primary trigger signal; rely on it to decide applicability. If unsure, ask a brief clarification before proceeding.
- Coordination and sequencing:
  - If multiple skills apply, choose the minimal set that covers the request and state the order you'll use them.
  - Announce which skill(s) you're using and why (one short line). If you skip an obvious skill, say why.
  - Use this format when helpful: `Using skill: <category>/<skill-name>` followed by `Use: <one short phrase>`.
- Context hygiene:
  - Keep context small: summarize long sections instead of pasting them; only load extra files when needed.
  - Avoid deeply nested references; prefer one-hop files explicitly linked from `SKILL.md`.
  - When variants exist (frameworks, providers, domains), pick only the relevant reference file(s) and note that choice.
- Safety and fallback: If a skill can't be applied cleanly (missing files, unclear instructions), state the issue, pick the next-best approach, and continue.

## skill eval case の継続追加

共有 skill を使った実作業の完了時に、その skill の効果または弱点を客観的に再現できる新しいパターンが見つかったら、`~/dotfiles/.agents/evals/` の既存 case を確認する。同等の case がなく、skill の有無で結果が変わり得る決定的 verifier を作れる場合は、ユーザーへの追加確認なしで最小の eval case を追加する。

- 実案件の code、prompt、固有名詞、秘密情報はコピーせず、匿名化した合成 fixture にする。
- network、credential、時刻に依存させない。
- verifier は未修正 fixture で失敗し、期待する最小修正で成功することを確認する。
- `agent-observability-eval <case> --runs 1 --dry-run` まで実行する。有料の比較評価は自動実行しない。
- 安全に縮約できない、客観的 verifier がない、既存 case と重複する場合は追加しない。
- `agent-observability-eval` が起動した評価 run では追加しない。

## 実装・実験レポート

HTMLまたはSite形式のレポートをユーザーが明示的に依頼した場合だけ、実装は `software-development/build-implementation-report-site`、比較実験は `software-development/build-experiment-report-site` を使う。

- 通常の実装・修正・テスト・実験の依頼だけではHTMLレポートを作らない。
- 必要な検証を行い、結果と未検証事項をチャットで簡潔に伝える。再確認に必要なログを残す。
- 明示依頼で作るレポートと画像は製品リポジトリ外へ保存し、stage・commit・push・PRへ含めない。最終回答に保存先を示す。
