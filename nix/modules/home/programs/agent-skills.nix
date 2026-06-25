{ dotfilesDir, ... }:
{
  linkCommands =
    targetSkillsDir:
    ''
      link_agent_skills_root() {
        local source_root="$1"
        local target_root="$2"

        [ -d "$source_root" ] || return 0

        while IFS= read -r skill_file; do
          local source_dir
          local relative_path
          local target_path
          local target_dir

          source_dir="$(dirname "$skill_file")"
          relative_path="''${source_dir#"$source_root"/}"
          target_path="$target_root/$relative_path"
          target_dir="$(dirname "$target_path")"

          if [ -e "$target_path" ] && [ "$(readlink "$target_path" || true)" != "$source_dir" ]; then
            echo "agent skill target collision: $target_path" >&2
            echo "  existing: $(readlink "$target_path" || echo "$target_path")" >&2
            echo "  new:      $source_dir" >&2
            exit 1
          fi

          $DRY_RUN_CMD mkdir -p "$target_dir"
          link_force "$source_dir" "$target_path"
        done < <(find "$source_root" -mindepth 2 -maxdepth 3 -name SKILL.md -type f | sort)
      }

      link_agent_skills_root "${dotfilesDir}/.agents/skills" "${targetSkillsDir}"
      link_agent_skills_root "${dotfilesDir}/.agents/installed-skills" "${targetSkillsDir}"
    '';
}
