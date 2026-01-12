# プロファイル固有の設定

このディレクトリには、プロファイル設定を`local.nix`に記述します。すべてのプロファイル定義を1つのファイルで管理します。

## セットアップ

### 初回セットアップ

1. `local.nix`を編集（必要なら`local.nix.example`を参照）:
   ```bash
   $EDITOR nix/modules/profiles/local.nix
   ```

2. `local.nix`に personal/work を分けて記述:
   ```nix
   {
    "personal" = {
      user = "your-username";
    };

    "work" = {
      user = "your-username";
    };
  }
   ```

**注意**: `local.nix`はリポジトリ管理のため、変更はコミット対象です。秘密情報は入れない運用にしてください。

## 使い方

### プロファイルファイルの構造

`local.nix`は以下の構造を持ちます:

```nix
{
  "personal" = {
    user = "your-username";           # 必須: ユーザー名
    
    # オプション: dotfilesディレクトリのパス（デフォルト: /Users/${user}/dotfiles）
    dotfilesDir = "/path/to/dotfiles";
    
    # オプション: 追加モジュール
    extraModules = [ ./some-module.nix ];

    # オプション: 設定オーバーライド（local.nix だけに閉じたい時に使用）
    # configOverrides = { pkgs, ... }: { ... };
  };
}
```

### プロファイルごとに設定を変更

このリポジトリでは、home-manager のプロファイル別設定は `local.nix` の `configOverrides` に集約します。

#### 方法1: local.nix の configOverrides に記述（推奨）

```nix
# local.nix
{
  "work" = {
    user = "your-username";
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

#### nix-darwin側の設定を追加/上書きする場合

`configOverrides` は home-manager のユーザー設定向けです。`system.*` や `environment.*` などの nix-darwin 側を触る場合は `extraModules` を使います。

```nix
# local.nix
{
  "work" = {
    user = "your-username";
    # local.nix からの相対パスなので ../../profiles を参照
    extraModules = [ ../../profiles/work-darwin.nix ];
  };
}
```

```nix
# nix/profiles/work-darwin.nix
{ pkgs, lib, ... }:
{
  environment.systemPackages = [ pkgs.git pkgs.gnupg ];
  system.defaults.dock.autohide = true;

  # 値を強制的に上書きしたい場合
  # system.defaults.NSGlobalDomain.KeyRepeat = lib.mkForce 2;
}
```

補足:
- `extraModules` は nix-darwin のモジュールとして読み込まれます（`nix/modules/darwin/*` と同じ扱い）。
- 追記/上書きの挙動は Nix モジュールの型に依存します（リストは連結、属性セットはマージ、同一キーは後勝ち）。

#### 設定が大きい場合は分割

```nix
# local.nix
{
  "work" = {
    user = "your-username";
    # local.nix と同じディレクトリなので ./work-home.nix を参照
    configOverrides = { ... }: import ./work-home.nix;
  };
}
```

```nix
# nix/modules/profiles/work-home.nix
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
Auto-selected profile: personal (only profile available)
Building darwin configuration for profile: personal
```

複数のプロファイルがある場合は、明示的に指定する必要があります:

```bash
# 複数のプロファイルがある場合
$ nix run .#build -- work
```

## 設定の優先順位

home-manager 側:
1. ベース設定（`nix/modules/home/`）
2. `configOverrides`で定義された設定（最優先）

nix-darwin 側:
1. ベース設定（`nix/modules/darwin/`）
2. `extraModules`で追加されたモジュール（最優先）

## 例

### プロファイルごとに異なるパッケージをインストール

```nix
# local.nix
{
  "work" = {
    user = "your-username";
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
# local.nix
{
  "work" = {
    user = "your-username";
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
# local.nix
{
  "work" = {
    user = "your-username";
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
