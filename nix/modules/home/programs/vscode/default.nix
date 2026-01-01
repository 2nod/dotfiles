{ config, pkgs, lib, ... }:
let
  helpers = import ../../../lib/helpers { inherit lib; };
  jsonFormat = pkgs.formats.json { };
  shared = import ../code-shared.nix { inherit config; };
  vscodeUserDir =
    if pkgs.stdenv.hostPlatform.isDarwin then
      "${config.home.homeDirectory}/Library/Application Support/Code/User"
    else
      "${config.xdg.configHome}/Code/User";
  vscodeSettings = jsonFormat.generate "vscode-settings.json" shared.userSettings;
  vscodeKeybindings = jsonFormat.generate "vscode-keybindings.json" shared.keybindings;
in
{
  home.activation.linkVscodeConfig = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
    ${helpers.activation.mkLinkForce}
    link_force "${vscodeSettings}" "${vscodeUserDir}/settings.json"
    link_force "${vscodeKeybindings}" "${vscodeUserDir}/keybindings.json"
  '';
}
