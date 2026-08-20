{
  config,
  dotfilesDir,
  ...
}:
let
  recorder = "${config.home.homeDirectory}/.local/bin/agent-observability-record";
in
{
  home = {
    sessionVariables.AGENT_OBSERVABILITY_RECORDER = recorder;
    file = {
      ".local/bin/agent-observability-record".source =
        config.lib.file.mkOutOfStoreSymlink "${dotfilesDir}/agent-observability/record-event.py";
      ".local/bin/agent-observability-report".source =
        config.lib.file.mkOutOfStoreSymlink "${dotfilesDir}/agent-observability/generate-report.py";
      ".local/bin/agent-observability-eval".source =
        config.lib.file.mkOutOfStoreSymlink "${dotfilesDir}/agent-observability/evaluate-skill.py";
      ".local/bin/agent-observability-audit-evals".source =
        config.lib.file.mkOutOfStoreSymlink "${dotfilesDir}/agent-observability/audit-evals.py";
    };
  };
}
