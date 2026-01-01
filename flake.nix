{
  description = "Example nix-darwin system flake";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
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
  };

  outputs = inputs@{ self, nix-darwin, nixpkgs, brew-nix, home-manager, ... }:
  let
    user = "tsuno";
    hostname = "yuheis-MacBook-Air";
    darwinSystem = "aarch64-darwin";
    pkgs = import nixpkgs { system = darwinSystem; };
  in
  {
    # Build darwin flake using:
    # $ darwin-rebuild build --flake .#yuheis-MacBook-Air
    darwinConfigurations."${hostname}" = nix-darwin.lib.darwinSystem {
      system = darwinSystem;
      specialArgs = { inherit self user; };
      modules =
        [
          brew-nix.darwinModules.default
          ./nix/modules/darwin/system.nix
          home-manager.darwinModules.home-manager
          {
            home-manager = {
              useGlobalPkgs = true;
              useUserPackages = true;
              extraSpecialArgs = { inherit user; };
              users.${user} =
                { pkgs, config, lib, ... }:
                {
                  imports = [
                    (import ./nix/modules/home {
                      inherit
                        pkgs
                        config
                        lib
                        ;
                      dotfilesDir = "/Users/${user}/dotfiles";
                    })
                    ./nix/modules/darwin
                  ];
                  home.username = user;
                  home.homeDirectory = "/Users/${user}";
                };
            };
          }
        ];
    };

    apps.${darwinSystem} = {
      build = {
        type = "app";
        program = toString (
          pkgs.writeShellScript "darwin-build" ''
            set -e
            echo "Building darwin configuration..."
            nix build .#darwinConfigurations.${hostname}.system
            echo "Build successful! Run 'nix run .#switch' to apply."
          ''
        );
      };

      switch = {
        type = "app";
        program = toString (
          pkgs.writeShellScript "darwin-switch" ''
            set -e
            echo "Building and switching darwin configuration..."
            sudo nix run nix-darwin -- switch --flake .#${hostname}
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
            echo "Done! Run 'nix run .#switch' to apply changes."
          ''
        );
      };
    };
  };
}
