{
  pkgs,
  lib,
  config,
  helpers,
  profile ? { },
  dotfilesDir,
  ...
}:
{
  imports = [
    ./ai-tools.nix
    (import ./git {
      inherit
        pkgs
        lib
        config
        ;
    })
    (import ./direnv.nix {
      inherit
        pkgs
        lib
        config
        ;
    })
    (import ./neovim.nix {
      inherit
        pkgs
        lib
        config
        dotfilesDir
        ;
    })
    (import ./fish.nix {
      inherit
        pkgs
        lib
        ;
    })
    (import ./vscode.nix {
      inherit
        pkgs
        lib
        config
        dotfilesDir
        ;
    })
    (import ./cursor.nix {
      inherit
        pkgs
        lib
        config
        dotfilesDir
        ;
    })
    (import ./codex.nix {
      inherit
        pkgs
        lib
        config
        dotfilesDir
        ;
    })
    (import ./claude-code {
      inherit
        pkgs
        lib
        config
        helpers
        dotfilesDir
        ;
    })
    ./delta.nix
    (import ./ghostty.nix {
      inherit
        pkgs
        lib
        config
        helpers
        ;
    })
    (import ./lazygit {
      inherit
        pkgs
        lib
        ;
    })
    (import ./cmux.nix {
      inherit pkgs;
    })
    (import ./colima.nix {
      inherit
        pkgs
        lib
        config
        profile
        ;
    })
  ];
}
