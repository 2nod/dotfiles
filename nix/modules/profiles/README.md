# プロファイル固有の設定

このディレクトリには、プロファイル設定を`local.nix`に記述します。すべてのプロファイル定義を1つのファイルで管理します。

## セットアップ

### 初回セットアップ

1. `local.nix.example`をコピーして`local.nix`を作成:
   ```bash
   cp nix/modules/profiles/local.nix.example nix/modules/profiles/local.nix
   ```

2. `local.nix`に自分の環境情報を記述:
   ```nix
   {
     "PC-2111" = {
       user = "your-username";
       hostname = "your-hostname";
       configOverrides = { pkgs, ... }: {
         # このプロファイル専用の設定
       };
     };
   }
   ```

**注意**: `local.nix`は`.gitignore`に含まれているため、リポジトリにコミットされません。個人固有の設定はここに記述してください。

## 使い方

### プロファイルファイルの構造

`local.nix`は以下の構造を持ちます:

```nix
{
  "プロファイル名" = {
    user = "your-username";           # 必須: ユーザー名
    hostname = "your-hostname";       # 必須: ホスト名
    
    # オプション: dotfilesディレクトリのパス（デフォルト: /Users/${user}/dotfiles）
    dotfilesDir = "/path/to/dotfiles";
    
    # オプション: 追加モジュール
    extraModules = [ ./some-module.nix ];
    
    # オプション: 設定オーバーライド
    configOverrides = { pkgs, ... }: {
      # このプロファイル専用の設定
      home.packages = [ pkgs.some-package ];
      programs.git.userEmail = "work@example.com";
    };
  };
}
```

### プロファイルごとに設定を変更

#### 方法1: configOverridesで直接記述（推奨）

```nix
{
  "PC-2111" = {
    user = "your-username";
    hostname = "your-hostname";
    configOverrides = { pkgs, ... }: {
      # パッケージを追加
      home.packages = [ pkgs.docker-compose pkgs.terraform ];
      
      # Git設定を変更
      programs.git.userEmail = "work@example.com";
      
      # シェル設定を追加
      programs.fish.shellAliases = {
        work = "cd ~/work";
      };
    };
  };
}
```

#### 方法2: 別ファイルに分離（設定が大きい場合）

```nix
# local.nix
{
  "PC-2111" = {
    user = "your-username";
    hostname = "your-hostname";
    extraModules = [ ./PC-2111-config.nix ];
  };
}
```

```nix
# PC-2111-config.nix
{ pkgs, ... }:
{
  home.packages = [ pkgs.docker-compose ];
  programs.git.userEmail = "work@example.com";
}
```

## プロファイルの自動選択

プロファイルが1つだけ定義されている場合、自動的にそのプロファイルが選択されます:

```bash
# プロファイルが1つだけの場合
$ nix run .#build
Auto-selected profile: PC-2111 (only profile available)
Building darwin configuration for profile: PC-2111
```

複数のプロファイルがある場合は、明示的に指定する必要があります:

```bash
# 複数のプロファイルがある場合
$ nix run .#build -- PC-2111
```

## 設定の優先順位

1. ベース設定（`nix/modules/home/`, `nix/modules/darwin/`）
2. `extraModules`で追加されたモジュール
3. `configOverrides`で定義された設定（最優先）

## 例

### プロファイルごとに異なるパッケージをインストール

```nix
{
  "PC-2111" = {
    user = "your-username";
    hostname = "PC-2111";
    configOverrides = { pkgs, ... }: {
      home.packages = [
        pkgs.docker-compose
        pkgs.terraform
      ];
    };
  };
}
```

### プロファイルごとに異なるGit設定

```nix
{
  "PC-2111" = {
    user = "your-username";
    hostname = "PC-2111";
    configOverrides = { ... }: {
      programs.git = {
        userEmail = "work@example.com";
        userName = "Work Account";
      };
    };
  };
}
```

### プロファイルごとに異なるシェル設定

```nix
{
  "PC-2111" = {
    user = "your-username";
    hostname = "PC-2111";
    configOverrides = { ... }: {
      programs.fish = {
        shellAliases = {
          work = "cd ~/work";
          deploy = "cd ~/work && ./deploy.sh";
        };
      };
    };
  };
}
```
