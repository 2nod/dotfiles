---
name: git-worktree-cleanup
description: Git worktree と branch の残骸を監査し、実装完了後の docs/plans とローカル Notion も確認して安全に片付ける。ユーザーが worktree の削除、stale 登録の整理、容量確保、または実装作業の後片付けを依頼したときに使う。
metadata:
  tags: [git, worktree, cleanup, documentation]
  related_skills:
    - software-development/git-workflow
    - knowledge-management/notion-workspace-maintenance
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
3. primary ではない worktree について、`docs/plans` と未追跡文書も確認する。
   完了済み plan に固有の知識が残る場合は、削除前に正本への昇格またはローカル Notion の訂正が必要である。
4. worktree を分類する。
   - **stale metadata**：`git worktree prune --dry-run --verbose` が prunable と報告する登録。もっとも安全に片付けられる。
   - **かなり消してよさそう**：clean で、`main` または `origin/main` に対する独自 commit がなく、branch が merge 済み、upstream gone、または別 worktree と重複している。
   - **差分を捨てるなら消せる**：package manager の一時 metadata、scratch docs など、軽微または使い捨てだと判断できる local diff だけがある。
   - **今は残す**：source/test の未 commit 変更、ahead commit、多数の独自 commit、不明な upstream/base 関係がある。
   - 公開済み Site のローカル原本だけが ignored / untracked artifact として残っている場合、ユーザーから保存方針の明示がなくても「差分を捨てるなら消せる」削除候補にする。
     Site が worktree から独立して公開済みであることを確認し、削除候補の報告ではローカル原本と再編集可能性が失われることを伝える。実際の削除には手順5の明示確認が必要である。
     この例外は未 push commit、通常の source/test、`docs/plans`、または Site 以外の未保存成果物には適用しない。
5. 既存 worktree を消す前、または local change を捨てる前に、必ずユーザーの明示確認を取る。
6. clean な worktree は `git -C <primary-repo> worktree remove <path>` で消す。
   `--force` は、捨てる差分を列挙し、ユーザーが同意した場合だけ使う。
7. worktree を削除した後で、local branch と remote branch を別々に分類する。
   - local branch は、全 commit が `origin/main`、対応する remote branch、または保持する tag のいずれかから到達可能なら、merge 状態にかかわらず原則として削除候補にする。
   - remote branch は、active PR がなく、全 commit が `origin/main` または保持する tag から到達可能で、merge 済みまたは役目を終えた一時・検証用 branch なら削除候補にする。
   - 保存先のない commit、active PR、用途が不明な branch は残す。
   local branch と remote branch の実際の削除は別操作として示し、それぞれ明示許可を得てから行う。
8. 削除後は `git worktree list --porcelain`、`git worktree prune --dry-run --verbose`、branch、path の存在確認で取りこぼしを確認する。

## 実装完了時の確認

- `docs/plans` の追跡済み、未追跡ファイルを列挙する。
- plan の確定事項が `docs/design`、`docs/adr`、実装近傍の文書へ移っているか確認する。
- ローカル Notion と現行実装に不一致がないか確認し、必要なら `notion-workspace-maintenance` を使う。
- 追跡済み plan の削除 commit、未追跡 plan の破棄、Notion SaaS 同期を同じ許可として扱わない。
- PR の merge、base branch への包含、upstream、独自 commit を確認してから worktree と branch を削除する。

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
