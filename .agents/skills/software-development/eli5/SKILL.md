---
name: eli5
description: 複雑なシステムを、大きな図と少ない言葉で段階的に読めるHTMLページとして説明するときに使う。ユーザーが「eli5」「仕組みを図解して」「このシステムを知らない人向けに説明して」「全体像が分かるページを作って」と依頼したときに発火する。差分ではなく、動いているシステムそのものを対象にする。
metadata:
  tags: [explanation, visualization, html, onboarding, codebase]
  related_skills:
    - software-development/build-implementation-report-site
---

# ELI5

そのコードベースを知らない人が、全体の流れを一度で掴めるページを作る。
やさしく言い換えるのではなく、図に説明を担わせて言葉を削る。

## 対象の切り分け

変更（PRや実装差分）の説明は `software-development/build-implementation-report-site` を使う。
この skill が扱うのは、今動いているシステムの仕組みである。

## 作業手順

1. entry point から runtime flow を実際に追う。読んでいない箇所を推測で埋めない。
2. 確認した事実と推論を分ける。推論はページ上でも推論として示す。
3. `references/investigation-checklist.md` で、省略しやすい層を潰す。
4. `templates/eli5-outline.md` に沿い、全体を1周させてから各段を詳細化する。
5. 比喩は導入だけに使い、同じ段に実装上の識別子を併記する。
6. 1つの図には1つの主張だけ載せる。言葉は図で足りない分だけ書く。
7. 広い画面と狭い画面の両方で表示を確認する。

## 表現の基準

- 比喩は理解の入口であって置き換えではない。path、endpoint、関数名など実装への戻り先を必ず添える。
- 1つの図に複数の抽象度を混ぜない。
- 正常系だけの図は未完成とみなす。失敗と権限は別の段に置く。
- 図中の番号は実装上の識別子か本文の参照順に限る。説明の都合で架空の段階番号を作らない。
- 色は意味の区別にだけ使う。流れは矢印と余白で示す。

## 成果物

HTMLは自己完結させ、外部CDNやリモート資産に依存させない。
Artifactとして公開できる agent ではArtifactにする。できない場合はHTMLファイルとして出力する。
