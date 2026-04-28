{
  config,
  pkgs,
  lib,
  helpers,
  dotfilesDir,
  ...
}:
let
  homeDir = config.home.homeDirectory;
  codexHomeDir = "${homeDir}/.codex";
  codexDotfilesDir = "${dotfilesDir}/codex";
  codexConfigPath = "${codexDotfilesDir}/config.toml";
in
{
  home.packages = [ pkgs.llm-agents.codex ];

  home.sessionVariables = {
    CODEX_HOME = codexHomeDir;
  };

  home.activation.linkCodexSettings = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
    ${helpers.activation.mkLinkForce}
    link_force "${codexConfigPath}" "${codexHomeDir}/config.toml"
    link_force "${codexDotfilesDir}/AGENTS.md" "${codexHomeDir}/AGENTS.md"
  '';
}
