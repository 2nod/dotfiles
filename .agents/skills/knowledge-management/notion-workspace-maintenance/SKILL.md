---
name: notion-workspace-maintenance
description: "コード、テスト、実行ログ、正式な契約をもとに、ローカル Notion に知識を残すか削除するかを判断し、実装ドキュメントとの整合性、knowledge repositoryのstageとcommitの境界、Markdown、メタデータ、索引を保守するときに使う。調査、実装、レビュー、検証中に不一致が明らかになった場合にも使う。"
metadata:
  tags: [notion, knowledge, documentation, maintenance]
  related_skills:
    - knowledge-management/notion-workspace-context
    - writing/japanese-tech-writing
---

# ローカル Notion 文書の保守

現在のワークスペース設定やリポジトリ情報からローカル Notion knowledge base を特定する。
個人環境の絶対パスを skill に固定しない。
場所を特定できない場合だけ、ユーザーに確認する。

knowledge base のルートにある `AGENTS.md` と対象文書を読み、更新対象と同期制約を確認する。

knowledge base がGit repositoryの場合は、文書を更新するときと終了処理をするときに[knowledge repositoryのGit境界](references/repository-workflow.md)を読む。

## 更新の判断

新しい文書を作るとき、既存文書を残すか迷うとき、実装終了時に文書を整理するときは、[ローカル Notion の保存判断](references/retention-policy.md)を読む。

コード、テスト、実環境の結果で確認でき、保存条件を満たす知識だけを更新する。

未マージ、レビュー中、未合意、再現確認前の内容は、確定文書へ混ぜない。

同じ主題の文書があれば、先にその文書を訂正または補足する。

## 不一致を見つけたとき

調査、実装、レビュー、検証中に、ローカル Notion の記述とコード、テスト、実行結果、正式な契約が食い違うと判明したら、この skill を使って訂正を提案する。

提案には、対象文書、食い違っている記述、確認できた実際の挙動、根拠、修正文案を含める。
同名フィールドでも処理段階やデータ契約が異なる場合は、どの境界の意味かを分けて説明する。

文書更新が依頼範囲に含まれる場合は、ローカル Markdown を訂正する。
作業中に付随して不一致を見つけた場合は、勝手に書き換えず、訂正案を示してユーザーの確認を得る。

未マージの差分だけが根拠の場合は確定事項として訂正せず、提案中の仕様として分離する。

## 更新時の制約

更新内容に根拠、適用範囲、未解決事項を分けて書く。

トークン、署名付き URL、個人情報、認証情報は残さない。

Notion SaaS や共有ページへの書き込みは行わない。

SaaS へ同期するには、差分と対象ページを示したうえでユーザーの明示許可を得る。

## 完了確認

本文、`.meta.yml`、`_index.md`、関連リンクの対応を確認する。

未確認の断定、リンク切れ、既存文書との矛盾を点検する。

報告では、更新した文書、根拠、Notion 本体へ未同期であることを示す。
