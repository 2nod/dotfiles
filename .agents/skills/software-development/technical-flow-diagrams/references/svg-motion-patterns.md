# SVG Motion Patterns

## Geometry Source

1本の経路を定数として持ち、wireとchip motionの両方へ渡す。これにより線形変更や曲率調整時にmotionが外れない。

```tsx
const SYNC_PATH = "M 24 96 C 120 32 216 160 312 96";

function DataFlowChip({ index }: { index: number }) {
  const delay = `${index * 0.44}s`;

  return (
    <circle className="flow-chip" r="6" opacity={0}>
      <animateMotion
        dur="11s"
        begin={delay}
        repeatCount="indefinite"
        path={SYNC_PATH}
        keyPoints="0; 0; 1"
        keyTimes="0; 0.22; 1"
        calcMode="spline"
        keySplines="0 0 1 1; 0.4 0 0.6 1"
      />
      <animate
        attributeName="opacity"
        values="0; 1; 1; 0"
        keyTimes="0; 0.02; 0.92; 1"
        dur="11s"
        begin={delay}
        repeatCount="indefinite"
      />
    </circle>
  );
}

<path className="wire" d={SYNC_PATH} fill="none" />;
```

`keyPoints`は距離上の出発点、待機点、到達点を表す。`keyTimes`は時間比であり、両方の要素数を一致させる。待機と移動の比率は説明したい処理の実際の間隔に合わせる。

## Stagger

- chip数が多い場合はintervalを固定し、開始をずらす。
- intervalが短すぎると個別の処理が読めない。最初は0.35〜0.7秒程度で試す。
- 全体周期は「待機 + 移動 + 到達後の余韻」を1セットとして決める。

## Reduced Motion

移動対象だけを非表示にし、wireと静的情報は残す。

```css
@media (prefers-reduced-motion: reduce) {
  .flow-chip {
    display: none;
  }
}
```

必要なら、開始地点、終端、累積件数、処理方向の矢印など、静止情報を追加して意味を保つ。

## React Timeline Shape

図ごとのDOM操作を作らず、共通timelineからview modelを作る。

```ts
type DomainState = {
  phase: "idle" | "uploading" | "committing" | "done";
};

type TimelineEvent = {
  at: number;
  kind: "start" | "chunk" | "ack" | "finish";
};

type ViewModel = {
  activeEdgeId: string | null;
  visibleChipIds: string[];
  label: string;
};

function project(state: DomainState, timeMs: number): ViewModel {
  // stateとeventsから、その時刻に表示されるedge、chip、labelだけを返す。
}
```

RAF loopは次を持つ:

- `speed`: 0.25x、1x、2xなどの再生速度
- `fpsCap`: 例えば30fps
- `paused`: ユーザー操作と画面外停止で真になる
- `loop`: 繰り返し境界の規則
- `timeSource`: URL時刻、テスト用固定時刻、RAF経過時刻

URLには正規化した時刻だけを持ち、復元時は`project(initialState, fixedTime)`から再構築する。ランダムなDOM状態やローカル変数へ依存しない。

## Review Gates

- `<path d>`とすべての`<animateMotion path>`が同じsourceから生成されているか。
- stagger中もchipの進行方向とwire方向が一致しているか。
- opacityの開始と終了がmotionの待機と到達に同期しているか。
- reduced-motionで消しているのがchip群だけか。
- 画面外でRAFが止まるか。
- 固定時刻で同じview modelとスクリーンショットになるか。

## Sources

- [Linear rebuilding delta sync read path](https://linear.app/now/rebuilding-delta-sync-read-path)
- [MDN `<animateMotion>`](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/animateMotion)
- [Cursor git at any scale](https://cursor.com/ja/blog/git-at-any-scale)
