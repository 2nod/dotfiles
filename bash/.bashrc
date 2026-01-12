# PATH
export XDG_CONFIG_HOME="$HOME/.config"
export PATH="/Users/tsuno/.detaspace/bin:$PATH"

# Homebrew
eval "$(/opt/homebrew/bin/brew shellenv)"

# Rust
. "$HOME/.cargo/env"

# ssh-agent
ssh-add -l &>/dev/null || ssh-add --apple-use-keychain "$HOME/.ssh/github" 2>/dev/null

# Node (nvm)
export NVM_DIR="${XDG_CONFIG_HOME}/nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# Bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# pnpm
export PNPM_HOME="/Users/tsuno/Library/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac

# home-manager session variables
HM_SESSION_VARS="$HOME/.local/state/home-manager/gcroots/current-home/home-path/etc/profile.d/hm-session-vars.sh"
. "$HM_SESSION_VARS"

# direnv
if [ -n "$BASH_VERSION" ] && command -v direnv >/dev/null 2>&1; then
  eval "$(direnv hook bash)"
fi
