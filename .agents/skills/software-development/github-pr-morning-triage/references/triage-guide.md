# GitHub PR Morning Triage Guide

## 対象スコープ

普段の仕事で確認したい organization / team repository だけを見る。

個人 repository は、ユーザーが明示的に依頼した場合だけ対象にする。朝の通常トリアージでは混ぜない。

## 分類ラベル

- `DO_NOW`: 自分が今返す、直す、確認する
- `MERGE_CANDIDATE`: merge 可能そうだが、必要条件を確認する
- `UNBLOCK_CHAIN`: 依存チェーンの上流を片付ける
- `WAIT_REVIEW`: reviewer の反応待ち
- `REQUEST_REVIEW`: 催促してよい
- `WAIT_DEPENDENCY`: 依存先が未解決なので待つ
- `CI_ACTION`: CI / conflict / mergeability 対応
- `DRAFT_CLEANUP`: draft や古い PR の棚卸し

## 依存関係の読み方

強い依存:

- `baseRefName` が default branch ではない
- body に「この PR は #1234 を前提」「前段 PR」「ベース PR」とある
- comments で reviewer が別 PR の確認を求めている

弱い関連:

- body の「関連」「参考」「follow-up」
- 同じ機能名や branch 名だが、base が default branch

強い依存がある PR は、依存先が `MERGE_CANDIDATE` か `merged` になるまで review 催促の優先度を下げる。

## Review 状況の読み方

`reviewDecision` だけで判断しない。

- `APPROVED` でも、最新コメントで別 PR 確認を求められていれば `DO_NOW`
- `reviewRequests` が残っていても、依存先が未解決なら `WAIT_DEPENDENCY`
- `COMMENTED` の中に未対応質問がある場合は `DO_NOW`
- 自分の「対応しました」以降に reviewer の反応がなければ `WAIT_REVIEW` / `REQUEST_REVIEW`

## CI / mergeability

見る順番:

1. `mergeable`
2. `mergeStateStatus`
3. failed / pending check
4. skipped check が必須扱いかどうか

`MERGEABLE`, `CLEAN`, CI success でも、review request や依存先コメントが残っていれば merge 候補には「確認付き」と書く。

## 最新コメントの向き

コメントの向きを判断する。

- reviewer -> author: 質問、確認依頼、別 PR 参照なら自分待ち
- author -> reviewer: 対応報告、確認依頼なら reviewer 待ち
- bot / AI review: 人間が採用したものだけ action にする

AI review の High / Medium は、その後の author response と commit で処理済みか確認する。

## Review 対応パック

`Need My Response` に入るものがある場合は、単に「確認する」と書かず、すぐ取り掛かれる情報をまとめる。

必ず含めるもの:

- 対象 PR / issue URL
- 対象コメント URL
- 何を聞かれているか
- 自分が判断すべきこと
- 修正が必要そうなファイル / package / test
- 関連 PR / 依存 PR
- 既に分かっている CI / review / mergeability 状態
- Codex session に渡す開始プロンプト

必要なら含めるもの:

- 既存の Codex session / thread が分かる場合はその URL や thread id
- 既存 session が分からない場合は「新規 session でよい」と明記
- 作業 repo / branch / base branch
- reviewer への返信草案

Codex session の扱い:

- 既にその PR 用の session が会話や PR コメントから分かる場合は、対象 session として書く。
- 分からない場合は session を推測しない。「新規 Codex session で開始」と書く。
- 依存 PR がある場合は、上流 PR の session で対応すべきか、対象 PR の新規 session で対応すべきかを分ける。

開始プロンプトは、次の形にする。

```text
<repo> の PR #<number> の review 対応をしてください。

対象コメント:
- <comment-url>

確認してほしいこと:
- <reviewer が求めている確認・修正>

前提:
- base/head: <base> <- <head>
- 依存 PR: <related-pr>
- CI: <ci-state>
- review: <review-state>

進め方:
1. PR diff と対象コメントを確認
2. 必要なら関連 PR も確認
3. 修正案または返信方針を整理
4. 実装が必要なら最小変更で対応
5. 実行した確認と reviewer 返信案を出す
```

## 悪い出力

単なる一覧:

```text
Open PRs: 8
Review requested: 0
CI failed: 0
```

これは行動につながらない。

## 良い出力

依存チェーンと行動順にする。

```text
Do first:
1. #2726 can probably merge. Confirm no pending review request.
2. #2730 depends on #2726, but #2757 may change implementation. Check #2757 first.
3. #2735 depends on #2730. Do not ask for review until #2730 lands.
```

review 対応がある場合は、作業開始パックを付ける。

```text
Review Action Pack

Target: owner/repo #1234
Comment: https://github.com/owner/repo/pull/1234#discussion_r...
Decision needed: Replace implementation A with B, or explain why A is intentional.
Suggested session: New Codex session
Prompt: ...
```
