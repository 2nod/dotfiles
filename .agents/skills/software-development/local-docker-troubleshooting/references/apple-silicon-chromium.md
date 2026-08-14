# ローカルComposeとChromiumの復旧

## まず標準Composeを試す

Composeのplatformを変える前に、既存設定の実効値と最小commandを確認する。

```bash
docker version
docker compose config
docker compose ps
docker system df
docker compose run --rm --no-deps <service> <minimal-command>
```

この実行が成功するなら、arm64 overrideは不要である。

失敗ログ、実行時platform、browser versionを保存する。

## 失敗の分類

| 症状 | 確認すること | 復旧方針 |
| --- | --- | --- |
| daemonへ接続できない | `docker version`、context | runtimeを起動して同じcommandを再実行する |
| `node_modules`が存在しない | `readlink node_modules`、targetの存在 | host symlinkを消さず、専用volumeまたは既存の正しいworktreeを使う |
| Yarnの`EEXIST` | Compose project label、volume内容 | 専用一時volumeだけを空にして再試行する。継続する場合はvolume経由のfull installを中止する |
| `No space left on device` | `docker system df`、対象image・volumeのlabel | 今回作成した一時resourceだけを削除する |
| Chromium launch失敗 | browser version、missing library、platform | 必要libraryを一時containerへ導入する。標準構成でQEMU由来の失敗が再現した場合だけarm64を試す |

Yarnのworkspaceリンク競合は、sourceやlockfileの破損を意味しない。

空の専用volumeでも再現する場合は、volume経由の依存インストールを回避する。

## 一時環境の安全な作り方

一時Compose projectには既存環境と異なる名前を使う。

```bash
docker compose -p <temporary-project> \
  -f <compose-file> \
  -f <temporary-override.yml> \
  run --rm --no-deps <service> <command>
```

削除前にlabelで対象を確認する。

```bash
docker volume inspect <volume-name>
docker ps -a --filter name=<temporary-project>
docker image ls
```

既存Compose projectの名前で`docker compose down`を実行すると、同じprojectに属する他者のcontainerまで停止・削除する。

一時環境のcleanupは、確認済みのcontainer、image、volumeを名前で指定する。

## arm64を使う条件

Apple Siliconだからという理由だけで`linux/arm64`へ切り替えない。

次のすべてを満たす場合だけ、診断として一時overrideを使う。

1. 標準Composeでbrowser launch failureを再現している。
2. 依存関係と保存領域の問題を先に除外している。
3. 実効設定が`linux/x86_64`であり、ログがQEMUまたはemulationによる失敗を示している。

成功しても、それはnative arm64でのローカル診断結果である。

標準Compose、CI、productionの互換性を証明するものではない。

## E2E検証とAPI変更を分ける

必要な観測値が既存logやresponseに含まれるなら、まずそれらで実行経路を検証する。

観測値が不足していることと、対象機能が失敗していることを区別する。

一回限りの調査で追加計測が必要なら、次の順を優先する。

1. 既存log、response、artifactから結論を出せるか確認する。
2. 対象serviceを直接呼ぶ最小probeで観測する。
3. それでも必要な場合だけ、local-onlyの計測を使う。

計測用fieldをAPI schemaへ追加した場合は、検証後に差分を戻す。

artifactには入力、依存version、実行runtime、request、response、error、関連logを記録する。
