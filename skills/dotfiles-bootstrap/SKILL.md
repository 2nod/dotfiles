---
name: dotfiles-bootstrap
description: このnix-darwin dotfilesリポジトリを新しいマシン/ホストにセットアップする時に使う（Nix導入、nix-command/flakes有効化、初回build/switch、hostname一致確認）。
---

# Dotfiles 初期セットアップ

## 対象
- このリポジトリを新しいマシン/新しいホストにセットアップする場合。

## 手順
1. Nix を導入し、nix-command/flakes を有効化する。
2. リポジトリをクローンし、ホスト名が `flake.nix` の設定と一致しているか確認する。
3. `nix run .#build`（任意）→ `nix run .#switch` の順で実行する。

## コマンド
```
scutil --get LocalHostName
nix run .#build
nix run .#switch
```

## 補足
- ホスト名が異なる場合は `flake.nix` と `darwinConfigurations` を更新する。
- `nix run .#switch` で sudo が要求される。
- 前提条件や詳細は `README.md` を参照する。
