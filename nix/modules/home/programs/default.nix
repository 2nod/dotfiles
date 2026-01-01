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
  ];
}
