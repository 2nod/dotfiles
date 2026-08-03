---
name: async-workflow-operations
description: 非同期 Workflow の実行状況、正常完了、失敗、手動キャンセル後の後始末を確認するときに使う。Pub/Sub、キュー、worker、callback、成果物を持つ処理の運用確認や、途中終了したジョブの安全な終了処理にも使う。
metadata:
  tags: [workflow, async, pubsub, callback, operations]
  related_skills:
    - engineering/diagnosing-bugs
---

# 非同期 Workflow の運用確認

非同期 Workflow は、親実行が終わっただけでは完了と判断しない。

入力、子実行、worker、成果物、callback、呼び出し元のジョブを一つの処理として確認する。

実行前に、環境、親実行 ID、子実行 ID、job ID、callback URL、入力 artifact の場所を記録する。

正常完了では、親と必要な子実行が成功状態であることを確認する。

最終 artifact が存在し、形式、件数、workflow 固有の必須値と null になる値を読めることを確認する。

callback の受信と、呼び出し元のジョブが成功状態になったことも確認する。

Pub/Sub や worker を使う場合は、対象 job ID のログが完了後に増えないことを確認する。

subscription の backlog と worker の状態は共有基盤の健全性として扱う。

共有 subscription の backlog や MIG の target size だけでは、対象ジョブの残作業を断定しない。

手動キャンセルでは、親 Workflow の cancel が配送済みメッセージを取り消さないことを前提にする。

対象の親と子を terminal にした後、対象 job ID の worker 出力が止まるまで確認する。

呼び出し元が callback を受けずに InProgress のままなら、実装済みの error callback API を使う。

この API 呼び出しは状態変更なので、環境、job ID、callback 未受信を確認し、ユーザーの明示的な許可を得てから行う。

共有 subscription の purge、共有 worker や MIG の削除、resize は一つのジョブの後始末として行わない。

途中 artifact は原因調査に必要なため、完了確認の直後に削除しない。

削除は対象 job prefix だけに限定し、ユーザーが別途許可した場合に行う。

詳しい確認項目は [references/lifecycle-checklist.md](references/lifecycle-checklist.md) を参照する。
