{
  pkgs,
  config,
  lib,
  ...
}:
let
  jsonFormat = pkgs.formats.json { };
  pstack = import ./pstack-cursor.nix { inherit pkgs; };

  settings = {
    permissions = {
      allow = [
        "Shell(ls)"
        "Shell(uv)"
        "Shell(git status)"
        "Shell(git diff)"
      ];
      deny = [ ];
    };
    version = 1;
    editor = {
      vimMode = false;
    };
    model = {
      modelId = "composer-2.5-fast";
      displayModelId = "composer-2.5-fast";
      displayName = "Composer 2.5 Fast";
      displayNameShort = "Composer 2.5 Fast";
      aliases = [ ];
    };
    hasChangedDefaultModel = true;
    privacyCache = {
      ghostMode = false;
      privacyMode = 3;
      updatedAt = 1763647036545;
    };
    network = {
      useHttp1ForAgent = false;
    };
  };
in
{
  xdg.configFile."cursor/cli-config.json" = {
    source = jsonFormat.generate "cli-config.json" settings;
    force = true;
  };

  # Cursor skips external symlinks in plugins/local, so deploy a real directory.
  home.activation.installCursorPstack = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    pstackDir="${config.home.homeDirectory}/.cursor/plugins/local/pstack"
    if [ -L "$pstackDir" ] || { [ -e "$pstackDir" ] && [ ! -f "$pstackDir/.dotfiles-managed" ]; }; then
      echo "Refusing to overwrite unmanaged Cursor plugin: $pstackDir" >&2
      exit 1
    fi
    mkdir -p "$pstackDir"
    ${pkgs.rsync}/bin/rsync -r --checksum --delete --chmod=u+w \
      --exclude=.dotfiles-managed ${pstack}/ "$pstackDir/"
    printf '%s\n' '${pstack}' > "$pstackDir/.dotfiles-managed"
  '';
}
