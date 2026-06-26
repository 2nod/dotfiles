# Test Design Review Comment Examples

テスト設計レビューで、そのまま使うか短く直して使うコメント例。

## 期待値の理由が隠れている

```md
[imo] この期待値を決めている入力が helper の中に隠れていて、test body から理由を追いにくいです。

`<期待値>` は `<入力A>` と `<入力B>` で決まるので、その値だけでも test case 側に出し、型を満たすだけの値は factory に残すと読みやすくなりそうです。
```

## Helper が広すぎる

```md
[nits] この helper は scenario 全体を作っていて、この test では使わない fixture まで共有しているように見えます。

この test で必要な `<条件>` だけを fixture builder の引数として出し、残りは default factory に逃すと DAMP 寄りになりそうです。
```

## Mock が順序依存

```md
[want] この mock は `mockResolvedValueOnce` の順序に依存していますが、この相対順は今回の behavior ではなさそうに見えます。

variables や operation name で振り分けると、実装順序への結合が弱くなりそうです。
```

## 大きい Contract Test として許容

```md
[memo] この test は複数 behavior を見ていますが、public response の代表 contract を固定する目的なら 1 test として残してよさそうです。
新しい edge case が増える場合は、その条件だけ小さい test に切り出すのがよさそうです。
```
