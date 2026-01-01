{ config, pkgs, dotfilesDir, ... }:
let
  codexConfigDir = "${config.xdg.configHome}/codex";
  codexDotfilesDir = "${dotfilesDir}/codex";
  tomlFormat = pkgs.formats.toml { };
  bunx = "${pkgs.bun}/bin/bunx";
  settings = {
    model = "gpt-5.2-codex";
    approval_policy = "on-request";
    model_reasoning_effort = "medium";
    web_search_request = true;

    mcp_servers = {
      chrome-devtools = {
        command = bunx;
        enabled = false;
        args = [
          "chrome-devtools-mcp@latest"
        ];
      };

      context7 = {
        startup_timeout_ms = 5000;
        url = "https://mcp.context7.com/mcp";
      };

      deepwiki = {
        startup_timeout_ms = 5000;
        url = "https://mcp.deepwiki.com/mcp";
      };

      figma-dev-mode-mcp-server = {
        startup_timeout_ms = 5000;
        url = "http://127.0.0.1:3845/mcp";
      };
    };

    notice = {
      hide_gpt5_1_migration_prompt = true;
      "hide_gpt-5.1-codex-max_migration_prompt" = true;
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
