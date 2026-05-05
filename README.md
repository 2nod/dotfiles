# nix-darwin dotfiles

## 概要
このリポジトリは macOS を nix-darwin + flakes で管理するための最小構成です。`flake.nix` を起点に `nix/modules/...` を読み込み、`nixpkgs-unstable` / `nix-darwin/master` / `home-manager` / `brew-nix` / `brew-api` を入力として、複数 Mac 向けのシステム構成 ( `darwinConfigurations` ) をエクスポートします。

## 役割分担
- nix-darwin: macOS のシステム設定、brew-nix の有効化。
- home-manager: ユーザー単位の CLI パッケージと brew-nix cask。
- brew-nix: Homebrew cask を Nix パッケージとして扱う仕組み。

## 何が入るか
- 一覧は [INSTALLS.md](/Users/tsuno/dotfiles/INSTALLS.md) にまとめています。

## 注意点
- `nix run .#switch -- <profile>` は、選んだ profile の `nix-darwin` と `home-manager` をまとめて適用します。
- `link_force` は既存のファイルやディレクトリを削除してから symlink を張るため、手元で編集した設定は上書きされます。
- `homebrew.onActivation.cleanup = "uninstall"` が有効なので、`homebrew.casks` から外した GUI アプリは削除対象になります。
- 初回適用や別 Mac への展開では、先に `INSTALLS.md` の上書き対象を確認してから `switch` してください。

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
1. [Nix](https://nixos.org/download.html) を macOS にインストールしておく（未導入なら下記の手順）。
2. `nix-command` と `flakes` を有効化しておく (初回実行の前に必要)。
3. 初回は `darwin-rebuild` が PATH に無いので、`nix run .#build -- <profile>` / `nix run .#switch -- <profile>` を使う。`switch` は途中で sudo を求められる。

### Nixのインストール
Nixがインストールされていない場合は、以下のコマンドでインストールします：
```bash
# Determinate Nix Installerを使用（推奨）
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install

# または、公式インストーラーを使用
sh <(curl -L https://nixos.org/nix/install) --daemon
```

インストール後、新しいターミナルを開くか、以下を実行して環境を読み込みます：
```bash
source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
```

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

※ `local.nix` はリポジトリ管理のため、秘密情報は入れない運用にしてください。プロファイルの設定手順は `nix/modules/profiles/README.md` を参照してください。複数 Mac を運用する場合は、Mac ごとに `profile` を分けて `system` / `hostName` を設定します。

## キーバインドと CLI ナビゲーション

### fzf キーバインド（fish shell）

| キー | 動作 |
|------|------|
| `Ctrl+G` | ghq で管理しているリポジトリを fzf で選択して cd |
| `Ctrl+B` | git ブランチを fzf で選択して switch |
| `Ctrl+T` | ファイルを fzf で選択してコマンドラインに挿入 |
| `Ctrl+R` | コマンド履歴を fzf で検索 |
| `Alt+C` | ディレクトリを fzf で選択して cd |
| `Ctrl+X Ctrl+K` | プロセスを fzf で選択して kill |

### リポジトリ管理（ghq）

`Ctrl+G` は `ghq list --full-path | roots | fzf` のパイプラインで動く。

- **ghq root**: `~/ghq`（`ghq get` でクローンした先）と `~/src`（手動クローン）の 2 つ
- **roots**: monorepo のルートディレクトリを検出する CLI。ghq の複数 root を正規化するフィルターとして使っている
- **運用方針**: 新規リポジトリは `ghq get github.com/<owner>/<repo>` で `~/ghq` に入れる。`~/src` は移行期の既存リポジトリ置き場

```fish
# リポジトリをクローン（~/ghq/github.com/<owner>/<repo> に入る）
ghq get github.com/<owner>/<repo>

# 管理リポジトリ一覧
ghq list
```

### ディレクトリ移動（zoxide）

`zoxide` が有効化されており、`z <keyword>` で訪問履歴からディレクトリジャンプできる。

```fish
z dotfiles   # ~/dotfiles に移動
z sig        # ~/src/signoz など履歴マッチで移動
```

## よく使うコマンド
- `nix run .#list-profiles`: 利用可能なプロファイル一覧を表示。
- `nix run .#build -- <profile>`: 指定したプロファイルで反映なしでビルドのみ行う。
- `nix run .#switch -- <profile>`: 指定したプロファイルで反映（途中で sudo を求められる）。
- `nix run .#update`: `flake.lock` を更新する。

## 変更と反映の流れ
1. `flake.nix` を編集してパッケージや設定を追加する。
2. 影響を確認したい場合は `nix run .#build -- <profile>` でビルドのみ行う。
3. 問題なければ `nix run .#switch -- <profile>` で本適用。

依存するチャネルを更新したい場合は `nix run .#update` (または `nix flake update`) を実行し、ロックファイル ( `flake.lock` ) が生成されたらコミットしてください。

## トラブルシューティング
### Nixが見つからない場合
新しいターミナルを開くか、シェル設定ファイル（`.zshrc`など）に以下を追加：
```bash
if [ -e '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh' ]; then
  . '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh'
fi
```

### ビルドエラーが発生した場合
```bash
# flake.lockを更新
nix run .#update

# 再度ビルド
nix run .#build -- <profile>
```

## リンクの挙動
`link_force` は、既存のファイル/ディレクトリを削除してからシンボリックリンクを張ります。
この repo では `nix/modules/home/dotfiles.nix` と `nix/modules/home/programs/neovim` で使っています。
手動で削除する必要はありませんが、必要なら `nix run .#switch -- <profile>` の前にバックアップを取っておくのがおすすめです。

例: `~/.bashrc`, `~/.bash_profile`, `~/.zshrc`, `~/.zshenv`, `~/.config/nvim`, `~/.config/wezterm`, `~/.config/aerospace`, `~/.config/karabiner` などが置き換わります。
Home Manager が生成する `~/.config/git/config` や `~/.local/state/home-manager/...` も作成されます。

## home-manager と link_force の使い分け
- パターンA（home-managerのみ）: `programs.*` で表現でき、設定量も無理なく Nix 化できるもの。例: `git`
- パターンB（home-manager + link_force）: モジュールは使いたいが、設定は既存ディレクトリをそのまま使いたいもの。例: `nvim`
- パターンC（link_forceのみ）: モジュールが無い、またはそのまま運用したい設定。例: `aerospace`/`wezterm`/`karabiner`/`bash`/`zsh`
- 判断フロー: 「モジュールがある？」→ Yes: Nix 化できるならA / 既存設定を残すならB、No: C
- 置き場所: `nix/modules/home/programs/` はA/B、repo直下の `wezterm/` などはCの設定置き場
- 引数方針: `dotfilesDir` などのカスタム引数は `import` で明示的に渡す（依存関係を見える化し、`_module.args` の暗黙依存を避けるため）

## よく編集する箇所
- `nix/modules/darwin/system.nix`: システム設定と brew-nix の有効化。
- `nix/modules/darwin/packages.nix`: brew-nix cask の追加場所 (home-manager 側)。
- `nix/modules/home/packages.nix`: CLI パッケージの追加場所 (例: `pkgs.gh`, `pkgs.pnpm`)。
- `programs.*`: 例として `programs.fish.enable = true;` をアンコメントすれば fish シェルを有効化できます。
- `system`: ARM Mac (Apple Silicon) 以外で使う場合は `local.nix` の `system` を明示します (例: `x86_64-darwin`)。
- `hostName`: Mac ごとにホスト名を変えたい場合は profile で指定します。
- `system.stateVersion`: nix-darwin の互換性のため、更新時はリリースノートを確認してください。

## ヒント
- `system.configurationRevision = self.rev or self.dirtyRev or null;` により `darwin-version` で現在のコミットが確認できます。Git 管理下で作業することで、構成の再現性を保てます。
- モジュールが増えてきたら `nix/modules/darwin/default.nix` や `nix/modules/home/default.nix` に `imports = [ ./foo.nix ];` を追加して分割できます。
- brew-nix cask は形式ごとに `unpackPhase` や `installPhase`、`hash` の上書きが必要な場合があり、`nix/modules/darwin/packages.nix` に例を置いてあります。
- 一部のアプリは初回起動時に `App is damaged` が出るので、`Privacy & Security` の `Open Anyway` で許可します。
- Nix の更新は新規インストール扱いになるため、アプリによっては設定やプロファイルがリセットされることがあります。

不明点があれば Issue や Pull Request でメモを残しておくと、次回セットアップ時の手間を減らせます。
