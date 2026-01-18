# 個人固有のプロファイル定義
# このファイルはリポジトリ管理のため、秘密情報は入れないでください

{
  "personal" = {
    user = "tsuno";
    # dotfilesディレクトリのパス（オプション、デフォルト: /Users/${user}/dotfiles）
    dotfilesDir = "/Users/tsuno/dotfiles";

    # home-manager側の設定を追加/上書きする場合（オプション）
    # configOverrides = { pkgs, ... }: { ... };

    # nix-darwin側の設定を追加/上書きする場合（オプション）
    # extraModules = [ ../../profiles/personal-darwin.nix ];
  };

  "work" = {
    user = "tsuno";
    # dotfilesディレクトリのパス（オプション、デフォルト: /Users/${user}/dotfiles）
    dotfilesDir = "/Users/tsuno/dotfiles";

    # home-manager側の設定を追加/上書きする場合（オプション）
    # configOverrides = { pkgs, ... }: { ... };

    # nix-darwin側の設定を追加/上書きする場合（オプション）
    # extraModules = [ ../../profiles/work-darwin.nix ];
  };
  # 新しい環境を追加する場合は、ここに追加してください
  # "新しいマシン名" = {
  #   user = "ユーザー名";
  #   # dotfilesDir = "/path/to/dotfiles";  # オプション
  #   configOverrides = { pkgs, ... }: { ... };
  # };
}
