---
name: pr-review-fix-workflow
description: GitHub PR のレビューコメント対応、CI 落ちの修正、コメントごとに何を直すかの整理、レビュー返信文の作成、変更内容と返信内容の整合確認を行うときに使う。PR コメント対応の変更・確認・push・返信を追跡可能な形で進める。
metadata:
  tags: [github, pull-request, review, workflow]
---

# PR レビュー対応ワークフロー

GitHub PR のレビューコメントや CI の失敗に対応するときに使う。

## 基本ループ

1. 現在の branch、base branch、PR 番号、レビューコメントを確認する。
2. コメントごとに「何を指摘されたか」「何を直すか」「1 commit に含める範囲」「返信文」「確認方法」を整理する。
3. コメントに対して必要十分な最小変更を実装する。
4. まず変更箇所に近い最小限の確認を実行し、必要な場合だけ影響範囲を広げて確認する。
5. commit / push / review reply 投稿の前に、リポジトリの指示、作業ツリーの状態、ユーザーの明示許可を確認する。
6. push / rebase 後は、返信や PR 説明が現在の変更内容と一致しているか確認する。

## 安全境界

- commit、push、rebase、review comment への投稿、PR description の更新は state-changing action として扱う。
- ユーザーが明示的に依頼していない state-changing action は実行せず、返信文や実行予定だけを提示する。
- 既存の未関係な変更を巻き込まない。必要な場合は、対象ファイルと理由をユーザーに示してから進める。

## 参照

- 返信文を作るときは [references/reply-format.md](references/reply-format.md) を読む。
- 標準の返信文は [templates/review-reply.md](templates/review-reply.md) を構造として使う。
