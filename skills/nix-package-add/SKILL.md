---
name: nix-package-add
description: このリポジトリでパッケージ追加や有効化を行う時に使う（CLIパッケージ、home-manager programs、brew-nix cask）。
---

# Nix パッケージ追加

## 対象
- CLI パッケージ追加、home-manager programs の有効化、brew-nix cask の追加。

## 手順
1. 対象を選ぶ:
   - CLI パッケージ: `nix/modules/home/packages.nix`
   - Programs: `nix/modules/home/programs/*.nix`
   - Casks: `nix/modules/darwin/packages.nix`
2. パッケージ追加または program を有効化する。
3. cask の上書きが必要なら `unpackPhase` / `installPhase` / `hash` を調整する。
4. `nix run .#build` で検証し、`nix run .#switch` で反映する。

## 補足
- 設定ファイルのリンク/保持が必要なら dotfiles-linking を使う。
