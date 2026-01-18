{
  description = "Example nix-darwin system flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    nix-darwin.url = "github:nix-darwin/nix-darwin/master";
    nix-darwin.inputs.nixpkgs.follows = "nixpkgs";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    brew-nix = {
      url = "github:BatteredBunny/brew-nix";
      inputs.brew-api.follows = "brew-api";
      inputs.nix-darwin.follows = "nix-darwin";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    brew-api = {
      url = "github:BatteredBunny/brew-api";
      flake = false;
    };
    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    inputs@{
      self,
      nix-darwin,
      nixpkgs,
      brew-nix,
      home-manager,
      treefmt-nix,
      ...
    }:
    let
      darwinSystem = "aarch64-darwin";
      pkgs = import nixpkgs { system = darwinSystem; };

      treefmtEval = treefmt-nix.lib.evalModule pkgs {
        projectRootFile = "flake.nix";
        programs = {
          nixfmt = {
            enable = true;
            package = pkgs.nixfmt;
          };
          stylua.enable = true;
          shfmt.enable = true;
        };
        settings = {
          global.excludes = [
            ".git/**"
            "result/**"
          ];
          formatter = {
            fish-indent = {
              command = "${pkgs.fish}/bin/fish_indent";
              options = [ "--write" ];
              includes = [ "*.fish" ];
            };
          };
        };
      };

      # プロファイル定義を別ファイルから読み込む
      localProfilesPath = ./nix/modules/profiles/local.nix;
      profiles =
        if builtins.pathExists localProfilesPath then
          import localProfilesPath
        else
          (
            # local.nixが存在しない場合の警告
            builtins.trace ''
              ⚠️  Warning: local.nix not found!

              Please create nix/modules/profiles/local.nix by copying local.nix.example:
                cp nix/modules/profiles/local.nix.example nix/modules/profiles/local.nix

              Then edit local.nix with your profile definitions.
            '' { }
          );

      # 利用可能なプロファイル名のリスト（実際に存在するもののみ）
      availableProfileNames = builtins.attrNames profiles;

      # プロファイル名のリストを文字列として取得（シェルスクリプトで使用）
      profileNamesStr = builtins.concatStringsSep " " availableProfileNames;

      # プロファイルからdarwinConfigurationを生成するヘルパー関数
      mkDarwinConfig =
        profileName:
        {
          user,
          dotfilesDir ? "/Users/${user}/dotfiles",
          extraModules ? [ ],
          configOverrides ? null,
        }:
        nix-darwin.lib.darwinSystem {
          system = darwinSystem;
          specialArgs = {
            inherit self user;
            profile = profileName;
          };
          modules = [
            brew-nix.darwinModules.default
            ./nix/modules/darwin/system.nix
            home-manager.darwinModules.home-manager
            {
              home-manager = {
                useGlobalPkgs = true;
                useUserPackages = true;
                extraSpecialArgs = {
                  inherit user;
                  profile = profileName;
                };
                users.${user} =
                  {
                    pkgs,
                    config,
                    lib,
                    ...
                  }:
                  {
                    imports = [
                      (import ./nix/modules/home {
                        inherit pkgs config lib;
                        inherit dotfilesDir;
                      })
                      ./nix/modules/darwin
                    ]
                    # プロファイル固有の設定オーバーライドをモジュールとして追加
                    ++ (if configOverrides != null then [ (configOverrides { inherit pkgs config lib; }) ] else [ ]);
                    home.username = user;
                    home.homeDirectory = "/Users/${user}";
                  };
              };
            }
          ]
          # プロファイル固有の追加モジュールを適用
          ++ extraModules;
        };

      # すべてのプロファイルからdarwinConfigurationsを生成
      darwinConfigs = builtins.mapAttrs (name: profile: mkDarwinConfig name profile) profiles;

      listProfilesApp = {
        type = "app";
        program = toString (
          pkgs.writeShellScript "list-profiles" ''
            set -e
            AVAILABLE_PROFILES="${profileNamesStr}"

            if [ -z "$AVAILABLE_PROFILES" ]; then
              echo "No profiles found."
              echo "Please create a profile file in nix/modules/profiles/"
              exit 1
            fi

            echo "Available profiles:"
            for p in $AVAILABLE_PROFILES; do
              echo "  $p"
            done
            echo ""
            echo "Usage:"
            echo "  nix run .#switch -- <profile>"
            echo "  NIX_DARWIN_PROFILE=<profile> nix run .#switch"
          ''
        );
      };
    in
    {
      # プロファイルごとのdarwinConfigurations
      darwinConfigurations = darwinConfigs;

      formatter.${darwinSystem} = treefmtEval.config.build.wrapper;

      checks.${darwinSystem}.formatting = treefmtEval.config.build.check self;

      apps.${darwinSystem} = {
        build = {
          type = "app";
          program = toString (
            pkgs.writeShellScript "darwin-build" ''
              # プロファイル名のリストを環境変数として設定
              export AVAILABLE_PROFILES="${profileNamesStr}"

              set -e

              # プロファイル選択ロジック
              PROFILE="''${NIX_DARWIN_PROFILE:-}"

              # コマンドライン引数からプロファイルを取得（最優先）
              if [ $# -gt 0 ]; then
                PROFILE="$1"
              fi

              # プロファイルが指定されていない場合
              if [ -z "$PROFILE" ]; then
                AVAILABLE_PROFILES="${profileNamesStr}"
                
                if [ -z "$AVAILABLE_PROFILES" ]; then
                  echo "Error: No profiles found!"
                  echo "Please create a profile file in nix/modules/profiles/"
                  exit 1
                fi
                
                # プロファイルが1つだけの場合、自動選択
                if [ $(echo "$AVAILABLE_PROFILES" | wc -w) -eq 1 ]; then
                  PROFILE="$AVAILABLE_PROFILES"
                  echo "Auto-selected profile: $PROFILE (only profile available)"
                else
                  echo "Error: Profile not specified."
                  echo ""
                  echo "Available profiles:"
                  for p in $AVAILABLE_PROFILES; do
                    echo "  $p"
                  done
                  echo ""
                  echo "Please specify a profile using:"
                  echo "  NIX_DARWIN_PROFILE=<profile> nix run .#build"
                  echo "  or"
                  echo "  nix run .#build -- <profile>"
                  exit 1
                fi
              fi

              echo "Building darwin configuration for profile: $PROFILE"
              nix build .#darwinConfigurations."$PROFILE".system
              echo "Build successful! Run 'nix run .#switch -- $PROFILE' to apply."
            ''
          );
        };

        switch = {
          type = "app";
          program = toString (
            pkgs.writeShellScript "darwin-switch" ''
              # プロファイル名のリストを環境変数として設定
              export AVAILABLE_PROFILES="${profileNamesStr}"

              set -e

              # プロファイル選択ロジック
              PROFILE="''${NIX_DARWIN_PROFILE:-}"

              # コマンドライン引数からプロファイルを取得（最優先）
              if [ $# -gt 0 ]; then
                PROFILE="$1"
              fi

              # プロファイルが指定されていない場合
              if [ -z "$PROFILE" ]; then
                AVAILABLE_PROFILES="${profileNamesStr}"
                
                if [ -z "$AVAILABLE_PROFILES" ]; then
                  echo "Error: No profiles found!"
                  echo "Please create a profile file in nix/modules/profiles/"
                  exit 1
                fi
                
                # プロファイルが1つだけの場合、自動選択
                if [ $(echo "$AVAILABLE_PROFILES" | wc -w) -eq 1 ]; then
                  PROFILE="$AVAILABLE_PROFILES"
                  echo "Auto-selected profile: $PROFILE (only profile available)"
                else
                  echo "Error: Profile not specified."
                  echo ""
                  echo "Available profiles:"
                  for p in $AVAILABLE_PROFILES; do
                    echo "  $p"
                  done
                  echo ""
                  echo "Please specify a profile using:"
                  echo "  NIX_DARWIN_PROFILE=<profile> nix run .#switch"
                  echo "  or"
                  echo "  nix run .#switch -- <profile>"
                  exit 1
                fi
              fi

              echo "Building and switching darwin configuration for profile: $PROFILE"
              sudo nix run nix-darwin -- switch --flake .#"$PROFILE"
            ''
          );
        };

        update = {
          type = "app";
          program = toString (
            pkgs.writeShellScript "flake-update" ''
              set -e
              echo "Updating flake.lock..."
              nix flake update
              echo "Done! Run 'nix run .#switch -- <profile>' to apply changes."
            ''
          );
        };

        fmt = {
          type = "app";
          program = toString (
            pkgs.writeShellScript "treefmt-wrapper" ''
              exec ${treefmtEval.config.build.wrapper}/bin/treefmt "$@"
            ''
          );
        };

        # プロファイル一覧を表示
        list-profiles = listProfilesApp;
        list = listProfilesApp;
      };
    };
}
