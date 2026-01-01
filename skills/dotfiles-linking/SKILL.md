---
name: dotfiles-linking
description: 設定ファイルの管理方法と link_force の判断で使う（home-manager とシンボリックリンク運用の使い分け）。
---

# Dotfiles リンク運用

## 対象
- 設定を home-manager / link_force / 併用のどれで管理するか判断する。

## 手順
1. home-manager のモジュール有無と、設定を Nix 管理するかを確認する。
2. パターンを選ぶ:
   - A: home-manager のみ（`programs.*` または `xdg.configFile`）
   - B: home-manager + link_force（既存設定ディレクトリを維持したい場合）
   - C: link_force のみ（モジュールが無い or そのまま運用したい場合）
3. 配置先:
   - A/B: `nix/modules/home/programs/` または `nix/modules/home/*.nix`
   - C: `nvim/` / `wezterm/` / `zsh/` / `karabiner/` など repo 直下
4. `nix run .#build` と `nix run .#switch` で反映する。

## 補足
- `link_force` はリンク前に既存ファイル/ディレクトリを置き換える。
