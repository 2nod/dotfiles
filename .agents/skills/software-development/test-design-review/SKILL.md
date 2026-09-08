---
name: test-design-review
description: 既存テストやテスト案の設計をレビューするときに使う。DAMP/DRY のバランス、fixture/helper/factory/beforeEach の切り分け、mock の順序依存、assertion の読みやすさ、public behavior と実装詳細の固定しすぎを点検する。「テスト設計を見て」「fixture が読みにくい」「mock が壊れやすい」「assertion を整理したい」といった依頼で使う。
metadata:
  tags: [testing, review, fixtures, mocks]
  related_skills:
    - engineering/tdd
---

# テスト設計レビュー

テストが何を保証し、失敗をどう診断できるかを確認する。
テスト名とassertionから対象の契約を把握し、必要な改善だけを提案する。
修正依頼なら変更後のテストを実行し、実行結果と未確認を分けて伝える。

## 判断基準

- 期待値の理由になる入力はテスト本体に見せる。期待値は検証対象の実装から計算しない。
- 型を満たす定型値、共通配線、期待値と無関係なshapeはhelperやfactoryに残してよい。重要入力を引数化するか直接記述するかは、実際の依存関係で選ぶ。
- mockの返値は意味のある入力に対応させる。取得順や回数が契約でなければ固定しない。順序自体が契約なら検証を保持する。
- assertionは公開された振る舞いを保証する。正当なhelper、既存の契約、回帰検出能力を保つ。
- 大きなテストは、複数要素の連携を守るcontract testなら残す。失敗原因の切り分けや読解を妨げる場合に分割する。

現状で目的を満たすなら変更不要とする。
重複除去やテスト追加自体を目的にしない。

## 判断が難しいときの資料

setupの切り分け、snapshotの粒度、contract testの扱いで判断がつかない場合は[review-guide.md](references/review-guide.md)の該当箇所を読む。
コメントの表現例が必要なら[comment-examples.md](references/comment-examples.md)を読む。
本文で判断できる作業では追加資料を読む必要はない。
