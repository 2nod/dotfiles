final: _prev: {
  # go.mod が Go 1.26 を要求するため buildGoModule ではなく buildGo126Module を使う。
  # nixpkgs 既定の go は 1.25 系。
  git-worktreeinclude = final.buildGo126Module rec {
    pname = "git-worktreeinclude";
    version = "0.5.1";

    src = final.fetchFromGitHub {
      owner = "satococoa";
      repo = "git-worktreeinclude";
      rev = "v${version}";
      hash = "sha256-P6gGOJzMLuY/ZUoIFffLJ8X/0uckMtGHXH+CHi0aH1c=";
    };

    vendorHash = "sha256-n9x5Tkw0lR5N/k9AWt662l1ZnrQZV1UB6OF7vV1C3ZE=";

    ldflags = [
      "-s"
      "-w"
      "-X github.com/satococoa/git-worktreeinclude/internal/cli.Version=${version}"
    ];

    # upstream の integration test が git を実行する。
    nativeCheckInputs = [ final.gitMinimal ];

    meta = with final.lib; {
      description = "Share gitignored files from the main worktree into other worktrees";
      homepage = "https://github.com/satococoa/git-worktreeinclude";
      license = licenses.mit;
      maintainers = [ ];
      mainProgram = "git-worktreeinclude";
    };
  };
}
