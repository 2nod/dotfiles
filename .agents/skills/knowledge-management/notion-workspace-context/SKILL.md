---
name: notion-workspace-context
description: "~/Documents/studio 配下のリポジトリまたはその worktree で行う調査・設計・実装・レビューの開始時に、~/Documents/Notion のローカル knowledge base を読み取り専用の調査データとして参照するときに使う。ユーザーが「Notion のメモを見て」「既存の知見を調べて」と依頼した場合にも使う。"
metadata:
  tags: [notion, knowledge, research, workflow]
  related_skills:
    - knowledge-management/notion-workspace-maintenance
---

# ローカル Notion 文脈の参照

この skill は知識を集めるための読み取り専用の入口である。

ローカル Notion 文書は、この skill だけでは更新しない。

## 作業の開始

`~/Documents/Notion/AGENTS.md` を読み、保存先、同期、直接書き込みの制約を確認する。

現在の worktree と、その worktree が属するリポジトリを確認する。

`personal-workspace-memo/_index.md`、対象タグの `README.md`、対象の既存メモを読む。

全文を一括で読むのではなく、`rg` でドメイン、用語、コンポーネント名から候補を絞る。

ローカル Notion は調査の出発点であり、コード、テスト、実行ログ、正式な契約と矛盾した場合は後者を一次情報とする。

`~/Documents/studio/` 外のリポジトリは、明示的な依頼または API、データ、デプロイの境界を確認する必要がある場合だけ参照する。

## 調査後の扱い

既存メモと一次情報の差異、更新候補、根拠を報告する。

ローカル Notion を更新する必要がある場合は、`notion-workspace-maintenance` を使う。

Notion SaaS、共有ページ、既存ページへは、ユーザーが明示的に許可するまで書き込まない。
