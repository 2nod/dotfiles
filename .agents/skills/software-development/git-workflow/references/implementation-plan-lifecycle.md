# 実装プランの管理

複数工程や設計判断を伴う実装では、リポジトリの規約を確認して `docs/plans/<topic>.md` に実装プランを作る。
plan には目的、対象範囲、判断が必要な点、検証方法、完了条件を書く。

## 共有

plan を他の開発者と相談する必要がある場合は、作業 branch で plan を commit し、push と PR の許可を個別に得て共有する。
相談を必要としないローカル plan は、共有のためだけに commit しない。

## 正本への昇格

実装と検証が完了したら、plan に残った情報を次の置き場所へ分ける。

- 将来の変更を拘束する設計判断と選択理由は `docs/adr` に残す。
- 安定した構造、契約、処理フローは `docs/design` に残す。
- 狭い実装詳細は、対象コードの近くにある README、docstring、テストへ残す。
- 複数repositoryを横断する確定知識は、`notion-workspace-maintenance`の保存判断を満たす場合だけローカル Notionへ残す。

plan 全体を正本へコピーしない。
実装中だけ意味を持つ手順、進捗、未採用案を除き、確定した判断と契約だけを移す。
PR別の検証結果、job ID、deploy tagはPR、CI、実行ログに残し、ローカル Notionへ昇格しない。

## 終了処理

正本と実装が揃ったら、用済みの plan を削除する。
追跡済みの plan は削除を独立した cleanup commit にして、plan が正本として残ったように見える状態を終わらせる。
未追跡の plan は、固有の知識が残っていないことを確認し、破棄対象を示してユーザーの許可を得てから削除する。

ローカル Notion は、現行コード、テスト、正式な契約と照合する。
不一致があれば `notion-workspace-maintenance` に従い、依頼範囲内ならローカル Markdown を訂正し、付随して見つけた場合は訂正案を示す。
Notion SaaS への同期は別途許可を得る。

最後に `git-worktree-cleanup` で worktree と branch の削除可否を監査する。
