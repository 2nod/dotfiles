{ pkgs, lib, config, dotfilesDir, ... }:
{
  imports = [
    (import ./git {
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
  ];
}
