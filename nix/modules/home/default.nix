{ config, lib, pkgs, dotfilesDir ? "${config.home.homeDirectory}/dotfiles", ... }:
let
  helpers = import ../lib/helpers { inherit lib; };
in
{
  imports = [
    ./packages.nix
    (import ./dotfiles.nix {
      inherit
        lib
        config
        helpers
        dotfilesDir
        ;
    })
    (import ./programs {
      inherit
        pkgs
        lib
        config
        dotfilesDir
        ;
    })
  ];

  home.stateVersion = "24.11";

  programs.home-manager.enable = true;
}
