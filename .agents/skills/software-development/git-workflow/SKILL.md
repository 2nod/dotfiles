---
name: git-workflow
description: リポジトリの役割を判定して、branch、stage、commit、push、PR を安全に進める手順。ユーザーが Git の状態確認、branch 作成、差分の stage、commit、push、PR、または site の公開を依頼したときに使う。
---

# Git 運用

最初に repository の役割と current branch を確認する。
既存の未コミット変更はユーザーのものとして扱い、依頼と無関係な変更を stage、修正、破棄しない。

## repository の分類

- **通常の製品 repository**：feature、fix、docs などの作業 branch を使う。
  `main` と `master` へ直接 push しない。
  ユーザーが明示した場合だけ例外を検討する。
- **専用 site source repository**：`.openai/hosting.json` を持ち、限定公開 site の配布元として使う repository は `main` を公開元にできる。
  この場合は feature branch や PR を必須にしない。
  `main` へ送る前には、その site source repository に直接 push することをユーザーに明示して確認する。
- どちらか不明な場合は、remote、hosting 設定、project instructions を読み、判断できなければ確認する。

## 変更の手順

1. `git status --short --branch` と必要な範囲の diff を確認する。
2. 実装依頼がない限り、状態を報告するだけに留める。
3. stage は対象ファイルを明示して行う。
   `git add .` は、対象が明確で未追跡ファイルを含める必要がある場合だけ使う。
4. commit 前に、対象、内容、検証結果を短く示して明示許可を得る。
5. push 前にも、送信先 branch と外部共有の意味を示して明示許可を得る。
   専用 site source repository では、承認済みなら `HEAD:main` を公開元へ送る。
6. push 後は branch と remote の状態を確認する。
   site はビルド済みの commit と同じ source を配布し、限定公開を優先する。

## 安全策

- `reset --hard`、`clean`、force push、branch delete、stash drop は、捨てる対象を列挙してから個別に確認する。
- pre-push hook が専用 site source repository の `main` 送信だけを妨げる場合、`--no-verify` はその repository と承認済みの push に限る。
- 通常の製品 repository で hook、CI、レビューを迂回しない。
- 作業完了時は、branch、stage、commit、push の実施状況と、残した変更だけを簡潔に伝える。
