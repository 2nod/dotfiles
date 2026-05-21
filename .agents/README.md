# Shared Agent Skills

This repository keeps reusable agent skills under `.agents/skills`.

## Discovery

Available skills are directories under `.agents/skills`. Each skill must include a `SKILL.md` file with frontmatter:

- `name`: the skill name users can invoke.
- `description`: the primary trigger signal for when to use the skill.

## Usage

When a user names a skill, or when the task clearly matches a skill description:

1. Open the matching `.agents/skills/<skill-name>/SKILL.md`.
2. Follow only the instructions needed for the current task.
3. If the skill references extra files, load only the directly relevant files.
4. If the skill cannot be applied cleanly, state the issue briefly and continue with the best fallback.

Do not carry a skill across turns unless the user names it again or the new task clearly matches the skill description.

## Installed Skills

- `grill-me`: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree.

## Adding a Skill

1. Create the skill directory:

   ```sh
   mkdir -p .agents/skills/<skill-name>
   ```

2. Add `.agents/skills/<skill-name>/SKILL.md`:

   ```md
   ---
   name: <skill-name>
   description: When to use this skill.
   ---

   Instructions for the agent.
   ```

3. Add the skill to the installed skills list in this file.

4. Make the skill available to Codex and Cursor Agent:

   ```sh
   mkdir -p ~/.codex/skills ~/.cursor/skills
   ln -s "$PWD/.agents/skills/<skill-name>" "$HOME/.codex/skills/<skill-name>"
   ln -s "$PWD/.agents/skills/<skill-name>" "$HOME/.cursor/skills/<skill-name>"
   ```

5. Add persistent links in Home Manager:

   - `nix/modules/home/programs/codex.nix`
   - `nix/modules/home/programs/cursor.nix`

6. Add a one-line entry to `claude/CLAUDE.md` so Claude knows when to open the skill.

7. Restart the relevant agent so it reloads available skills and instructions.

## Current Links

- `~/.codex/AGENTS.md` links to `codex/AGENTS.md`.
- `~/.claude/CLAUDE.md` links to `claude/CLAUDE.md`.
- `~/.codex/skills/grill-me` links to `.agents/skills/grill-me`.
- `~/.cursor/skills/grill-me` links to `.agents/skills/grill-me`.
