---
name: local-docker-troubleshooting
description: macOSのローカルDocker ComposeやPlaywright検証が失敗したときに使う。Compose設定、依存volume、保存領域、browser runtimeを順に切り分け、既存環境を壊さず最小検証を復旧する。
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

1. `docker version`、`docker compose config`、`docker system df`で、daemon、実効設定、空き容量を確認する。
2. hostの`node_modules`が壊れたsymlinkでないかを確認する。既存symlinkや他のworktreeを削除しない。
3. Yarnの`EEXIST`は、専用の一時Compose projectとvolumeだけで再現する。対象volumeがそのprojectのlabelを持つことを確認してから掃除する。
4. Playwrightだけが落ちる場合は、browser version、依存library、platformを記録する。標準環境でQEMU由来のSIGSEGVなどを再現した場合だけ、一時arm64 overrideを診断用に使う。

**改行や描画の観測値がartifactにない**ことは、Capture APIの変更理由にはならない。

既存のline bbox、overflow、入力文字列で必要な結論が得られるなら、それを使う。

一時的に計測を加える場合も、production API契約へ残さず、検証後に戻す。

Compose cleanupでは、既存環境と同じproject名で`down`しない。

必ず固有の`-p <temporary-project>`を使い、削除前にcontainer、image、volumeがそのprojectに属することを確認する。

`docker system prune`、`docker volume prune --all`、他者の停止containerの削除は使わない。

詳細な確認コマンド、失敗別の復旧、artifactへ残す情報は[references/apple-silicon-chromium.md](references/apple-silicon-chromium.md)を参照する。
