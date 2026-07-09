---
name: git-worktree-cleanup
description: Git worktree の残骸を監査し、安全に片付けるための手順。ユーザーが「無駄な worktree が残っていないか」「stale な worktree を消したい」「削除候補を分類して」「容量を空けたい」「定期的に worktree を点検したい」と依頼したときに使う。
---

# Git Worktree の整理

この skill は、Git worktree を削除する前に状態を点検するために使う。
まず根拠を集める。
登録済み worktree、stale/prunable な登録、clean/dirty、upstream、`main` との差分、最後の commit、サイズ、更新時刻を確認する。

## 手順

1. ユーザーが指定した root 配下の Git repository を探す。
   指定がなければ、現在の workspace、`~/Documents`、`~/work` などの開発用 root を見る。
   home directory 全体のような広すぎる探索は、権限エラーが多いので避ける。
2. 可能なら `scripts/audit-worktrees.sh <root>...` を実行する。
   この script は読み取り専用で、worktree を削除しない。
3. primary ではない worktree を分類する。
   - **stale metadata**：`git worktree prune --dry-run --verbose` が prunable と報告する登録。もっとも安全に片付けられる。
   - **かなり消してよさそう**：clean で、`main` または `origin/main` に対する独自 commit がなく、branch が merge 済み、upstream gone、または別 worktree と重複している。
   - **差分を捨てるなら消せる**：package manager の一時 metadata、scratch docs など、軽微または使い捨てだと判断できる local diff だけがある。
   - **今は残す**：source/test の未 commit 変更、ahead commit、多数の独自 commit、不明な upstream/base 関係がある。
4. 既存 worktree を消す前、または local change を捨てる前に、必ずユーザーの明示確認を取る。
5. clean な worktree は `git -C <primary-repo> worktree remove <path>` で消す。
   `--force` は、捨てる差分を列挙し、ユーザーが同意した場合だけ使う。
6. 削除後は `git worktree list --porcelain`、`git worktree prune --dry-run --verbose`、path の存在確認で取りこぼしを確認する。

## 報告

報告は判断に必要な情報だけに絞る。

- stale metadata がある場合は、最初に exact path と理由を出す。
- 削除候補は「安全に片付けられる」「差分破棄が必要」「残す」に分ける。
- path、branch/upstream、dirty summary、unique/ahead/behind、サイズ、最後の commit 日を含める。
- dirty worktree を捨ててよいか判断する場面を除き、長い diff は出さない。

## ガードレール

- この workflow では `git reset --hard`、`rm -rf`、`git clean` を使わない。
- ユーザーが別途依頼しない限り、push、commit、branch delete はしない。
- dotfiles や repository worktree にある無関係なユーザー変更は触らない。
