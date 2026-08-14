---
name: pr-diff-findings
description: GitHub PRの変更差分を初回レビューし、コードの意味理解と品質チェックに基づく指摘事項を、優先度付きのインライン案として作成するときに使う。レビューの修正必須度をprefixで示すときにも使う。
metadata:
  tags: [github, pull-request, review, comments]
  related_skills:
    - software-development/pr-review-fix-workflow
    - software-development/test-design-review
---

# PR差分レビュー所見

GitHub PRの差分を読み、コードの意味を理解して品質上の問題を見つけるためのコメント案を作る。
設計決定や既存コメント対応は扱わない。

## 手順

1. PRのdescription、baseとheadの差分、近接するテスト、関連する仕様やADRを読む。
2. 変更の目的、公開契約、データと制御の流れ、失敗時の挙動を確認する。
3. 正しさ、セキュリティ、信頼性、データ整合性、テスト、保守性の順に、変更行に根拠のある所見を探す。
4. 各所見を変更行、条件、影響、修正または確認方法に結び付ける。
5. 意味を読み取れない場合は、推測で問題を断定せず、質問か具体的な理解支援にする。

設計、API方針、データモデルはPR作成前に文書で決める。
PR上でその判断を始めず、無関係なリファクタリング、個人的な好み、単なる整形も指摘しない。
指摘がなければ「actionableな指摘なし」と明記し、残るテスト不足や未確認事項を分けて記録する。

## コメントprefix

- `[nits]`：細部の指摘。対応は任意。
- `[imo]`：意見や代替案。対応は任意。
- `[ask]`：質問や確認。回答を必須とする。
- `[warning]`：修正または確認がない限りApproveできない問題。
- `[memo]`：コード理解のための補足。対応は求めない。

「気になる」とだけ書かず、問題になる理由、発生条件、影響、修正または確認方法を書く。

## 出力形式

所見は重要度順に並べる。

```text
[warning] path/to/file.ts:42
問題: どの条件で、どの動作が壊れるか。
影響: 利用者、データ、運用に起きること。
提案: 修正方法または確認すべき契約・テスト。
```

GitHubへの投稿は明示依頼がある場合だけにする。
AI作成のインラインコメントを投稿するときは、[reply-format.md](../pr-review-fix-workflow/references/reply-format.md) の詳細欄形式を使う。

## 役割の境界

- 既存コメントの修正と返信：`software-development/pr-review-fix-workflow`
- テスト設計：`software-development/test-design-review`
- モジュール境界と公開インターフェース：`engineering/codebase-design`
