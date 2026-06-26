---
name: test-design-review
description: 既存テストやテスト案の設計をレビューするときに使う。DAMP/DRY のバランス、fixture/helper/factory/beforeEach の切り分け、mock の順序依存、assertion の読みやすさ、public behavior と実装詳細の固定しすぎを点検する。「テスト設計を見て」「fixture が読みにくい」「mock が壊れやすい」「assertion を整理したい」といった依頼で使う。
metadata:
  tags: [testing, review, fixtures, mocks]
  related_skills:
    - engineering/tdd
---

# テスト設計レビュー

テストは実行できる仕様書でもある。読みやすさと失敗時の診断しやすさが重要な場面では、厳密な DRY より DAMP (Descriptive And Meaningful Phrases) を優先する。

中心ルール: **期待値の理由になる値は test case 本体に見せる。** 型を満たすだけの退屈な値、共通の配線、期待値に関係しない shape は factory / helper / `beforeEach` に逃してよい。

## 手順

1. テスト名を読む。
2. setup より先に assertion を読み、何を保証しているか把握する。
3. assertion を成立させる入力値を特定する。
4. その入力値が test case 本体に見えているか確認する。
5. 隠れている setup を、test case に戻すべきか、小さい factory に残すべきか、`beforeEach` に逃してよいか分類する。
6. mock が本質ではない呼び出し順に依存していないか確認する。
7. 大きい test が代表的な contract test として妥当か、分割すべきか判断する。

## 詳細な点検項目

次の判断基準が必要なときは [references/review-guide.md](references/review-guide.md) を読む。

- test case に残す値と factory に逃す値
- `beforeEach` に置いてよい setup
- helper と fixture builder の切り分け
- mock の順序依存
- assertion と snapshot の粒度
- 大きい test を分割するか、contract test として残すか

## レビューコメント例

具体的なコメント文を作るときは [references/comment-examples.md](references/comment-examples.md) を読む。

## 最終チェック

- テスト名から守りたい behavior が分かるか
- 重要な期待値の理由を test body から説明できるか
- factory は退屈なデフォルトだけを隠しているか
- `beforeEach` は共通配線に留まっているか
- mock は本質的な behavior だけに結合しているか
- 大きい test は contract / integration test として意図的に大きいか
