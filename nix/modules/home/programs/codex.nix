{
  config,
  pkgs,
  lib,
  dotfilesDir,
  ...
}:
let
  homeDir = config.home.homeDirectory;
  codexConfigDir = "${config.xdg.configHome}/codex";
  codexDotfilesDir = "${dotfilesDir}/codex";
  tomlFormat = pkgs.formats.toml { };
  settings = {
    model = "gpt-5.4-mini";
    approval_policy = "never";
    sandbox_mode = "danger-full-access";
    network_access = "restricted";
    model_reasoning_effort = "high";
    web_search_request = true;

    notice = {
      hide_gpt5_1_migration_prompt = true;
      "hide_gpt-5.1-codex-max_migration_prompt" = true;
    };

    projects = {
      "${homeDir}" = {
        trust_level = "trusted";
      };
    };
  };
  codexConfig = tomlFormat.generate "codex-config" settings;
in
{
  home.packages = [ pkgs.llm-agents.codex ];

  home.sessionVariables = {
    CODEX_HOME = codexConfigDir;
  };

  home.activation.writeCodexConfig = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
    $DRY_RUN_CMD mkdir -p "${codexConfigDir}"
    if [ -e "${codexConfigDir}/config.toml" ] || [ -L "${codexConfigDir}/config.toml" ]; then
      $DRY_RUN_CMD rm -f -- "${codexConfigDir}/config.toml"
    fi
    $DRY_RUN_CMD install -m 0644 "${codexConfig}" "${codexConfigDir}/config.toml"
  '';

  home.file = {
    "${codexConfigDir}/AGENTS.md".source =
      config.lib.file.mkOutOfStoreSymlink "${codexDotfilesDir}/AGENTS.md";
  };
}
