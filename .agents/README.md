# Shared Agent Skills

This repository keeps reusable agent skills under `.agents/skills` and installed third-party skills under `.agents/installed-skills`.

## Discovery

Available skills are stored under `.agents/skills` or `.agents/installed-skills`, grouped by category like `software-development/<skill-name>`. Each skill must include a `SKILL.md` file with frontmatter:

- `name`: the skill name users can invoke.
- `description`: the primary trigger signal for when to use the skill.

## Usage

When a user names a skill, or when the task clearly matches a skill description:

1. Open the matching `.agents/skills/<category>/<skill-name>/SKILL.md`, `.agents/installed-skills/<category>/<skill-name>/SKILL.md`, or legacy flat `.agents/skills/<skill-name>/SKILL.md`.
2. Follow only the instructions needed for the current task.
3. If the skill references extra files, load only the directly relevant files.
4. If the skill cannot be applied cleanly, state the issue briefly and continue with the best fallback.

Do not carry a skill across turns unless the user names it again or the new task clearly matches the skill description.

## Listing Skills

This README does not keep a hand-written list of every skill.
Use the `SKILL.md` files as the source of truth:

```sh
find .agents/skills .agents/installed-skills -mindepth 2 -maxdepth 4 -name SKILL.md -print
```

## Public Targets

The path exposed to agents is the public target. Keep targets category-based and unique across authored and installed skills.

- Use `.agents/skills/...` for skills authored in this repository.
- Use `.agents/installed-skills/...` for installed third-party skills.
- Expose both through the same public namespace, such as `planning/grill-me` or `software-development/pr-review-fix-workflow`.
- Do not expose `installed-skills` in the public target. Agent-facing paths should describe the task domain, not the source of the skill.
- Do not reuse the same public target in `.agents/skills` and `.agents/installed-skills`. Home Manager activation checks for target collisions before linking.
- When adding a skill, check both source roots before choosing a public path.

## Adding a Skill

1. Create or install the skill directory.

   For skills authored in this repository:

   ```sh
   mkdir -p .agents/skills/<category>/<skill-name>
   ```

   For installed third-party skills, use the wrapper so the skill is installed under `.agents/installed-skills`:

   ```sh
   .agents/bin/install-skill \
     --target <category>/<skill-name> \
     --repo <owner>/<repo> \
     --path <path/to/skill>
   ```

   Keep installed skills as close to upstream as possible. Do not split, summarize, or rewrite the upstream `SKILL.md` unless there is a clear reason and the local change is documented. Add source information in `SOURCE.md`.

2. For authored skills, add `SKILL.md`:

   ```md
   ---
   name: <skill-name>
   description: When to use this skill.
   ---

   Instructions for the agent.
   ```

3. To make the skill available immediately, link it under each agent's skills directory:

   ```sh
   mkdir -p "$HOME/.codex/skills/<category>" "$HOME/.cursor/skills/<category>" "$HOME/.claude/skills/<category>"
   ln -s "$PWD/.agents/skills/<category>/<skill-name>" "$HOME/.codex/skills/<category>/<skill-name>"
   ln -s "$PWD/.agents/skills/<category>/<skill-name>" "$HOME/.cursor/skills/<category>/<skill-name>"
   ln -s "$PWD/.agents/skills/<category>/<skill-name>" "$HOME/.claude/skills/<category>/<skill-name>"
   ```

4. Home Manager links any directory under `.agents/skills` or `.agents/installed-skills` that contains a `SKILL.md` file. No per-skill Nix entry is required for persistent setup.

5. Restart the relevant agent so it reloads available skills and instructions.

## Current Links

Do not maintain a hand-written list of current skill links.
Check the live links when needed:

```sh
find -L "$HOME/.codex/skills" "$HOME/.cursor/skills" "$HOME/.claude/skills" -maxdepth 4 -name SKILL.md -print
```
