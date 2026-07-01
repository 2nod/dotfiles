---
name: github-pr-morning-triage
description: 毎朝 GitHub の issue/PR を確認し、PR の依存関係、review 状況、CI、mergeability、未返信コメントを見て、今日のネクストアクション順に整理するときに使う。GitHub Morning Brief、PR Dependency Triage、朝の GitHub 棚卸し、レビュー待ち整理、マージ順整理に使う。
metadata:
  tags: [github, pull-request, triage, review, workflow]
---

# GitHub PR Morning Triage

毎朝の GitHub 確認を「一覧」ではなく「どの順番で詰まりを解くか」に変換する。

## ゴール

出力は、ユーザーが次の 10 分で動ける形にする。

- 最初に着手する PR / issue が分かる
- stacked PR の前後関係が分かる
- review 待ち、返信待ち、merge 待ち、CI 対応待ちが分かれる
- 依存先が詰まっている PR を催促対象にしない
- merge してよい候補と、まだ確認が必要な候補を混ぜない
- review 対応が必要なものは、対象コメント、必要な判断、作業開始プロンプトまで揃える

## 取得する情報

対象は、ユーザーが普段の仕事で確認したい organization / team repository に絞る。個人 repository は、ユーザーが明示的に依頼した場合だけ対象にする。

GitHub CLI が使える場合は、まず対象 owner を指定して次を取得する。

```bash
gh search prs --owner <org-or-owner> --author @me --state open --limit 30 --json repository,title,number,url,updatedAt,isDraft,labels
gh search prs --owner <org-or-owner> --review-requested @me --state open --limit 30 --json repository,title,number,url,updatedAt,author,isDraft
gh search issues --owner <org-or-owner> --assignee @me --state open --limit 30 --json repository,title,number,url,updatedAt,labels,isPullRequest
gh search issues --owner <org-or-owner> --mentions @me --state open --limit 30 --json repository,title,number,url,updatedAt,author,labels
```

重要 PR については `gh pr view` で詳細を見る。

```bash
gh pr view <number> --repo <owner/repo> --json number,title,url,isDraft,reviewDecision,mergeStateStatus,mergeable,baseRefName,headRefName,body,reviewRequests,reviews,comments,latestReviews,commits,statusCheckRollup,updatedAt
```

## 判断手順

1. `reviewDecision`, `mergeable`, `mergeStateStatus`, `statusCheckRollup` で merge 可能性を分ける。
2. `baseRefName` が `main` / `master` / default branch 以外なら stacked PR として扱う。
3. PR body / comments から `#1234`, `pull/1234`, `前段`, `依存`, `ベースPR`, `blocked by`, `depends on` を拾う。
4. `reviewRequests` が残っている PR は「review 待ち」にする。ただし依存先が未解決なら催促対象にしない。
5. `latestReviews` と最新コメントを見て、最後の有意味な要求が誰から誰に向いているかを判断する。
6. 自分が「対応しました」「確認お願いします」と書いた後に reviewer response がなければ reviewer 待ち。
7. reviewer が質問・依頼・別 PR 参照を返していれば自分の確認待ち。
8. draft PR は merge queue から外し、「棚卸し」枠に置く。

## 優先度

1. 自分が返すべき質問・確認依頼
2. CI failed / blocked / dirty / conflict
3. 依存チェーンの最上流で、approved + mergeable + CI pass の PR
4. review requested to me
5. reviewer 待ちだが、依存先が解けていて催促してよい PR
6. stale な ready PR
7. draft / 長期放置 PR の棚卸し

## 出力

最終出力には [templates/morning-triage.md](templates/morning-triage.md) を使う。

review 対応が必要な PR / issue がある場合は、あわせて [templates/review-action-pack.md](templates/review-action-pack.md) を使い、すぐ Codex session に渡せる形にする。

詳細な読み取り観点が必要なときは [references/triage-guide.md](references/triage-guide.md) を読む。
