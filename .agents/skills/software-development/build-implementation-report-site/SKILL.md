---
name: build-implementation-report-site
description: 製品コード、設定、APIやDB契約、運用スクリプトを実装または修正したとき、完了前にレビュワー向けの実装ブリーフと検証結果をHTMLで作るために使う。「実装して」「修正して」「回帰テストやローカルE2Eまで」という通常の実装依頼でも必ず使う。「実装レポート」「検証レポート」「コード差分と検証結果を図解して」という依頼でも使う。調査、回答、docsだけの変更、生成物更新だけの作業では使わない。
metadata:
  tags: [implementation-report, site, pull-request, review, visualization]
  related_skills:
    - writing/html
    - software-development/build-experiment-report-site
    - software-development/git-workflow
    - software-development/pr-review-fix-workflow
    - software-development/technical-flow-diagrams
---

# レビュー用実装ブリーフ作成

`writing/html` をHTML作成の共通基盤として使い、実装もPRやissueの会話も知らないレビュワーが5分程度で、変更箇所の全体での役割、何をなぜどのように変えたか、根拠、判断事項を追えるHTMLを作る。
設計書や作業日誌にせず、最初の画面に結論を置き、詳細は必要なときだけ開く。
レポートは実装タスクの完了条件であり、製品リポジトリとPRには含めない。
比較実験の詳細は `software-development/build-experiment-report-site` に分け、このレポートには結論と参照先を置く。

## Skillの階層

- `writing/html` は、静的HTML、共通デザインシステム、目次、図、コード、数式、印刷を扱う表示基盤である。
- このskillは、実装差分をレビューするための情報構成、コード根拠、検証結果、保存先を扱う。
- 内容の順序、証拠、保存先はこのskillを優先し、HTMLの部品と表現は `writing/html` に従う。
- HTMLを作る前に `writing/html/design-system/component-samples.html` を確認し、同梱の `document.css` と必要なアセットを使う。ページ固有のCSSは配置調整に限る。

## 完了条件と保存先

- 実装と必要な検証を終えた後、最終回答の前にレポートを作成または更新する。
- 既定の保存先は `$CODEX_HOME/visualizations/<日付>/<task-id>/<report-name>/index.html` とする。利用できない環境では、製品リポジトリ外の一時ディレクトリを使う。
- レポート、画像、検証用HTMLを製品リポジトリへ置かない。`git add`、commit、push、PR対象にしない。
- 最終回答ではレポートの絶対パスまたはURLを示す。

## 作業手順

1. base SHAと変更後の参照を確認する。変更後が未commitならworking treeとdirty状態、commit済みならSHAを記録し、trackedとuntrackedの差分、設計、実装、テスト、計測成果物を確認する。
2. `git diff --name-status <base>...<after>` 相当の変更一覧と関連するディレクトリ構成を確認する。変更ファイルを責務ごとにまとめ、追加、削除、移動を含む変更箇所と、その箇所が全体で担う役割を把握する。全リポジトリのtreeは作らず、入口、呼び出し先、契約、テストなど変更を理解する近接要素だけを残す。
3. `templates/report-outline.md` でレビュー内容を組み立て、`writing/html` でHTMLへ実装する。変更目的と判断事項、読み始めるための文脈、変更マップ、責務別の変更、検証と未確認事項の順に示す。
4. 読者向けの語を先に使い、内部名は対応付けてから出す。変更領域ごとに、全体での役割、変更前、変更後、目的、変更方法、影響と未変更境界、コードと検証を一つの変更単位へまとめる。各レビュー項目には重要度、状態、理由、根拠を付ける。この変更単位を詳細への唯一の導線とし、同じ要約表を別に作らない。
5. 責務、ガード、契約、状態遷移が変わる重要箇所だけ、baseと変更後の実コードをBefore / Afterで並べる。importや周辺ノイズ、全ファイルの機械的な比較は省く。
6. schema、API、設定、正規化の列挙値が変わるときだけ契約表を置く。複数箇所のガードが一つの保証を作るときだけ、不変条件を一覧化する。
7. 検証はコマンド、ケース別結果、手動確認手順、未確認範囲を短く示す。UIや実環境を含む場合は、各手順の期待結果と起きてはいけない結果を書く。
8. 既存レポートを再構成するときは、現在も有効なコード、契約、検証根拠を棚卸しし、古い結果だけを更新する。必要な根拠を説明文へ圧縮したり無言で落としたりしない。
9. 保証する範囲と保証しない範囲を一致させる。推定、実測、設定値、上限を混同しない。
10. 見出し、順序、余白、ラベル、段階的開示で重要度と情報階層を表す。色だけに意味を持たせない。詳細は必要なものだけを折りたたみ、図は文章とコードより短く責務の関係や処理経路を示せる場合に限る。
11. HTMLを実ブラウザで開き、リンク、ID重複、横溢れ、デスクトップとモバイルの表示を確認する。

## 参照

- 構成を作るときは [templates/report-outline.md](templates/report-outline.md) を使う。
- 初稿前に [references/failure-patterns.md](references/failure-patterns.md) を読む。
- 完了前に [references/review-checklist.md](references/review-checklist.md) で監査する。
