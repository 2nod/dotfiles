# Knowledge repositoryのGit境界

ローカル Notionなどのknowledge baseが独立したGit repositoryなら、製品repositoryとは別の変更対象として扱う。
製品repositoryで得たstage、commit、pushの承認をknowledge repositoryへ引き継がない。

最初にknowledge repositoryの`AGENTS.md`、current branch、remote、既存変更を確認する。
repository固有の指示がこのreferenceと異なる場合は、repository固有の指示を優先する。

## 操作の境界

| 操作 | 基本方針 |
| --- | --- |
| 既存メモの参照と一次情報との照合 | 依頼に必要なら行う |
| 本文、`.meta.yml`、索引の更新 | 依頼範囲なら行う |
| `git diff --check`と文書間の整合確認 | 更新後に行う |
| stage | commit準備を依頼された場合だけ、対象pathを限定して行う |
| local commit | 差分と対象を示し、明示承認を得てから行う |
| branchとworktree | 並行作業、長期作業、大規模な再編、個別レビューで分離が必要な場合だけ作る |
| pushとPR | repositoryが許可し、個別の承認がある場合だけ行う |
| Notion SaaS同期 | local commitとは別の変更として明示承認を得る |

local-onlyでremoteを持たないrepositoryは、repository固有の指示が許可していれば、小規模な更新をcurrent branchへ直接commitしてよい。
この場合もcommit前の承認は省略しない。

dirtyなworktreeでbranchを切り替えても、未commit変更は新しいbranchへ引き継がれる。
別作業を分離する必要がある場合は、既存作業を先に完了するか、cleanな基点からtask branchと別worktreeを作る。

## Commit単位

本文、対応する`.meta.yml`、索引は一つの論理単位として扱う。
新規作成と削除では、三点を同じcommit候補に含める。
既存文書の更新でも、metadataや索引の日付、status、linkが変わる場合は同じcommit候補に含める。

## 既存変更がある場合

- 別ファイルの変更は、今回のpathだけをcommit候補にする。
- 同じファイルに既存変更がある場合は、勝手に同じcommitへ含めない。
- 部分stageが必要なら、含めるhunkを提示して承認を得る。
- 安全に分離できなければ、変更を未commitのまま残して報告する。

## 完了条件

commitの有無ではなく、次の状態で完了を判断する。

1. 保存基準を満たす知識だけが残っている。
2. 本文、metadata、索引が整合している。
3. 無関係な既存変更を巻き込んでいない。
4. 今回の差分を既存変更から識別できる。
5. commitとNotion SaaS同期が、それぞれ未実施または個別に承認済みである。
