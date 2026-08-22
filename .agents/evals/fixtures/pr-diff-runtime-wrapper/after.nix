{ config, ... }:
let
  installDir = "${config.home.homeDirectory}/.local/share/example-router";
in
{
  # Interactive shells provide Node through a user-managed version manager.
  home.file.".local/bin/example-router".source =
    config.lib.file.mkOutOfStoreSymlink "${installDir}/bin/dispatcher";
}
