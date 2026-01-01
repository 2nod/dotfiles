{ config, lib, dotfilesDir ? "${config.home.homeDirectory}/dotfiles", ... }:
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
  ];

  home.stateVersion = "24.11";

  programs.home-manager.enable = true;
}
