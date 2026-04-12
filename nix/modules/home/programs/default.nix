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
    (import ./git {
      inherit
        pkgs
        lib
        config
        ;
    })
    (import ./direnv {
      inherit
        pkgs
        lib
        config
        ;
    })
    (import ./neovim {
      inherit
        pkgs
        lib
        config
        dotfilesDir
        ;
    })
    (import ./fish {
      inherit
        pkgs
        lib
        ;
    })
    (import ./vscode {
      inherit
        pkgs
        lib
        config
        dotfilesDir
        ;
    })
    (import ./cursor {
      inherit
        pkgs
        lib
        config
        dotfilesDir
        ;
    })
    (import ./codex {
      inherit
        pkgs
        lib
        config
        dotfilesDir
        ;
    })
    ./delta.nix
    (import ./ghostty {
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
    (import ./cmux {
      inherit pkgs;
    })
    (import ./colima {
      inherit
        pkgs
        lib
        config
        profile
        ;
    })
  ];
}
