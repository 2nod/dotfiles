{ ... }:
{
  imports = [
    ./packages.nix
  ];

  home.stateVersion = "24.11";

  programs.home-manager.enable = true;
}
