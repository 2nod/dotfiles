{
  config,
  dotfilesDir,
  pkgs,
  ...
}:
let
  pythonEntry =
    filename:
    pkgs.writeShellScript "agent-observability-${filename}" ''
      exec ${pkgs.python3}/bin/python3 ${pkgs.lib.escapeShellArg "${dotfilesDir}/agent-observability/${filename}"} "$@"
    '';
in
{
  home = {
    file = {
      ".local/bin/agent-observability-report".source = pythonEntry "generate-report.py";
      ".local/bin/agent-observability-eval".source = pythonEntry "evaluate-skill.py";
      ".local/bin/agent-observability-audit-evals".source = pythonEntry "audit-evals.py";
      ".local/bin/agent-observability-analyze-usage".source = pythonEntry "analyze-usage.py";
      ".local/bin/agent-observability-collect".source = pythonEntry "collect-usage.py";
      ".local/bin/agent-observability-doctor".source = pythonEntry "doctor.py";
    };
  };
  launchd.agents.agent-observability-collect = {
    enable = true;
    config = {
      ProgramArguments = [
        "${pkgs.python3}/bin/python3"
        "${dotfilesDir}/agent-observability/collect-usage.py"
        "--once"
      ];
      RunAtLoad = true;
      StartInterval = 60;
      ProcessType = "Background";
      LowPriorityIO = true;
      Umask = 63;
    };
  };
}
