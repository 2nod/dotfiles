# Agent skills configuration
# https://github.com/Kyure-A/agent-skills-nix
#
# Authoring lives in .agents/skills; agent-skills-nix deploys the same bundle
# to each agent's runtime skills directory.
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
    };

    skills.enableAll = [ "local" ];

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
