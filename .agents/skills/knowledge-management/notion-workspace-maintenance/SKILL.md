---
name: notion-workspace-maintenance
description: "コード、テスト、実行ログ、正式な契約で確定した知見をもとに、~/Documents/Notion のローカル Markdown、メタデータ、索引を新規作成または訂正するときに使う。ユーザーが「知見を残して」「既存 Notion メモを直して」「Notion を腐らせないよう更新して」と依頼した場合にも使う。"
metadata:
  tags: [notion, knowledge, documentation, maintenance]
  related_skills:
    - knowledge-management/notion-workspace-context
    - writing/japanese-tech-writing
---

# ローカル Notion 文書の保守

`~/Documents/Notion/AGENTS.md` と対象文書を読み、更新対象と同期制約を確認する。

## 更新の判断

コード、テスト、実環境の結果で確認でき、今後の調査、実装、運用で再利用できる事実だけを更新する。

実験の一回限りの値は、観測日と条件を添え、恒久仕様として書かない。

未マージ、レビュー中、未合意、再現確認前の内容は、確定文書へ混ぜない。

同じ主題の文書があれば、先にその文書を訂正または補足する。

独立して参照する検証、決定、運用記録は、`personal-workspace-memo/<Tag>/` に本文と `.meta.yml` の組で作り、`_index.md` を更新する。

## 更新時の制約

更新内容に根拠、適用範囲、未解決事項を分けて書く。

トークン、署名付き URL、個人情報、認証情報は残さない。

Notion SaaS や共有ページへの書き込みは行わない。

SaaS へ同期するには、差分と対象ページを示したうえでユーザーの明示許可を得る。

## 完了確認

本文、`.meta.yml`、`_index.md`、関連リンクの対応を確認する。

未確認の断定、リンク切れ、既存文書との矛盾を点検する。

報告では、更新した文書、根拠、Notion 本体へ未同期であることを示す。
