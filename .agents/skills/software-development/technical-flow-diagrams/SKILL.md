---
name: technical-flow-diagrams
description: 技術解説やレビュー用の図、SVGフロー図、アーキテクチャ図、プロトコル図、データパイプライン図を設計・実装するときに使う。domain stateからSVGへの投影、animateMotionによるデータフロー表現、Reactタイムライン、reduced-motion対応を含む。
---

# Technical Flow Diagrams

説明対象を先にモデル化し、その投影として図を作る。装飾的な動きを追加しない。

## 設計順序

1. 対象をdomain stateとして固定する。登場主体、保持値、遷移条件、入力、出力、終端を書く。
2. 時間が意味を持つ図はtimeline eventへ落とす。開始、待機、移動、分岐、完了、失敗の時刻または条件を決める。
3. view modelへ変換する。座標、path、ラベル、色、実行コストの区別、表示優先度を決める。
4. 最後にinline SVGへ投影する。この順序を逆にしない。

静的図だけで構造を読めることを前提にする。動きは処理方向、同時性、反復、待機を補強する補助である。

## 図の種類

- 実行順序や分岐が主題ならflowchartにする。矢印、分岐条件、合流、早期終了、戻り先を明示する。
- 主体間の依存や境界が主題ならarchitecture diagramにする。データ所有者と呼び出し方向を明示する。
- 時刻や応答順が主題ならprotocol diagramにする。同一メッセージの送信側と受信側を同じ識別子で結ぶ。
- pipeline内の対象が移動すること自体が主題ならdataflow animationにする。静止図で経路と対象を先に読めるようにしてからmotionを付ける。

## SVG motion契約

配線と移動チップは同じgeometry sourceを使う。描画用`<path d>`と`<animateMotion path>`に同じpath文字列を渡す。既存DOMへの`<mpath>`参照ではなく文字列再利用を既定にする。

詳細な実装例と検収項目は [references/svg-motion-patterns.md](references/svg-motion-patterns.md) を読む。

最低限守ること:

- wireの見た目だけを先に作らず、domain上の実際の経路と一致させる。
- 複数段階を順に示す場合は、共通周期内の開始と終了を先に固定する。各段階に共通周期全体の移動時間を与え、beginだけをずらさない。
- 共通周期の属性計算には [scripts/motion_window.py](scripts/motion_window.py) を使える。境界時刻で位置と可視性を検査し、計算値をmotionとopacityへ渡す。
- 待機、加速、減速、到達後の消失を`keyTimes`とeasingで表現する。
- `prefers-reduced-motion: reduce`では移動チップだけを隠し、wire、対象、状態ラベル、終端は残す。
- 動きを止めた状態で、何がどこへ流れるかが説明として成立しているか確認する。

## React timeline

時間付き図をReactで作るときは、図ごとのad hoc animationではなく共通timelineを使う。RAFで時刻を進め、pause、loop、speed、FPS上限を持たせる。`IntersectionObserver`で画面外の図を停止する。

クリックや入力で後続状態が変わる小さなprotocol simulatorは、現在stateからview modelを再計算する。特定時刻をURLへ固定できるようにすると、状態のレビューとvisual testを再現しやすい。

## 検収

- domain state、timeline event、view model、SVGの対応を追跡できる。
- 静止図だけで主要な構造、経路、分岐、終端が読める。
- 動く要素の位置と向きが実際のpathおよび状態遷移と一致する。
- reduced-motionでも説明が失われない。
- 長い図では画面外停止とフレームレート制御がある。
- 説明した時刻と描画結果を照合する。実装を読んだだけの確認と、実ブラウザでの位置、待機、reduced-motionの確認を分け、未実施の検収を完了扱いにしない。
