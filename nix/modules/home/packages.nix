{ pkgs, ... }:
let
  git-worktreeinclude = pkgs.unstable.buildGo126Module rec {
    pname = "git-worktreeinclude";
    version = "0.5.1";

    src = pkgs.fetchFromGitHub {
      owner = "satococoa";
      repo = "git-worktreeinclude";
      rev = "v${version}";
      hash = "sha256-P6gGOJzMLuY/ZUoIFffLJ8X/0uckMtGHXH+CHi0aH1c=";
    };

    vendorHash = "sha256-n9x5Tkw0lR5N/k9AWt662l1ZnrQZV1UB6OF7vV1C3ZE=";
    ldflags = [ "-X github.com/satococoa/git-worktreeinclude/internal/cli.Version=${version}" ];
    nativeCheckInputs = [ pkgs.gitMinimal ];
  };
in
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
    git-worktreeinclude
    pkgs.lazygit
    pkgs.colima
    pkgs.docker_29
    pkgs.lazydocker
    pkgs.google-cloud-sdk
    pkgs.pnpm
    pkgs.spotify
    pkgs.starship
    pkgs.ripgrep
    pkgs.roots
    pkgs.terraform
    pkgs.pyright
    pkgs.ruff
    pkgs.uv
    pkgs.wezterm
    pkgs.yazi
    pkgs.zoxide
  ];
}
