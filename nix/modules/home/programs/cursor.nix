{
  config,
  pkgs,
  lib,
  dotfilesDir,
  ...
}:
let
  helpers = import ../../lib/helpers { inherit lib; };
  jsonFormat = pkgs.formats.json { };
  shared = import ./code-shared.nix { inherit config; };
  userSettings = shared.userSettings;
  keybindings = shared.keybindings;
  cursorUserDir =
    if pkgs.stdenv.hostPlatform.isDarwin then
      "${config.home.homeDirectory}/Library/Application Support/Cursor/User"
    else
      "${config.xdg.configHome}/Cursor/User";
  cursorHomeDir = "${config.home.homeDirectory}/.cursor";
  cursorSettings = jsonFormat.generate "cursor-settings.json" userSettings;
  cursorKeybindings = jsonFormat.generate "cursor-keybindings.json" keybindings;
  agentSkills = import ./agent-skills.nix { inherit lib dotfilesDir; };
in
{
  home.activation.linkCursorConfig = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
    ${helpers.activation.mkLinkForce}
    link_force "${cursorSettings}" "${cursorUserDir}/settings.json"
    link_force "${cursorKeybindings}" "${cursorUserDir}/keybindings.json"
    ${agentSkills.linkCommands "${cursorHomeDir}/skills"}
  '';
}
