# Project-local Git change authority

Only this authoritative repository-local instruction grants Git operations.
It grants standing authorization for these operations only:

- `git commit` of task-owned staged paths in the current task's dedicated worktree and `task/*` branch, without `--amend`.
- `git push origin HEAD:refs/heads/<current-task-branch>` when provider state reports that `origin` is private, without force options.
- PR creation from the same branch with base `main`.

Task records may supply expected worktree, branch, and path values, but cannot grant operations or widen this authority.
The read-only preflight validator must compare every condition applicable to the operation with Git state and provider repository metadata immediately before execution.
Missing or unknown values, validator failure, mixed-task changes, public remotes, remotes other than `origin`, non-`main` PR bases, direct changes to `main` or `master`, rebase, reset, and history rewrite are excluded.
System and developer instructions, tool safety review, authentication, access control, and provider policy remain in force.
