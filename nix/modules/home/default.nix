{
  config,
  lib,
  pkgs,
  profile ? { },
  dotfilesDir ? "${config.home.homeDirectory}/dotfiles",
  local-skills,
  ...
}:
let
  helpers = import ../lib/helpers { inherit lib; };
in
{
  imports = [
    (import ./agent-skills.nix { inherit local-skills; })
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
        helpers
        profile
        dotfilesDir
        ;
    })
  ];

  home.stateVersion = "24.11";

  programs.home-manager.enable = true;
}
