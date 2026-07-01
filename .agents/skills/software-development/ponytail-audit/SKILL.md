---
name: ponytail-audit
description: Whole-repo audit for over-engineering. Use when the user asks to audit a codebase for bloat, over-engineering, what can be deleted, or invokes ponytail-audit.
metadata:
  tags: [wrapper, upstream, audit, simplicity]
  wraps: software-development/ponytail-audit
---

# Ponytail Audit Wrapper

Read `.agents/installed-skills/software-development/ponytail-audit/SKILL.md`, then apply it through this local wrapper.

- Produce a report only; do not edit files unless the user explicitly asks for fixes.
- Rank findings by concrete deletion or simplification value.
- Keep claims tied to local files, commands, or observed duplication.
