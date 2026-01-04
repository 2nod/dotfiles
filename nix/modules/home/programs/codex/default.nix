{ config, pkgs, dotfilesDir, ... }:
let
  homeDir = config.home.homeDirectory;
  codexConfigDir = "${config.xdg.configHome}/codex";
  codexDotfilesDir = "${dotfilesDir}/codex";
  tomlFormat = pkgs.formats.toml { };
  settings = {
    model = "gpt-5.2-codex";
    approval_policy = "never";
    sandbox_mode = "danger-full-access";
    network_access = "restricted";
    model_reasoning_effort = "xhigh";
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
in
{
  home.sessionVariables = {
    CODEX_HOME = codexConfigDir;
  };

  home.file = {
    "${codexConfigDir}/config.toml" = {
      source = tomlFormat.generate "codex-config" settings;
      force = true;
    };
    "${codexConfigDir}/AGENTS.md".source =
      config.lib.file.mkOutOfStoreSymlink "${codexDotfilesDir}/AGENTS.md";
  };
}
