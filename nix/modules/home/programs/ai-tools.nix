{ pkgs, ... }:
{
  # Antigravity CLI is installed via its official installer in ~/.local/bin/agy.
  home.packages = [
    pkgs.llm-agents.cursor-agent
    pkgs.llm-agents.opencode
    pkgs.llm-agents.pi
  ];
}
