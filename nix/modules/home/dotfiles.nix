{ lib, config, dotfilesDir ? "${config.home.homeDirectory}/dotfiles", helpers, ... }:
let
  configHome = config.xdg.configHome;
  homeDir = config.home.homeDirectory;
in
{
  home.activation.linkDotfiles = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
    ${helpers.activation.mkLinkForce}

    link_force "${dotfilesDir}/wezterm" "${configHome}/wezterm"
    link_force "${dotfilesDir}/karabiner" "${configHome}/karabiner"
    link_force "${dotfilesDir}/zsh/zshenv" "${homeDir}/.zshenv"
    link_force "${dotfilesDir}/zsh/zshrc" "${homeDir}/.zshrc"
    link_force "${dotfilesDir}/bash/.bash_profile" "${homeDir}/.bash_profile"
    link_force "${dotfilesDir}/bash/.bashrc" "${homeDir}/.bashrc"
  '';
}
