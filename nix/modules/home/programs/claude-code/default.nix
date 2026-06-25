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
  agentSkills = import ../agent-skills.nix { inherit lib dotfilesDir; };
in
{
  home.packages = [ pkgs.claude-code ];

  home.activation.linkClaudeCodeSettings = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
    ${helpers.activation.mkLinkForce}
    $DRY_RUN_CMD mkdir -p "${homeDir}/.claude"
    link_force "${claudeDotfilesDir}/settings.json" "${homeDir}/.claude/settings.json"
    link_force "${claudeDotfilesDir}/CLAUDE.md" "${homeDir}/.claude/CLAUDE.md"
    ${agentSkills.linkCommands "${homeDir}/.claude/skills"}
  '';
}
