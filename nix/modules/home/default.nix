{ ... }:
{
  imports = [
    ./packages.nix
    ./dotfiles.nix
  ];

  home.stateVersion = "24.11";

  programs.home-manager.enable = true;
}
