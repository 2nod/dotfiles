#!/usr/bin/env bash
# One-shot bootstrap for this nix-darwin dotfiles repo.
#
# Reduces new-machine setup to a single command: installs Nix if missing,
# ensures the nix-command/flakes experimental features are available, then
# applies the given profile with nix-darwin. Safe to re-run (idempotent).
#
# Usage:
#   ./bootstrap.sh <profile>
#   NIX_DARWIN_PROFILE=<profile> ./bootstrap.sh
#
# Run with no profile to list the available ones. See README.md for details.
set -euo pipefail

cd "$(dirname "$0")"

PROFILE="${1:-${NIX_DARWIN_PROFILE:-}}"

nix_daemon_profile=/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh

load_nix() {
  if ! command -v nix >/dev/null 2>&1 && [ -e "$nix_daemon_profile" ]; then
    # shellcheck disable=SC1090
    . "$nix_daemon_profile"
  fi
}

# 1. Ensure Nix is installed and on PATH.
load_nix
if ! command -v nix >/dev/null 2>&1; then
  echo "==> Nix not found. Installing via the Determinate Systems installer..."
  curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
  load_nix
fi
if ! command -v nix >/dev/null 2>&1; then
  echo "Error: Nix is still not on PATH. Open a new terminal and re-run this script." >&2
  exit 1
fi

# 2. Enable nix-command/flakes for this invocation (the Determinate installer
#    enables them globally, but pass the flags so a stock install also works).
NIX="nix --extra-experimental-features nix-command --extra-experimental-features flakes"

# 3. Require a profile; otherwise list what is available and stop.
if [ -z "$PROFILE" ]; then
  echo "No profile specified. Available profiles:"
  echo
  $NIX run .#list-profiles
  exit 1
fi

# 4. Build then switch, so a broken config fails before touching the system.
echo "==> Building profile: $PROFILE"
$NIX run .#build -- "$PROFILE"

echo "==> Switching to profile: $PROFILE (sudo will be requested)"
$NIX run .#switch -- "$PROFILE"

echo "==> Done. Open a new terminal to pick up the new environment."
