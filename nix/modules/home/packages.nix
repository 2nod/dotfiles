{ pkgs, ... }:
{
  # CLI packages live here (home-manager).
  home.packages = [
    pkgs.bat
    pkgs.bun
    pkgs.claude-code
    pkgs.codex
    pkgs.deno
    pkgs.gh
    pkgs.git
    pkgs.lazygit
    pkgs.pnpm
    pkgs.uv
    pkgs.wezterm
    pkgs.yazi
  ];
}
