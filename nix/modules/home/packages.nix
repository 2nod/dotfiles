{ pkgs, ... }:
{
  # CLI packages live here (home-manager).
  home.packages = [
    pkgs.bat
    pkgs.bun
    pkgs.claude-code
    pkgs.mise
    pkgs.codex
    pkgs.deno
    pkgs.eza
    pkgs.gh
    pkgs.git
    pkgs.lazygit
    pkgs.colima
    pkgs.docker
    pkgs.lazydocker
    pkgs.google-cloud-sdk
    pkgs.pnpm
    pkgs.spotify
    pkgs.ripgrep
    pkgs.uv
    pkgs.wezterm
    pkgs.yazi
  ];
}
