# 非同期 Workflow の確認項目

## 正常完了

1. 親 Workflow と、fan-out した子 Workflow が terminal であることを確認する。
2. `SUCCEEDED` だけでなく、最終 artifact を読み込む。
3. artifact の形式、ページ数や件数、必須 field、workflow 固有の null 値を確認する。
4. callback の受信と、呼び出し元のジョブの成功状態を確認する。
5. 対象 job ID の worker ログが terminal 後に増えないことを確認する。
6. 関連 subscription の backlog と worker の状態を共有基盤の観測値として記録する。

## 失敗

1. 親と子の失敗状態、失敗した step、原因となるログを記録する。
2. error callback が呼び出し元へ届き、ジョブが失敗状態になったことを確認する。
3. request、入力 artifact、中間 artifact を残し、再実行や削除は原因を特定してから判断する。

## 手動キャンセル

1. 環境、親実行 ID、子実行 ID、remote job ID、呼び出し元の job ID、理由を記録する。
2. 特定した親と子だけを cancel する。
3. Workflow が terminal になった後も、配送済み worker の対象 job ID ログを確認する。
4. subscription backlog は共有キューの健康状態として確認する。
5. callback が届かず呼び出し元が InProgress の場合だけ、既存の error callback API で失敗に遷移する。
6. API 契約を読み直し、対象環境と ID を再確認してから送信する。
7. partial artifact を残す。

## 報告

結果は次の項目を分けて報告する。

- Workflow の terminal state
- 呼び出し元ジョブの state
- 対象 job ID の worker activity
- artifact と callback の状態
- 共有 Pub/Sub、worker、MIG の観測値
- 実行しなかった操作と理由
