{ pkgs, ... }:
{
  # Generic CLI packages that don't have a dedicated programs/<tool>/ module.
  # Tool-specific packages live alongside their config in programs/<tool>/default.nix.
  home.packages = [
    pkgs.bat
    pkgs.bun
    pkgs.mise
    pkgs.deno
    pkgs.eza
    pkgs.fzf
    pkgs.gh
    pkgs.ghq
    pkgs.lazygit
    pkgs.colima
    pkgs.docker
    pkgs.lazydocker
    pkgs.google-cloud-sdk
    pkgs.pnpm
    pkgs.spotify
    pkgs.ripgrep
    pkgs.roots
    pkgs.uv
    pkgs.wezterm
    pkgs.yazi
    pkgs.zoxide
  ];
}
