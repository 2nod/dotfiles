# nix-darwin dotfiles

## 概要
このリポジトリは macOS を nix-darwin + flakes で管理するための最小構成です。`flake.nix` を起点に `nix/modules/...` を読み込み、`nixpkgs-unstable` / `nix-darwin/master` / `home-manager` / `brew-nix` / `brew-api` を入力として、`yuheis-MacBook-Air` ホスト向けのシステム構成 ( `darwinConfigurations` ) をエクスポートします。

## 役割分担
- nix-darwin: macOS のシステム設定、brew-nix の有効化。
- home-manager: ユーザー単位の CLI パッケージと brew-nix cask。
- brew-nix: Homebrew cask を Nix パッケージとして扱う仕組み。

## 参考
- https://github.com/ryoppippi/dotfiles
- https://apribase.net/2025/03/24/brew-nix/
- https://dev.classmethod.jp/articles/shuntaka-claude-code-terminal-life/

## ディレクトリ構成
- `flake.nix`: すべての設定を定義しているフレーク。入力やモジュールの結線、`darwinConfigurations` を定義。
- `nix/`: Nix 設定をまとめるディレクトリ。
- `nix/modules/darwin/`: macOS 固有のモジュール。brew-nix cask 設定 ( `default.nix`, `packages.nix` ) とシステム設定 ( `system.nix` )。
- `nix/modules/home/`: home-manager のユーザー設定 ( `default.nix`, `packages.nix` )。OS 非依存の設定はここにまとめる。

## 前提条件
1. [Nix](https://nixos.org/download.html) を macOS にインストールしておく。
2. `nix-command` と `flakes` を有効化しておく (初回実行の前に必要)。
3. 初回は `darwin-rebuild` が PATH に無いので、`nix run .#build` / `nix run .#switch` を使う。`switch` は途中で sudo を求められる。

### `nix-command` / `flakes` の有効化
`/etc/nix/nix.conf` に追記してデーモンを再起動します。
```bash
sudo mkdir -p /etc/nix
echo "experimental-features = nix-command flakes" | sudo tee -a /etc/nix/nix.conf
sudo launchctl kickstart -k system/org.nixos.nix-daemon
```

一時的に使うだけなら、実行時に付ける方法もあります。
```bash
nix --extra-experimental-features "nix-command flakes" <command>
```

Determinate Nix を使う場合は、nix-darwin の Nix 管理を無効化する必要があります。
このリポジトリは `nix.enable = false;` を設定済みなので、Nix の設定は `/etc/nix/nix.conf` 側で行います。

## 最短の手順
```bash
# dotfiles を手元に取得
git clone git@github.com:<your-account>/dotfiles.git
cd dotfiles

# プロファイル一覧を確認
nix run .#list-profiles

# プロファイルを指定してビルド（任意）
nix run .#build -- <profile>

# プロファイルを指定して本適用（途中で sudo を求められる）
nix run .#switch -- <profile>
```

### プロファイルの使い方

このリポジトリは複数の環境（異なるuser/hostname）に対応するため、プロファイルベースの管理を採用しています。

**プロファイルの指定方法:**

1. **コマンドライン引数で指定（推奨）:**
   ```bash
   nix run .#switch -- PC-2111
   nix run .#build -- yuheis-MacBook-Air
   ```

2. **環境変数で指定:**
   ```bash
   NIX_DARWIN_PROFILE=PC-2111 nix run .#switch
   ```

3. **自動検出:**
   プロファイルが指定されていない場合、現在のホスト名に基づいて自動選択を試みます。

**初回セットアップ:**

個人固有のプロファイル定義は`local.nix`に記述します（`.gitignore`に含まれるため、リポジトリにコミットされません）:

```bash
# local.nix.exampleをコピーしてlocal.nixを作成
cp nix/modules/profiles/local.nix.example nix/modules/profiles/local.nix
```

`local.nix`に自分の環境情報を記述:

```nix
{
  "PC-2111" = {
    user = "your-username";
    hostname = "your-hostname";
    # オプション: dotfilesディレクトリのパス（デフォルト: /Users/${user}/dotfiles）
    # dotfilesDir = "/path/to/dotfiles";
    configOverrides = { pkgs, ... }: {
      # このプロファイル専用の設定
      home.packages = [ pkgs.some-package ];
    };
  };
}
```

**新しい環境を追加する場合:**

`local.nix`に新しいプロファイルを追加:

```nix
{
  "PC-2111" = { ... };
  "新しいマシン名" = {
    user = "ユーザー名";
    hostname = "ホスト名";
    configOverrides = { pkgs, ... }: { ... };
  };
}
```

**プロファイルごとに設定を変更する場合:**

`local.nix`の各プロファイルに`configOverrides`で設定を追加:

```nix
{
  "PC-2111" = {
    user = "your-username";
    hostname = "your-hostname";
    configOverrides = { pkgs, ... }: {
      # パッケージを追加
      home.packages = [ pkgs.docker-compose ];
      
      # Git設定を変更
      programs.git.userEmail = "work@example.com";
    };
  };
}
```

設定が大きい場合は、`extraModules`で別ファイルに分離することもできます。

**プロファイルの自動選択:**

プロファイルが1つだけ定義されている場合、自動的にそのプロファイルが選択されます:

```bash
# プロファイルが1つだけの場合
$ nix run .#build
Auto-selected profile: PC-2111 (only profile available)
```

複数のプロファイルがある場合は、明示的に指定する必要があります:

```bash
$ nix run .#build -- PC-2111
```

**注意**: `local.nix`は`.gitignore`に含まれているため、個人固有の設定を安全に管理できます。詳細は`nix/modules/profiles/README.md`を参照してください。

詳細は `nix/modules/profiles/README.md` を参照してください。

ホスト名は `scutil --get LocalHostName` または `hostname` で確認できます。

## よく使うコマンド
- `nix run .#list-profiles`: 利用可能なプロファイル一覧を表示。
- `nix run .#build -- <profile>`: 指定したプロファイルで反映なしでビルドのみ行う。
- `nix run .#switch -- <profile>`: 指定したプロファイルで反映（途中で sudo を求められる）。
- `nix run .#update`: `flake.lock` を更新する。

## 変更と反映の流れ
1. `flake.nix` を編集してパッケージや設定を追加する。
2. 影響を確認したい場合は `nix run .#build` でビルドのみ行う。
3. 問題なければ `nix run .#switch` で本適用。

依存するチャネルを更新したい場合は `nix run .#update` (または `nix flake update`) を実行し、ロックファイル ( `flake.lock` ) が生成されたらコミットしてください。

## リンクの挙動
`link_force` は、既存のファイル/ディレクトリを削除してからシンボリックリンクを張ります。
この repo では `nix/modules/home/dotfiles.nix` と `nix/modules/home/programs/neovim` で使っています。
手動で削除する必要はありませんが、必要なら `nix run .#switch` の前にバックアップを取っておくのがおすすめです。

例: `~/.bashrc`, `~/.bash_profile`, `~/.zshrc`, `~/.zshenv`, `~/.config/nvim`, `~/.config/wezterm`, `~/.config/karabiner` などが置き換わります。
Home Manager が生成する `~/.config/git/config` や `~/.local/state/home-manager/...` も作成されます。

## home-manager と link_force の使い分け
- パターンA（home-managerのみ）: `programs.*` で表現でき、設定量も無理なく Nix 化できるもの。例: `git`
- パターンB（home-manager + link_force）: モジュールは使いたいが、設定は既存ディレクトリをそのまま使いたいもの。例: `nvim`
- パターンC（link_forceのみ）: モジュールが無い、またはそのまま運用したい設定。例: `wezterm`/`karabiner`/`bash`/`zsh`
- 判断フロー: 「モジュールがある？」→ Yes: Nix 化できるならA / 既存設定を残すならB、No: C
- 置き場所: `nix/modules/home/programs/` はA/B、repo直下の `wezterm/` などはCの設定置き場
- 引数方針: `dotfilesDir` などのカスタム引数は `import` で明示的に渡す（依存関係を見える化し、`_module.args` の暗黙依存を避けるため）

## よく編集する箇所
- `nix/modules/darwin/system.nix`: システム設定と brew-nix の有効化。
- `nix/modules/darwin/packages.nix`: brew-nix cask の追加場所 (home-manager 側)。
- `nix/modules/home/packages.nix`: CLI パッケージの追加場所 (例: `pkgs.gh`, `pkgs.pnpm`)。
- `programs.*`: 例として `programs.fish.enable = true;` をアンコメントすれば fish シェルを有効化できます。
- `darwinSystem` / `nixpkgs.hostPlatform`: ARM Mac (Apple Silicon) 以外で使う場合は両方を変更します (例: `x86_64-darwin`)。
- `system.stateVersion`: nix-darwin の互換性のため、更新時はリリースノートを確認してください。

## ヒント
- `system.configurationRevision = self.rev or self.dirtyRev or null;` により `darwin-version` で現在のコミットが確認できます。Git 管理下で作業することで、構成の再現性を保てます。
- モジュールが増えてきたら `nix/modules/darwin/default.nix` や `nix/modules/home/default.nix` に `imports = [ ./foo.nix ];` を追加して分割できます。
- brew-nix cask は形式ごとに `unpackPhase` や `installPhase`、`hash` の上書きが必要な場合があり、`nix/modules/darwin/packages.nix` に例を置いてあります。
- 一部のアプリは初回起動時に `App is damaged` が出るので、`Privacy & Security` の `Open Anyway` で許可します。
- Nix の更新は新規インストール扱いになるため、アプリによっては設定やプロファイルがリセットされることがあります。

不明点があれば Issue や Pull Request でメモを残しておくと、次回セットアップ時の手間を減らせます。
