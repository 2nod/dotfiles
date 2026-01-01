---
name: dotfiles-linking
description: このリポジトリで dotfiles を home-manager と link_force のどちらで管理するか判断し、配置先と反映手順を決めるときに使う。
---

# Dotfiles リンク運用

## 使う場面
- 新しい設定を追加/移行する。
- home-manager 管理か link_force 運用か迷う。
- link_force の追加/更新を行う。

## 判断フロー
1. home-manager の `programs.*` で表現できるか？
2. 設定を Nix 化できるか、既存ディレクトリを維持したいか？

### パターン
- A: home-manager のみ（`programs.*`）
  - 条件: Nix 化でき、設定をモジュール内で完結させたい
- B: home-manager + link_force
  - 条件: `programs.*` は使うが、既存設定ディレクトリを維持したい
- C: link_force のみ
  - 条件: モジュールが無い / 今は Nix 化しない

## 配置先と作業
- A/B:
  - `nix/modules/home/programs/<name>/default.nix` を作成/更新
  - `nix/modules/home/programs/default.nix` に import を追加
  - B の場合は `home.activation.*` で `link_force` を追加
- C:
  - 設定は repo 直下に置く（`wezterm/`, `zsh/` など）
  - `nix/modules/home/dotfiles.nix` に `link_force` を追加

## link_force の使い方
- `helpers.activation.mkLinkForce` を読み込み、`lib.hm.dag.entryAfter [ "linkGeneration" ]` で実行する。
- `link_force <src> <dest>` は既存ファイル/ディレクトリを削除して張り替えるため、必要ならバックアップを取る。
- `dotfilesDir` などの引数は import で明示的に渡し、ハードコードしない。

## 反映コマンド
- `nix run .#build`
- `nix run .#switch`

## 参考パターン
- A: `nix/modules/home/programs/git/default.nix`
- B: `nix/modules/home/programs/neovim/default.nix`
- C: `nix/modules/home/dotfiles.nix`

## 補足
- `link_force` はリンク前に既存ファイル/ディレクトリを置き換える。
