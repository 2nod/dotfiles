{
  config,
  lib,
  pkgs,
  profile ? { },
  ...
}:
let
  colima = profile.colima or null;
  colimaConfigDir = "${config.home.homeDirectory}/.config/colima/default";
  colimaConfig = "${colimaConfigDir}/colima.yaml";
in
lib.mkIf (colima != null) {
  home.activation.syncColimaConfig = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
    $DRY_RUN_CMD mkdir -p "${colimaConfigDir}"
    if [ -f "${colimaConfig}" ]; then
      $DRY_RUN_CMD ${pkgs.perl}/bin/perl -0pi -e 's/^cpu: .*/cpu: ${toString colima.cpu}/m; s/^memory: .*/memory: ${toString colima.memory}/m' "${colimaConfig}"
    else
      $DRY_RUN_CMD cat > "${colimaConfig}" <<'EOF'
# Managed by nix/modules/profiles/work-colima.nix
cpu: ${toString colima.cpu}
memory: ${toString colima.memory}
EOF
    fi
  '';
}
