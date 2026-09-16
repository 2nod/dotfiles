{ pkgs, ... }:
let
  gemini = pkgs.writeShellScriptBin "gemini" ''
    if [ "''${1:-}" = "--acp" ]; then
      shift
      exec ${pkgs.gemini-cli}/bin/gemini --experimental-acp "$@"
    fi
    exec ${pkgs.gemini-cli}/bin/gemini "$@"
  '';
in
{
  home.packages = [
    gemini
    pkgs.llm-agents.cursor-agent
    pkgs.llm-agents.opencode
    pkgs.llm-agents.pi
  ];
}
