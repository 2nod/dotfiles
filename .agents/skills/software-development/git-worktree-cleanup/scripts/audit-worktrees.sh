#!/usr/bin/env bash
set -u

if [ "$#" -eq 0 ]; then
  printf 'usage: %s <root>...\n' "$0" >&2
  exit 2
fi

tmp_repos="$(mktemp)"
trap 'rm -f "$tmp_repos"' EXIT

for root in "$@"; do
  [ -d "$root" ] || continue
  find "$root" \
    \( -path '*/.git' -type d -o -name .git -type f \) \
    -print 2>/dev/null |
    while IFS= read -r git_entry; do
      repo="${git_entry%/.git}"
      if [ -f "$git_entry" ]; then
        repo="$(dirname "$git_entry")"
      fi
      top="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null || true)"
      [ -n "$top" ] && printf '%s\n' "$top"
    done
done | sort -u >"$tmp_repos"

while IFS= read -r repo; do
  [ -n "$repo" ] || continue
  printf 'REPO %s\n' "$repo"

  prune="$(git -C "$repo" worktree prune --dry-run --verbose 2>/dev/null || true)"
  if [ -n "$prune" ]; then
    printf 'PRUNABLE\n%s\n' "$prune"
  fi

  git -C "$repo" worktree list --porcelain |
    awk '
    /^worktree / { if (path != "") print path "\t" branch; path = substr($0, 10); branch = "" }
    /^branch / { branch = substr($0, 8) }
    /^detached$/ { branch = "(detached)" }
    END { if (path != "") print path "\t" branch }
  ' |
    while IFS="$(printf '\t')" read -r path branch; do
      [ -n "$path" ] || continue
      current_branch="$(git -C "$path" branch --show-current 2>/dev/null || true)"
      [ -n "$current_branch" ] || current_branch="$branch"

      upstream="$(git -C "$path" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
      [ -n "$upstream" ] || upstream="(none)"

      ahead_behind="n/a"
      if [ "$upstream" != "(none)" ]; then
        ahead_behind="$(git -C "$path" rev-list --left-right --count HEAD...'@{u}' 2>/dev/null | awk '{print "ahead="$1",behind="$2}' || true)"
        [ -n "$ahead_behind" ] || ahead_behind="n/a"
      fi

      base=""
      if git -C "$path" rev-parse --verify main >/dev/null 2>&1; then
        base="main"
      elif git -C "$path" rev-parse --verify origin/main >/dev/null 2>&1; then
        base="origin/main"
      fi

      main_delta="unique=n/a,behind=n/a"
      if [ -n "$base" ]; then
        unique="$(git -C "$path" rev-list --count "$base"..HEAD 2>/dev/null || printf 'n/a')"
        behind="$(git -C "$path" rev-list --count HEAD.."$base" 2>/dev/null || printf 'n/a')"
        main_delta="unique=$unique,behind=$behind"
      fi

      dirty_count="$(git -C "$path" status --porcelain --untracked-files=all 2>/dev/null | wc -l | tr -d ' ')"
      branch_line="$(git -C "$path" status --short --branch --untracked-files=all 2>/dev/null | sed -n '1p')"
      last="$(git -C "$path" log -1 --date=short --format='%cd %h %s' 2>/dev/null || true)"
      size="$(du -sh "$path" 2>/dev/null | awk '{print $1}')"
      mtime="$(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$path" 2>/dev/null || stat -c '%y' "$path" 2>/dev/null | cut -d. -f1)"

      printf 'WORKTREE %s\n' "$path"
      printf '  branch: %s\n' "$current_branch"
      printf '  upstream: %s %s\n' "$upstream" "$ahead_behind"
      printf '  main_delta: %s\n' "$main_delta"
      printf '  dirty: %s %s\n' "$dirty_count" "$branch_line"
      printf '  last: %s\n' "$last"
      printf '  size: %s mtime: %s\n' "$size" "$mtime"
    done
  printf -- '---\n'
done <"$tmp_repos"
