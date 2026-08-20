{
  config,
  pkgs,
  lib,
  dotfilesDir,
  ...
}:
let
  codexHomeDir = "${config.home.homeDirectory}/.codex";
  codexXdgDir = "${config.xdg.configHome}/codex";
  codexDotfilesDir = "${dotfilesDir}/codex";

  # agmsg hardcodes this path for its SQLite store, team registry, and run state.
  agmsgSkillDir = "${config.home.homeDirectory}/.agents/skills/agmsg";

  tomlFormat = pkgs.formats.toml { };
  jsonFormat = pkgs.formats.json { };
  observabilityCommand = "${pkgs.python3}/bin/python3 ${codexHomeDir}/skill-observability.py";
  observabilityHook = [
    {
      hooks = [
        {
          type = "command";
          command = observabilityCommand;
          timeout = 2;
        }
      ];
    }
  ];

  appHooks = {
    hooks = {
      SessionStart = [
        {
          hooks = [
            {
              type = "command";
              command = "bash '${codexHomeDir}/herdr-agent-state.sh' session";
              timeout = 10;
            }
            {
              type = "command";
              command = observabilityCommand;
              timeout = 2;
            }
          ];
        }
      ];
      UserPromptSubmit = observabilityHook;
      PreToolUse = observabilityHook;
      PostToolUse = observabilityHook;
      Stop = observabilityHook;
      SessionEnd = observabilityHook;
    };
  };

  settings = {
    model = "gpt-5.5";
    approval_policy = "on-request";
    approvals_reviewer = "auto_review";
    allow_login_shell = true;
    model_reasoning_effort = "high";
    web_search_request = true;
    personality = "pragmatic";
    service_tier = "standard";
    project_doc_fallback_filenames = [ "CLAUDE.md" ];

    shell_environment_policy = {
      "inherit" = "all";
      experimental_use_profile = true;
    };

    # agmsg writes outside the workspace, which the default workspace-write
    # sandbox blocks. Its own installer patches this file, but writeCodexConfig
    # below regenerates config.toml on every activation, so declare it here.
    sandbox_workspace_write.writable_roots = [
      "${agmsgSkillDir}/db"
      "${agmsgSkillDir}/teams"
      "${agmsgSkillDir}/run"
    ];

    features = {
      goals = true;
      js_repl = true;
      multi_agent = true;
      terminal_resize_reflow = true;
    };

    notice.fast_default_opt_out = false;

    plugins."github@openai-curated" = {
      enabled = true;
    };
  };
in
{
  launchd.agents.codex-home = lib.mkIf pkgs.stdenv.hostPlatform.isDarwin {
    enable = true;
    config = {
      ProgramArguments = [
        "/bin/launchctl"
        "setenv"
        "CODEX_HOME"
        codexHomeDir
      ];
      RunAtLoad = true;
    };
  };

  home = {
    packages = [ pkgs.llm-agents.codex ];

    sessionVariables = {
      CODEX_HOME = codexHomeDir;
    };

    activation.linkCodexXdgDir = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      if [ -e "${codexXdgDir}" ] && [ ! -L "${codexXdgDir}" ]; then
        backup="${codexXdgDir}.legacy-$(date +%Y%m%d-%H%M%S)"
        echo "Moving legacy ${codexXdgDir} to $backup" >&2
        mv "${codexXdgDir}" "$backup"
      fi

      mkdir -p "${codexHomeDir}" "$(dirname "${codexXdgDir}")"
      ln -sfn "${codexHomeDir}" "${codexXdgDir}"
    '';

    # User skills live in ~/.agents/skills (experimental_use_profile). Keep only Codex system skills here.
    activation.pruneCodexUserSkills = lib.hm.dag.entryAfter [ "linkCodexXdgDir" ] ''
      skillsDir="${codexHomeDir}/skills"
      if [ ! -d "$skillsDir" ]; then
        exit 0
      fi

      for item in "$skillsDir"/*; do
        [ -e "$item" ] || continue
        base=$(basename "$item")
        if [ "$base" = ".system" ]; then
          continue
        fi
        echo "Removing legacy Codex user skill path $item" >&2
        rm -rf "$item"
      done
    '';

    activation.writeCodexConfig = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      mkdir -p "${codexHomeDir}"
      cp --no-preserve=mode,ownership ${tomlFormat.generate "codex-config" settings} "${codexHomeDir}/config.toml"
      chmod 644 "${codexHomeDir}/config.toml"
    '';

    file = {
      "${codexHomeDir}/AGENTS.md".source =
        config.lib.file.mkOutOfStoreSymlink "${codexDotfilesDir}/AGENTS.md";
      "${codexHomeDir}/skill-observability.py".source =
        config.lib.file.mkOutOfStoreSymlink "${codexDotfilesDir}/skill-observability.py";
      "${codexHomeDir}/hooks.json" = {
        source = jsonFormat.generate "codex-hooks" appHooks;
        force = true;
      };
    };
  };
}
