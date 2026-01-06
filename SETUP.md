# dotfiles セットアップ手順

このPC環境（`PC-2111`、ユーザー: `yuhei.tsunoda`）に適用する手順です。

## 前提条件の確認とセットアップ

### 1. Nixのインストール

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

### 2. nix-command と flakes の有効化

Nixの実験的機能を有効化します：

```bash
sudo mkdir -p /etc/nix
echo "experimental-features = nix-command flakes" | sudo tee -a /etc/nix/nix.conf
sudo launchctl kickstart -k system/org.nixos.nix-daemon
```

### 3. dotfilesの適用

```bash
# dotfilesディレクトリに移動
cd ~/dotfiles

# 利用可能なプロファイルを確認
nix run .#list-profiles

# プロファイルを指定してビルド（任意、動作確認用）
# 例: PC-2111環境の場合
nix run .#build -- PC-2111

# プロファイルを指定して本適用（途中でsudoパスワードを求められます）
# 例: PC-2111環境の場合
nix run .#switch -- PC-2111
```

**プロファイルの指定方法:**

- **コマンドライン引数（推奨）:** `nix run .#switch -- <profile>`
- **環境変数:** `NIX_DARWIN_PROFILE=<profile> nix run .#switch`
- **自動検出:** プロファイルを指定しない場合、現在のホスト名から自動選択を試みます

## 注意事項

- `nix run .#switch` を実行すると、以下のファイル/ディレクトリがシンボリックリンクに置き換わります：
  - `~/.bashrc`
  - `~/.bash_profile`
  - `~/.zshrc`
  - `~/.zshenv`
  - `~/.config/nvim`
  - `~/.config/wezterm`
  - `~/.config/karabiner`
  
  必要に応じて、事前にバックアップを取っておくことをおすすめします。

- 一部のアプリは初回起動時に「App is damaged」と表示される場合があります。その場合は、`システム設定` > `プライバシーとセキュリティ` で「開く」をクリックして許可してください。

## よく使うコマンド

- `nix run .#list-profiles`: 利用可能なプロファイル一覧を表示
- `nix run .#build -- <profile>`: 指定したプロファイルで反映なしでビルドのみ行う
- `nix run .#switch -- <profile>`: 指定したプロファイルで設定を反映（sudoが必要）
- `nix run .#update`: `flake.lock`を更新して依存関係を最新化

**例:**
```bash
# PC-2111環境の場合
nix run .#switch -- PC-2111

# yuheis-MacBook-Air環境の場合
nix run .#switch -- yuheis-MacBook-Air
```

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
nix run .#build
```

