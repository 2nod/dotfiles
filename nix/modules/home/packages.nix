{ pkgs, ... }:
{
  # CLI packages live here (home-manager).
  home.packages = [
    pkgs.neovim
    pkgs.gh
  ];
}
