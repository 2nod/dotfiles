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
    pkgs.git-worktreeinclude
    pkgs.lazygit
    pkgs.colima
    pkgs.docker_29
    pkgs.lazydocker
    pkgs.google-cloud-sdk
    pkgs.pnpm
    pkgs.spotify
    pkgs.starship
    pkgs.rclone
    pkgs.ripgrep
    pkgs.roots
    # stable nixpkgs still ships the old v1 CLI (no `network-volume`/`nv`
    # command group); pkgs.unstable tracks upstream's v2 releases.
    pkgs.unstable.runpodctl
    pkgs.terraform
    pkgs.pyright
    pkgs.ruff
    pkgs.uv
    pkgs.wezterm
    pkgs.wrangler
    pkgs.yazi
    pkgs.zoxide
  ];
}
