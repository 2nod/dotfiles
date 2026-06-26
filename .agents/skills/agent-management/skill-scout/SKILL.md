---
name: skill-scout
description: shared agent skill を定期点検し、外部の agent workflow 動向も調べて、新規 skill 化・既存 skill 改善・運用保守の提案レポートを作る。ユーザーが「skill を調査して」「skill 候補を探して」「既存 skill を監査して」「定期的に skill を見直して」と依頼したときに使う。ファイル編集なしの提案のみで進めたい場合にも使う。
metadata:
  tags: [skills, audit, agents, maintenance]
  related_skills:
    - agent-management/skill-maintenance
---

# Skill Scout

shared skill の棚卸し、外部動向の確認、skill 化候補の発見、既存 skill の改善提案を行う。
Codex automation の定期実行と、手動の「これは skill 化した方がよいか？」の確認に使う。

## 手順

1. ローカルの skill inventory を確認する。
   - `.agents/skills/**/SKILL.md`
   - `.agents/installed-skills/**/SKILL.md`
   - 必要に応じて、直接参照されている `references/`, `templates/`, `scripts/`, `SOURCE.md`
2. 最近の作業シグナルを確認する。
   - `.agents` 周辺の git 履歴
   - 繰り返し出ているファイル操作、コマンド、レビュー対応、デバッグ手順、文章作成、ドキュメント化
3. Web が使える場合は外部動向を調べる。
   - Codex, Claude Code, Cursor, MCP, agent workflows, hooks, subagents, evals, PR review automation, skill ecosystems
   - レポートには出典リンクを含める
4. レポートだけを出す。
   ユーザーが実装を明示するまで、ファイル編集、stage、commit、push、PR 作成はしない。
5. 日本語でレポートを書くときは `writing/japanese-tech-writing` も併用する。
   冗長さ、LLM っぽい表現、根拠の曖昧さを点検してから返す。

## 点検ルール

- `.agents/skills` は自作 skill として改善提案の対象にする。
- `.agents/installed-skills` は upstream 由来として扱い、直接書き換えではなく、更新・置き換え・wrapper skill・source metadata 補完を提案する。
- 広い一般論より、対象ファイルや根拠が分かる具体的な指摘を優先する。
- ファイル編集、git 操作、外部 credential が必要な action は「要ユーザー承認」と明記する。
- 出典や provenance が不明な場合は、推測で埋めずに不明と書く。
- installed skill に `scripts/`, 外部通信、credential 参照、state-changing command が含まれる場合は、安全点検の対象として明記する。

詳細な点検項目は [references/audit-checklist.md](references/audit-checklist.md) を読む。
標準レポートは [templates/skill-scout-report.md](templates/skill-scout-report.md) を使う。
