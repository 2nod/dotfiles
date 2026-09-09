---
name: build-implementation-report-site
description: ユーザーがHTMLまたはSite形式の実装レポート・検証レポートを明示的に依頼したときに使う。コードの変更理由、責務、処理フロー、検証結果をレビュワー向けにまとめる。通常の実装・修正・テスト依頼だけでは使わない。
metadata:
  tags: [implementation-report, site, pull-request, review, visualization]
  related_skills:
    - writing/html
    - writing/show-me
    - software-development/build-experiment-report-site
    - software-development/git-workflow
    - software-development/pr-review-fix-workflow
    - software-development/technical-flow-diagrams
---

# レビュー用実装ブリーフ作成

`writing/html`を表示基盤として、変更を知らないレビュワーが5分程度で、変更の役割、理由、実装、根拠、判断事項を追えるHTMLを作る。
設計書や作業日誌にはせず、最初の画面に結論を置く。
比較実験の詳細は`software-development/build-experiment-report-site`へ分ける。

## 作成要否

- ユーザーがHTMLまたはSite形式の実装・検証レポートを明示的に依頼したときだけ作成・更新する。
- 「実装して」「修正して」「テストして」「PRにして」「実装が完了した」といった依頼や、作業結果の報告だけでは、レポート依頼とはみなさない。
- レポートを作るか迷う場合は作成せず、変更内容・検証結果・未検証事項をチャットで簡潔に伝える。
- 通常の実装、修正、回帰テスト、E2Eの依頼だけでは、このskillを使わない。
- レポートの依頼がなくても必要な検証は行い、変更内容・結果・未検証事項をチャットで簡潔に伝える。

## Skillの階層

- 内容、証拠、保存先はこのskill、HTML部品は`writing/html`に従う。
- 作成前に`writing/html/design-system/component-samples.html`を確認し、共有CSSと必要なアセットを使う。
- ページ固有CSSは配置調整に限る。
- 変更マップとコードの変化を示すときは`writing/show-me`を併用する。複数ファイルの変更マップは、変更対象だけを実際の階層で並べた浅いディレクトリツリーにし、役割と追加／変更／削除を添える。平らな表や役割別の折りたたみ一覧でツリーを代替しない。単一ファイルの局所変更では省略できる。
- ディレクトリ再編がない場合は変更対象のツリー、再編がある場合は構成のBefore / Afterを示す。コードや呼び出し順の説明用スケッチは実コード差分と明記して区別し、実コードの根拠を置き換えない。

## 完了条件と保存先

- 以下の完了条件と作業手順は、HTMLまたはSite形式のレポートを明示的に依頼された場合だけ適用する。他のskillからの参照や実装・PR・マージの完了を作成の契機にしない。
- 依頼されたレポートは、実装と必要な検証後、最終回答の前に作成または更新する。
- 既定は`$CODEX_HOME/visualizations/<日付>/<task-id>/<report-name>/index.html`へ保存する。
- レポートと画像は製品リポジトリ、stage、commit、push、PRへ含めない。
- 最終回答ではレポートの絶対パスまたはURLを示す。

## 作業手順

1. base SHA、afterのSHAまたはdirty working tree、trackedとuntrackedの差分、設計、テスト、計測成果物を確認する。
2. 変更ファイルを責務へまとめ、入口、呼び出し先、契約、テストだけの変更マップを作る。
3. `templates/report-outline.md`で、概要、文脈、変更マップ、責務別変更、検証の順に組み立てる。
4. 各変更単位を`入力 → 判定・防御 → 出力 → Before / After → テスト証拠`に統一する。実装、自動テスト、ローカルE2E、未確認を分ける。
5. 重要な責務、ガード、契約、状態遷移だけを実コードBefore / Afterで示す。横断的な保証は概要の少数の不変条件からコードとテストへつなぐ。
6. 目的と共通の操作は変更単位に一度、検証意図、前提、期待結果はテストケースごとに示し、実ファイルpathへつなぐ。検証意図には、そのケースが防ぐ事故または固定する契約を書く。テストが直接保証する範囲を越えてUIや運用の成立を断定しない。
7. 複数の変更単位には、役割、検証状態、anchorを持つ右サイドナビを置く。用語集は本文の文脈内で折りたたむ。
8. 既存レポートの再構成では有効な根拠を落とさず、古い結果だけを更新する。
9. 実ブラウザでリンク、ID重複、横溢れ、デスクトップとモバイルを確認する。

## 参照

- 構成は[templates/report-outline.md](templates/report-outline.md)を使う。
- 初稿前に[references/failure-patterns.md](references/failure-patterns.md)を読む。
- 完了前に[references/review-checklist.md](references/review-checklist.md)で監査する。
