{
  pkgs,
  lib,
  config,
  helpers,
  ...
}:
let
  ghosttySettings = {
    font-family = "UDEV Gothic 35LG";
    font-size = 13;
    font-feature = [ "-dlig" ];

    background-opacity = 0.70;
    background-blur-radius = 20;

    theme = "Kanagawa Dragon";

    shell-integration = "fish";
    shell-integration-features = "no-cursor";

    cursor-style = "block";
    cursor-style-blink = false;

    mouse-hide-while-typing = true;

    working-directory = "inherit";
  };

  ghosttyConfigText = lib.concatStringsSep "\n" (
    lib.mapAttrsToList (
      name: value:
      if builtins.isList value then
        lib.concatMapStringsSep "\n" (v: "${name} = ${toString v}") value
      else if builtins.isBool value then
        "${name} = ${if value then "true" else "false"}"
      else
        "${name} = ${toString value}"
    ) ghosttySettings
  );
in
{
  programs.ghostty = lib.mkIf (!pkgs.stdenv.isDarwin) {
    enable = true;
    package = pkgs.ghostty;
    enableFishIntegration = true;
    settings = ghosttySettings;
  };

  xdg.configFile."ghostty/config" = lib.mkIf pkgs.stdenv.isDarwin {
    text = ghosttyConfigText;
  };

  home.activation.linkGhosttyConfig = lib.mkIf pkgs.stdenv.isDarwin (
    lib.hm.dag.entryAfter [ "linkGeneration" ] ''
      ${helpers.activation.mkLinkForce}
      link_force "${config.xdg.configHome}/ghostty/config" "${config.home.homeDirectory}/Library/Application Support/com.mitchellh.ghostty/config"
    ''
  );
}
