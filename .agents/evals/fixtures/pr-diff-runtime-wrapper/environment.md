# Execution contract

Interactive shells add the user's Node version-manager shims to `PATH`.
Automation and service processes may invoke `~/.local/bin/example-router` with only system directories on `PATH`.
Node is deliberately absent from the global package set to avoid conflicting with the user's version manager.
