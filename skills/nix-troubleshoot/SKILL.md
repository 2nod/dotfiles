---
name: nix-troubleshoot
description: このリポジトリで nix run .#build / .#switch が失敗した時に使う（評価エラー、パッケージ問題、cask の上書き）。
---

# Nix トラブルシュート

## 対象
- このリポジトリで build/switch が失敗した場合の切り分け。

## 手順
1. まず `nix run .#build` を再実行してエラーを絞り込む。
2. エラー出力のファイル/行を特定して設定を修正する。
3. 主要な当たり所:
   - `nix/modules/home/**`（home-manager 周り）
   - `nix/modules/darwin/packages.nix`（cask の上書きや hash）
   - `flake.nix`（モジュール接続やホスト設定）
4. 再度 build → switch を実行する。

## 補足
- リンク済み設定ファイルが原因なら dotfiles-linking のパターンを確認する。
