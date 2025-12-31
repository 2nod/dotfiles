{ pkgs, ... }:
{
  # CLI packages live here (home-manager).
  home.packages = [
    pkgs.bun
    pkgs.codex
    pkgs.deno
    pkgs.gh
    pkgs.git
    pkgs.neovim
    pkgs.pnpm
    pkgs.uv
    pkgs.wezterm
  ];
}
