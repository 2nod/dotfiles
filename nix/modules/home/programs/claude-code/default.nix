{
  pkgs,
  lib,
  config,
  dotfilesDir,
  ...
}:
let
  claudeConfigDir = "${config.xdg.configHome}/claude";
  claudeDotfilesDir = "${dotfilesDir}/claude";

  checkJsonschema = lib.getExe pkgs.check-jsonschema;
  jq = lib.getExe pkgs.jq;
  jsonFormat = pkgs.formats.json { };

  settings = {
    "$schema" = "https://json.schemastore.org/claude-code-settings.json";
    permissions = {
      defaultMode = "auto";
      allow = [
        "Bash(jq -r:*)"
      ];
    };
    effortLevel = "high";
    alwaysThinkingEnabled = true;
    skipAutoPermissionPrompt = true;
    skipDangerousModePermissionPrompt = true;
    enabledPlugins = {
      "codex@openai-codex" = true;
    };
    extraKnownMarketplaces = {
      openai-codex = {
        source = {
          source = "github";
          repo = "openai/codex-plugin-cc";
        };
      };
    };
  };
in
{
  launchd.agents.claude-config-dir = lib.mkIf pkgs.stdenv.hostPlatform.isDarwin {
    enable = true;
    config = {
      ProgramArguments = [
        "/bin/launchctl"
        "setenv"
        "CLAUDE_CONFIG_DIR"
        claudeConfigDir
      ];
      RunAtLoad = true;
    };
  };

  home = {
    packages = [ pkgs.claude-code ];

    # Also exported to fish via fish/conf.d/02-hm-session-vars.fish
    sessionVariables = {
      CLAUDE_CONFIG_DIR = claudeConfigDir;
    };

    activation.writeClaudeSettings = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      mkdir -p "${claudeConfigDir}"
      cp --no-preserve=mode,ownership ${jsonFormat.generate "claude-settings.json" settings} "${claudeConfigDir}/settings.json"
      chmod 644 "${claudeConfigDir}/settings.json"
    '';

    activation.validateClaudeSettings = lib.hm.dag.entryAfter [ "writeClaudeSettings" ] ''
      SETTINGS_FILE="${claudeConfigDir}/settings.json"
      SCHEMA_URL=$(${jq} -r '.["$schema"]' "$SETTINGS_FILE")

      echo "Validating Claude Code settings.json..."
      if ${checkJsonschema} --schemafile "$SCHEMA_URL" "$SETTINGS_FILE" 2>&1; then
        echo "Claude Code settings.json validation passed"
      else
        echo "Claude Code settings.json validation failed (non-blocking, schema may be outdated)" >&2
      fi
    '';
  };

  xdg.configFile = {
    "claude/CLAUDE.md".source = config.lib.file.mkOutOfStoreSymlink "${claudeDotfilesDir}/CLAUDE.md";
  };
}
