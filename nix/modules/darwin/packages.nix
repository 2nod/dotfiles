{ pkgs, ... }:
let
  brewCasks = pkgs.brewCasks;
in
{
  # macOS-only packages and brew-nix casks live here (home-manager).
  home.packages = [
    # Add Homebrew casks via brew-nix, for example:
    brewCasks.arc
    brewCasks.bitwarden
    brewCasks.cursor
    brewCasks.discord
    brewCasks.nani
    brewCasks.notion
    brewCasks.raycast
    brewCasks.slack
    brewCasks.visual-studio-code
    brewCasks.zoom
  ]
  ++ [
    # Examples from brew-nix notes:
    # tar.gz cask needs a custom unpackPhase
    # (brewCasks.alfred.overrideAttrs (o: {
    #   nativeBuildInputs = o.nativeBuildInputs ++ [ pkgs.gnutar ];
    #   unpackPhase = "tar -xvzf $src";
    # }))

    # CLI cask needs a custom installPhase
    # (brewCasks.desktoppr.overrideAttrs (_: {
    #   installPhase = ''
    #     mkdir -p $out/bin
    #     cp ./usr/local/bin/desktoppr $out/bin/
    #   '';
    # }))

    # Missing hash needs a manual fetchurl hash
    # (brewCasks.sensei.overrideAttrs (old: {
    #   src = pkgs.fetchurl {
    #     url = builtins.head old.src.urls;
    #     hash = "sha256-REPLACE_ME";
    #   };
    # }))
  ];
}
