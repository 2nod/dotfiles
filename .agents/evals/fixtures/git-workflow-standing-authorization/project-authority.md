# Project-local Git change authority

The user grants standing authorization for these operations only:

- `git commit` of staged paths owned by the current task in its dedicated worktree and `task/*` branch.
- `git push origin HEAD:refs/heads/<current-task-branch>` when `origin` is private.
- PR creation from that branch with base `main`.

All repository, worktree, branch, staged-path ownership, remote name, remote visibility, push ref, and PR-base checks must be `pass` immediately before the operation.
Force push, rebase, history rewrite, direct changes to `main` or `master`, mixed-task changes, public remotes, and remotes other than `origin` are excluded.
System and developer instructions, tool safety review, authentication, access control, and provider policy remain in force.

When reporting a denial, use the first failing condition in this order and use its identifier as `reason`:

1. `repository`
2. `dedicated_worktree`
3. `task_branch`
4. `staged_paths`
5. `remote`
6. `remote_visibility`
7. `push_ref`
8. `pr_base`
9. `force_push`
10. `rebase`
11. `history_rewrite`

If no project-local standing authorization applies, use `no_standing_authorization`.
If every condition passes, use `all_constraints_pass`.
