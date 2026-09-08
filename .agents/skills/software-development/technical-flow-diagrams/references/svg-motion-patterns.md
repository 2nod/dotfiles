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

## 共通周期内の移動区間

同じ対象が複数の経路を順に通る場合は、周期Tと各経路の開始s、終了eを秒単位で決める。
単独の経路にだけ使うstaggerと区別する。
`0 <= s < e <= T`を満たし、前段の到着から後段の出発までを待機として表す。

```sh
python3 scripts/motion_window.py 6 0 2.16
python3 scripts/motion_window.py 6 3.48 5.64
```

このscriptはJSONのmotion属性とopacity属性を返す。どちらもbegin=0s、dur=6sで共通の時計を使い、移動区間だけをkeyTimesに投影する。
第一経路は0秒から2.16秒まで移動し、第二経路は3.48秒から5.64秒まで移動する。2.16秒から3.48秒はqueueでの待機であり、移動チップとは別の静止ラベルや保持状態で示す。

属性をそれぞれ`animateMotion`とopacityの`animate`へ渡す。pathは既存の共有geometryから与え、beginやdurだけを後から別々に上書きしない。
scriptは線形移動と段階的な可視性を扱う。easingや余韻が必要な場合は用途に合わせて拡張し、時刻の契約を再検査する。

数値検査は時刻の対応だけを保証する。実ブラウザではs直前、区間の中間、e直後、次段開始、周期境界で位置と可視性を確認する。
reduced-motionではチップ以外の線とラベルが残ることも確認する。

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
