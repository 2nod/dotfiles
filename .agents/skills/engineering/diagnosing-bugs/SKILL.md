---
name: diagnosing-bugs
description: Diagnosis loop for hard bugs and performance regressions. Use when the user says "diagnose"/"debug this", or reports something broken, throwing, failing, slow, or flaky.
metadata:
  tags: [wrapper, upstream, debugging]
  wraps: engineering/diagnosing-bugs
---

# Diagnosing Bugs Wrapper

Read `.agents/installed-skills/engineering/diagnosing-bugs/SKILL.md`, then apply it through this local wrapper.

- Build or identify a red-capable feedback loop before settling on a cause.
- Keep temporary instrumentation scoped and remove it unless the user asks to keep it.
- Report the exact command used for the verification loop.
