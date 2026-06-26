# Test Design Review Guide

テスト設計レビューで使う詳細な判断基準。

## Test Case に残すもの

次の値は test case 本体に残す。

- テスト名やシナリオに直接出てくる値
- assertion の出力を決める値
- edge case を成立させる値: null, empty, deleted, merged, locale, permission, status, pagination, sort order, feature flag など
- filter, sort, merge, grouping, validation, error path を左右する値
- 失敗時に読者が最初に見るべき値

例:

```ts
textArea({ id: 'merged', mergeSourceObjectIds: ['source_a', 'source_b'] })
sourceText({ textAreaId: 'source_a', text: 'A' })
sourceText({ textAreaId: 'source_b', text: 'B' })

expect(result.sourceText).toBe('A\nB')
```

この形なら、期待値の理由を helper にジャンプせず読める。

## Factory に逃すもの

次の値は factory に逃してよい。

- 型や schema を満たすだけの値
- 退屈なデフォルト値: timestamp, ID, bbox, metadata, default flag など
- 多くの object literal で繰り返す値
- API / GraphQL response の外枠

良い factory は小さい。
1 object または 1 response shape を作り、意味のある値は override で受け取る。

```ts
const user = (overrides = {}) => ({
  id: 'user_1',
  role: 'viewer',
  deleted: false,
  ...overrides,
})
```

避けたい factory / helper:

```ts
setupComplexHappyPathWithDeletedMergedAndPermissions()
```

これはシナリオ全体を隠し、assertion の理由を test body から追いにくくする。

## beforeEach に逃すもの

次の setup は `beforeEach` に逃してよい。

- mock reset
- dependency / client の作成
- 共通の auth / environment context
- subject を動かすための安定した配線
- assertion の理由にならない共通前提

test ごとに期待値を変える値や edge case を成立させる値は、`beforeEach` に逃さない。

## Helper と Fixture Builder

helper は手順を隠すもの。
fixture builder は、意味のある入力を見せながら退屈なデフォルトを埋めるもの。

読みづらくなりやすい例:

```ts
setupTwoPageHappyPath()
```

読みやすい例:

```ts
setupRevision({
  pages: [page({ index: 0 }), page({ index: 1 })],
  objects: [textArea({ id: 'target', page: 1 })],
})
```

後者は記述量を減らしつつ、期待値の理由になる scenario を test case 側に残せている。

## Mock のレビュー

mock は重要な behavior を固定するために使う。
偶然の実装順序を固定しすぎない。

注意する smell:

- `mockResolvedValueOnce` が長く続いている
- contract ではない相対順を `toHaveBeenNthCalledWith` で固定している
- 独立した request の順番を入れ替えただけで test が落ちる

順序が本質でない場合は、意味のある入力で振り分ける。

```ts
requestMock.mockImplementation((_operation, variables) => {
  if ('id' in variables) return Promise.resolve(buildCoreData())
  if ('keyword' in variables) return Promise.resolve(buildSearchData())
  throw new Error(`unexpected variables: ${JSON.stringify(variables)}`)
})
```

順序自体が contract なら、なぜ順序が重要なのかをテスト名か短いコメントで明示する。

## Assertion のレビュー

- public response shape 全体が contract なら `toEqual` で固定してよい。
- 一部の挙動だけを見たいなら `toMatchObject` / `arrayContaining` で焦点を絞る。
- 原因が setup に隠れた巨大 `toEqual` は避ける。
- snapshot は小さく、人間が差分をレビューできる場合だけ使う。
- 大きな assertion を残す場合、重要な block ごとにどの入力から来るか読めるようにする。

## 前提 / 操作 / 期待

長い test や setup が重い test では、Arrange / Act / Assert を明示すると読みやすい。

- `// 前提`: 入力 fixture、mock response、環境条件を書く
- `// 操作`: subject の実行だけを書く
- `// 期待`: assertion を書く

短い test では無理にコメントを入れない。
コメントは「何をしているか」ではなく、なぜこの値が期待値になるか、またはどの contract を固定しているかを補うために使う。

良いコメント:

```ts
// deleted:true のため出力されない
deletedUser: user({ id: 'deleted_user', deleted: true })
```

不要なコメント:

```ts
// user を作る
const activeUser = user({ id: 'active_user' })
```

## 分割するか、まとめるか

分割した方がよい場合:

- 複数の独立 behavior が別々の理由で壊れ得る
- failure message だけでは壊れた挙動が分からない
- fixture が巨大な隠し scenario になっている
- 1 つの edge case を足すと無関係な assertion が壊れる

まとめてもよい場合:

- 代表的な public contract test として response shape を固定したい
- caller にとって組み合わさった shape 自体が重要
- 個別 branch は別の小さい test で検証済み
- integration としての価値が setup の大きさを上回る

大きい test を残す場合は、テスト名やコメントで contract / integration test としての意図を出す。
