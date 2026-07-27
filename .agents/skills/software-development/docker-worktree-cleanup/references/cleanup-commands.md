# Docker と worktree の容量整理コマンド

## 調査

Docker の容量は、まず分類別に確認する。

```sh
docker system df
docker system df -v
docker ps --all --size
```

Compose の project と元の working directory は、コンテナ label から確認する。

```sh
ids=$(docker ps -aq)
[ -z "$ids" ] || docker inspect --format '{{.Name}}\t{{index .Config.Labels "com.docker.compose.project"}}\t{{index .Config.Labels "com.docker.compose.project.working_dir"}}' $ids
```

worktree が残っている場合は、primary repository から監査する。

```sh
git worktree list --porcelain
git worktree prune --dry-run --verbose
```

## 段階的な削除

実体が消えた Compose project は、まず削除予定を列挙する。

```sh
docker ps --all --filter "label=com.docker.compose.project=<project>"
docker volume ls --filter "name=^<project>_"
```

停止済みで、working directory が存在せず、named volume のデータも不要と確認できた project だけを削除する。

```sh
ids=$(docker ps -aq --filter "label=com.docker.compose.project=<project>")
[ -z "$ids" ] || docker rm $ids

volumes=$(docker volume ls -q --filter "name=^<project>_")
[ -z "$volumes" ] || docker volume rm $volumes
```

未使用イメージとビルドキャッシュは、Docker の参照状態に従って削除できる。

```sh
docker image prune --all --force
docker builder prune --force
```

停止コンテナを一括削除する場合は、named volume が残ることと、対象の開発環境を Compose で再作成することを承認前に説明する。

```sh
docker container prune --force
```

匿名 volume だけを削除するには `--all` を付けない。

```sh
docker volume prune --force
```

`docker volume prune --all` は、停止コンテナを消した後の DB・MinIO・依存キャッシュを含む named volume まで削除するため、使わない。

実体のない Git worktree 登録だけは、別途削除できる。

```sh
git worktree prune --dry-run --verbose
git worktree prune --verbose
```

## 確認

```sh
docker system df
docker ps --all
git worktree prune --dry-run --verbose
```

named volume を削除した project は、次回 `docker compose up` や project 固有の起動コマンドで DB・依存キャッシュを作り直す。
