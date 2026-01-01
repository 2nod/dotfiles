{ lib, ... }:
{
  mkLinkForce = ''
    link_force() {
      src="$1"
      dest="$2"

      $DRY_RUN_CMD mkdir -p "$(dirname "$dest")"
      if [ -e "$dest" ] || [ -L "$dest" ]; then
        $DRY_RUN_CMD rm -rf -- "$dest"
      fi
      $DRY_RUN_CMD ln -s "$src" "$dest"
    }
  '';
}
