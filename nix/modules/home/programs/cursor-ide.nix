{
  config,
  pkgs,
  lib,
  ...
}:
let
  helpers = import ../../lib/helpers { inherit lib; };
  jsonFormat = pkgs.formats.json { };
  shared = import ./code-shared.nix { inherit config; };
  cursorUserDir =
    if pkgs.stdenv.hostPlatform.isDarwin then
      "${config.home.homeDirectory}/Library/Application Support/Cursor/User"
    else
      "${config.xdg.configHome}/Cursor/User";
  cursorSettings = jsonFormat.generate "cursor-settings.json" shared.userSettings;
  cursorKeybindings = jsonFormat.generate "cursor-keybindings.json" shared.keybindings;
in
{
  home.activation.linkCursorIdeConfig = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
    ${helpers.activation.mkLinkForce}
    link_force "${cursorSettings}" "${cursorUserDir}/settings.json"
    link_force "${cursorKeybindings}" "${cursorUserDir}/keybindings.json"
  '';
}
