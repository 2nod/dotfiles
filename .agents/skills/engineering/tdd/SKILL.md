---
name: tdd
description: Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions red-green-refactor, or wants integration tests.
metadata:
  tags: [wrapper, upstream, testing]
  wraps: engineering/tdd
---

# TDD Wrapper

Read `.agents/installed-skills/engineering/tdd/SKILL.md`, then apply it through this local wrapper.

- Keep the first test focused on the public behavior being changed.
- Run the red test before implementation when feasible.
- Let refactoring follow a green test, and keep unrelated cleanup out of the patch.
