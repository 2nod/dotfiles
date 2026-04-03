{
  config,
  lib,
  pkgs,
  profile ? { },
  ...
}:
let
  profileColima = profile.colima or null;
  colima = {
    cpu = (profileColima.cpu or 2);
    memory = (profileColima.memory or 8);
    vmType = (profileColima.vmType or "vz");
    rosetta = (profileColima.rosetta or true);
  };
  colimaConfigDir = "${config.home.homeDirectory}/.config/colima/default";
  colimaConfig = "${colimaConfigDir}/colima.yaml";
in
lib.mkIf (profileColima != null) {
  home.activation.syncColimaConfig = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
    $DRY_RUN_CMD mkdir -p "${colimaConfigDir}"
    if [ -f "${colimaConfig}" ]; then
      $DRY_RUN_CMD ${pkgs.perl}/bin/perl -0pi -e '
        s/^cpu: .*/cpu: ${toString colima.cpu}/m;
        s/^memory: .*/memory: ${toString colima.memory}/m;
        s/^vmType: .*/vmType: ${colima.vmType}/m;
        s/^rosetta: .*/rosetta: ${lib.boolToString colima.rosetta}/m;
      ' "${colimaConfig}"
    else
      $DRY_RUN_CMD cat > "${colimaConfig}" <<'EOF'
# Managed by nix home-manager (colima module)
cpu: ${toString colima.cpu}
memory: ${toString colima.memory}
vmType: ${colima.vmType}
rosetta: ${lib.boolToString colima.rosetta}
EOF
    fi
  '';
}
