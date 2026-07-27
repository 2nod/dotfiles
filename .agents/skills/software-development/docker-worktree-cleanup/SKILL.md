---
name: docker-worktree-cleanup
description: Docker の仮想ディスクや local volume が肥大化したとき、worktree と Docker Compose 環境を対応付けて、安全な削除候補を調査・整理する。古い worktree、停止コンテナ、未使用イメージ、named volume を片付けたいときに使う。
metadata:
  tags: [docker, compose, worktree, disk-cleanup]
  related_skills:
    - software-development/git-worktree-cleanup
    - software-development/local-docker-troubleshooting
---

# Docker と worktree の容量整理

Docker の容量整理では、コンテナ、イメージ、ビルドキャッシュ、volume を別々に扱う。
Docker の「reclaimable」は、再作成できることを示すだけで、データを捨ててよいことを示さない。

まず `docker system df` で分類別の容量を確認する。
Compose コンテナには project と working directory の label があるため、reference のコマンドで worktree と対応付ける。

Git worktree の実体、未コミット差分、独自コミット、stale metadata は `git-worktree-cleanup` で監査する。

## 削除候補の分類

- **安全に片付けられる**：実体のない worktree の Git 登録、working directory が存在しない停止 Compose プロジェクト、未使用イメージ、未使用ビルドキャッシュ、匿名 volume。
- **明示承認後に片付ける**：停止コンテナ、working directory が残るプロジェクト、named volume。
- **残す**：稼働中コンテナ、未コミット変更または未マージの worktree、用途が確認できない DB・MinIO などの named volume。

削除前に、対象、データの種類、再作成方法、想定回収量を示してユーザーの承認を得る。
停止コンテナの削除は named volume を消さないが、再開時には Compose で作り直す必要がある。

named volume は project ごとに明示指定して削除する。
`docker volume prune --all`、`docker system prune --volumes`、プロジェクト名や保管データを確認しない一括削除は使わない。

削除後は `docker system df`、`docker ps --all`、`git worktree prune --dry-run --verbose` で確認する。
Colima や Docker Desktop の仮想ディスクは sparse file のため、Docker の論理使用量ほど host の空き容量が直ちに増えるとは限らない。

詳細な確認コマンドと削除順序は [references/cleanup-commands.md](references/cleanup-commands.md) を読む。
