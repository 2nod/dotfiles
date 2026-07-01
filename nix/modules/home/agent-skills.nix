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
  config,
  pkgs,
  lib,
  ...
}:
let
  claudeSharedSkillsPlugin = pkgs.runCommand "dotfiles-claude-shared-skills-plugin" { } ''
    set -eu

    mkdir -p "$out/.claude-plugin" "$out/skills"
    cat > "$out/.claude-plugin/plugin.json" <<'EOF'
    {
      "$schema": "https://anthropic.com/claude-code/plugin.schema.json",
      "name": "dotfiles-shared-skills",
      "version": "0.1.0",
      "description": "Shared agent skills managed by tsuno/dotfiles.",
      "author": {
        "name": "tsuno"
      }
    }
    EOF

    cd ${config.programs.agent-skills.bundlePath}
    ${pkgs.findutils}/bin/find -L . -name SKILL.md -type f | sort | while IFS= read -r skill_md; do
      skill_dir="''${skill_md%/SKILL.md}"
      skill_id="''${skill_dir#./}"
      skill_name="''${skill_id##*/}"
      dest="$out/skills/$skill_name"

      if [ -e "$dest" ]; then
        echo "Duplicate Claude skill name: $skill_name" >&2
        echo "Conflicting skill id: $skill_id" >&2
        exit 1
      fi

      ln -s "${config.programs.agent-skills.bundlePath}/$skill_id" "$dest"
    done
  '';
in
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
        # Claude Code loads user skills from plugin directories containing
        # .claude-plugin/plugin.json and skills/<name>/SKILL.md. The generic
        # agent-skills target preserves category/name nesting, so we publish a
        # Claude-specific plugin below instead.
        enable = false;
      };
      cursor = {
        dest = ".cursor/skills";
        structure = "symlink-tree";
      };
    };
  };

  home.file.".config/claude/skills/dotfiles-shared-skills" =
    lib.mkIf config.programs.agent-skills.enable
      {
        source = claudeSharedSkillsPlugin;
        recursive = true;
        force = true;
      };
}
