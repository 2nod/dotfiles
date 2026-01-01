fish_add_path "$HOME/.detaspace/bin"
fish_add_path "$HOME/.cargo/bin"

set -gx NVM_DIR "$XDG_CONFIG_HOME/nvm"

set -gx BUN_INSTALL "$HOME/.bun"
fish_add_path "$BUN_INSTALL/bin"

set -gx PNPM_HOME "$HOME/Library/pnpm"
fish_add_path "$PNPM_HOME"
