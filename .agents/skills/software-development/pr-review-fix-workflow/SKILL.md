---
name: pr-review-fix-workflow
description: GitHub PR のレビューコメント対応、CI 落ちの修正、コメント別の対応 commit 整理、レビュー返信文の作成、commit link と返信内容の整合確認を行うときに使う。PR コメント対応の変更・検証・push・返信を追跡可能な形で進める。
---

# PR レビュー対応ワークフロー

GitHub PR のレビューコメントや CI feedback に対応するときに使う。

## 基本ループ

1. 現在の branch、base branch、PR 番号、レビューコメントを確認する。
2. コメントごとに次を整理する。
   - 指摘されている具体的な問題
   - 対応する code / doc / test の変更
   - 新しい commit にするか、既存 commit に fold するか
   - ノーコンテキストでも伝わる返信文
3. コメントに対して必要十分な最小変更を実装する。
4. まず focused verification を実行し、影響範囲が広い場合だけ broader verification を追加する。
5. 意図が分かる commit message で commit する。
6. local status と repository instruction を確認してから push する。
7. push / rebase 後は、返信や PR 説明に書いた commit SHA が現在の履歴と一致しているか確認する。

## コメント返信

できるだけレビューコメントごとに 1 つの返信を書く。返信では次を明確にする。

- 何を変更したか
- なぜその変更で指摘に対応できるか
- どの commit に入っているか
- あえて変更しなかった点がある場合はその理由
- 何を検証したか

複数 commit を参照する場合は、それぞれの commit が何に対応しているかを分けて書く。「これらの commit で対応しました」だけで済ませない。

返信例:

```md
対応しました。

- [`abc1234`](https://github.com/OWNER/REPO/commit/abc1234): query-level test に変更
- [`def5678`](https://github.com/OWNER/REPO/commit/def5678): 共有 fixture 依存をやめ、各 `it` 内で arrange する形に整理

確認: `yarn workspace ... test ...`
```

## Commit Link の扱い

branch 履歴が確定するまで commit link は変わり得る。

- autosquash / rebase / amend / force-push をすると、古い commit SHA は間違いになる可能性がある。
- 最終 push 後に `git log --oneline` を確認し、投稿済みの PR 返信と現在の commit SHA を突き合わせる。
- 古い SHA を含む返信があれば GitHub comment を編集する。
- commit link は、履歴の形を決めた後に貼るのが望ましい。

## CI Failure

CI が落ちているとき:

1. Run `gh pr checks <PR>`.
2. `gh run view ... --job ... --log` で failing job log を開く。
3. 失敗している file / line / error を特定する。
4. 可能なら最も近い focused command で local reproduce する。
5. 症状だけでなく root cause を修正する。
6. focused local verification を再実行する。
7. push 後に `gh pr checks <PR>` を再確認する。

local verification が環境要因で blocked の場合は、何が block したかを明示する。通っていない test を通ったように書かない。

## Test Fixture レビューの観点

test readability や DAMP に関するレビューコメントでは、次を確認する。

- 重要な arrange data は、それを assert する `it` の近くに置く。
- nested ORM create shape などの boilerplate を隠す helper は使ってよい。
- helper が test 対象の振る舞いを隠していないか確認する。
- test の意味が前提データに依存する場合、共有 `beforeAll` fixture に寄せすぎない。
- per-test cleanup を削除する場合、test が共有 fixture の mutation に依存して後続 test に影響しないか確認する。
- 間接的な ID より、matched word など振る舞いが直接見える assertion の方が明確ならそちらを選ぶ。

## Commit の粒度

follow-up や CI fix として独立して review しやすい変更は、別 commit にする。

同じレビュー対応への小さな修正で、user が clean history を望む場合は既存 commit に fold してよい。

迷う場合は、過度に賢い履歴より reviewer にとっての分かりやすさを優先する。repository instruction が要求する場合、push 済み履歴を書き換える前に確認する。
