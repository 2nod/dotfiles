{ lib, config, dotfilesDir ? "${config.home.homeDirectory}/dotfiles", helpers, ... }:
let
  configHome = config.xdg.configHome;
in
{
  xdg.enable = true;

  home.activation.linkDotfiles = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
    ${helpers.activation.mkLinkForce}

    link_force "${dotfilesDir}/wezterm" "${configHome}/wezterm"
    link_force "${dotfilesDir}/nvim" "${configHome}/nvim"
    link_force "${dotfilesDir}/karabiner" "${configHome}/karabiner"
  '';
}
