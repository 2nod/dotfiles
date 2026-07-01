# Agent skills configuration
# https://github.com/Kyure-A/agent-skills-nix
#
# Authoring lives in .agents/skills; third-party skills in .agents/installed-skills.
# agent-skills-nix bundles both and deploys to each agent's runtime skills directory.
{
  local-skills,
  ...
}:
{
  programs.agent-skills = {
    enable = true;

    sources = {
      local = {
        path = local-skills;
        subdir = ".agents/skills";
      };
      installed = {
        path = local-skills;
        subdir = ".agents/installed-skills";
      };
    };

    skills.enableAll = [
      "local"
      "installed"
    ];

    targets = {
      agents = {
        dest = ".agents/skills";
        structure = "copy-tree";
      };
      claude = {
        dest = ".config/claude/skills";
        structure = "link";
      };
      cursor = {
        dest = ".cursor/skills";
        structure = "symlink-tree";
      };
    };
  };
}
