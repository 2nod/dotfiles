---
name: local-docker-troubleshooting
description: macOSのローカルDocker Compose、ホストとコンテナを混在させたE2E、Playwright検証が失敗したときに使う。実行場所、接続先、生成物、認証、依存volume、保存領域、browser runtimeを順に切り分け、既存環境を壊さず最小検証を復旧する。
metadata:
  tags: [docker, compose, macos, playwright, chromium, disk]
  related_skills:
    - engineering/diagnosing-bugs
---

# Local Docker troubleshooting

Docker Composeの失敗は、アプリケーションの不具合、依存関係の破損、保存領域不足、browser runtimeの失敗を分けて扱う。

標準Composeが動かないことを、CPUアーキテクチャの問題と決めない。

まず既存のCompose fileとplatformのまま、対象serviceの最小commandを一度実行する。

失敗時は、次の順で原因を確認する。

1. 各processをhostとcontainerのどちらで動かすかを決め、接続先、生成物、認証、mountを一覧にする。
2. `docker version`、`docker compose config`、`docker system df`で、daemon、実効設定、空き容量を確認する。
3. hostの`node_modules`が壊れたsymlinkでないかを確認する。既存symlinkや他のworktreeを削除しない。
4. Yarnの`EEXIST`は、専用の一時Compose projectとvolumeだけで再現する。対象volumeがそのprojectのlabelを持つことを確認してから掃除する。
5. Playwrightだけが落ちる場合は、browser version、依存library、platformを記録する。標準環境でQEMU由来のSIGSEGVなどを再現した場合だけ、一時arm64 overrideを診断用に使う。

標準Composeで実行できる場合は、一部のprocessだけをhostで起動しない。

hostとcontainerを混在させる場合は、processごとの実行場所、URL、port、認証、mountを起動前に整理する。

標準サポートしない経路を、一回の検証のために恒久実装しない。

**検証に必要な観測値がartifactにない**ことだけでは、production API契約の変更理由にならない。

既存のlog、response、入力データで必要な結論が得られるなら、それを使う。

一時的に計測を加える場合も、production API契約へ残さず、検証後に戻す。

Compose cleanupでは、既存環境と同じproject名で`down`しない。

必ず固有の`-p <temporary-project>`を使い、削除前にcontainer、image、volumeがそのprojectに属することを確認する。

`docker system prune`、`docker volume prune --all`、他者の停止containerの削除は使わない。

Apple Silicon、Chromium、volumeの詳細な確認手順は[references/apple-silicon-chromium.md](references/apple-silicon-chromium.md)を参照する。
