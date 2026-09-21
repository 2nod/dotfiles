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
  vscodeUserDir =
    if pkgs.stdenv.hostPlatform.isDarwin then
      "${config.home.homeDirectory}/Library/Application Support/Code/User"
    else
      "${config.xdg.configHome}/Code/User";
  vscodeSettings = jsonFormat.generate "vscode-settings.json" shared.userSettings;
  vscodeKeybindings = jsonFormat.generate "vscode-keybindings.json" shared.keybindings;
  leanExtensions = with pkgs.vscode-extensions; [
    leanprover.lean4
    tamasfe.even-better-toml
  ];
in
{
  # VS Code itself stays Homebrew-managed. Manage only these extension links,
  # preserving the other extensions and the existing settings/keybindings.
  home.file = builtins.listToAttrs (
    map (extension: {
      name = ".vscode/extensions/${extension.vscodeExtUniqueId}";
      value = {
        source = "${extension}/share/vscode/extensions/${extension.vscodeExtUniqueId}";
        # Like programs.vscode's mutable-extension support, invalidate the index
        # so VS Code discovers both the new links and manually installed extensions.
        onChange = ''
          run rm -f "$HOME/.vscode/extensions/extensions.json" \
            "$HOME/.vscode/extensions/.init-default-profile-extensions"
        '';
      };
    }) leanExtensions
  );

  home.activation.linkVscodeConfig = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
    ${helpers.activation.mkLinkForce}
    link_force "${vscodeSettings}" "${vscodeUserDir}/settings.json"
    link_force "${vscodeKeybindings}" "${vscodeUserDir}/keybindings.json"
  '';
}
