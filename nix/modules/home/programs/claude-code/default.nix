{
  config,
  lib,
  pkgs,
  helpers,
  dotfilesDir,
  ...
}:
let
  homeDir = config.home.homeDirectory;
  claudeDotfilesDir = "${dotfilesDir}/claude";
in
{
  home.packages = [ pkgs.claude-code ];

  home.activation.linkClaudeCodeSettings = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
    ${helpers.activation.mkLinkForce}
    $DRY_RUN_CMD mkdir -p "${homeDir}/.claude"
    link_force "${claudeDotfilesDir}/settings.json" "${homeDir}/.claude/settings.json"
  '';
}
