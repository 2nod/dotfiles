# nix-darwin dotfiles

## 概要
このリポジトリは macOS を nix-darwin + flakes で管理するための最小構成です。`flake.nix` だけで構成されており、`nixpkgs-unstable` と `nix-darwin/master` を入力として読み込み、`yuheis-MacBook-Air` ホスト向けのシステム構成 ( `darwinConfigurations` ) をエクスポートします。

## ディレクトリ構成
- `flake.nix`: すべての設定を定義しているフレーク。`environment.systemPackages` にインストールするパッケージ、`nix.settings` や `system.stateVersion` などのベース設定を記述。
- `darwin/`: 将来的にモジュールを分割配置したい場合の配置先 (現状は空)。
- `home-manager/`: home-manager 用のモジュールを置く想定のディレクトリ (現状は空)。
- `shell/`: 補助的なスクリプトやシェル設定を置くためのディレクトリ (現状は空)。

## 前提条件
1. [Nix](https://nixos.org/download.html) を macOS にインストールしておく。
2. `nix-command` と `flakes` を有効化 (本フレークでは `nix.settings.experimental-features = "nix-command flakes";` を設定済み)。
3. `nix run nix-darwin -- switch --flake .#yuheis-MacBook-Air` を初回に実行できるよう、`darwin-rebuild` を利用可能にしておく。

## 初回セットアップ
```bash
# dotfiles を手元に取得
mkdir -p ~/src && cd ~/src
git clone git@github.com:<your-account>/dotfiles.git
cd dotfiles

# 初めて適用する場合
nix run nix-darwin -- switch --flake .#yuheis-MacBook-Air
```

`yuheis-MacBook-Air` の部分は `flake.nix` 内の `darwinConfigurations` 名に合わせて変更してください。ホスト名を変えたい場合は `flake.nix` を編集し、`darwinConfigurations."<hostname>" = ...` を追加・変更します。

## 変更と反映の流れ
1. `flake.nix` を編集してパッケージや設定を追加する。
2. 影響を確認したい場合は `darwin-rebuild test --flake .#yuheis-MacBook-Air` を実行して sandboxed な適用を行う。
3. 問題なければ `darwin-rebuild switch --flake .#yuheis-MacBook-Air` で本適用。

依存するチャネルを更新したい場合は `nix flake update` を実行し、ロックファイル ( `flake.lock` ) が生成されたらコミットしてください。

## よく編集する箇所
- `environment.systemPackages`: `pkgs.vim` のようにインストールしたいパッケージを並べます。
- `programs.*`: 例として `programs.fish.enable = true;` をアンコメントすれば fish シェルを有効化できます。
- `nixpkgs.hostPlatform`: ARM Mac (Apple Silicon) 以外で使う場合はここを変更します。
- `system.stateVersion`: nix-darwin の互換性のため、更新時はリリースノートを確認してください。

## ヒント
- `system.configurationRevision = self.rev or self.dirtyRev or null;` により `darwin-version` で現在のコミットが確認できます。Git 管理下で作業することで、構成の再現性を保てます。
- モジュールが増えてきたら `darwin/` や `home-manager/` ディレクトリに `.nix` ファイルを作成し、`modules = [ configuration ];` のリストに追加する形で整理できます。
- shell の便利スクリプト類は `shell/` 以下に置き、`environment.shells` や `programs.zsh` 等から読み込むようにすると管理しやすくなります。

不明点があれば Issue や Pull Request でメモを残しておくと、次回セットアップ時の手間を減らせます。
