# PATH
export XDG_CONFIG_HOME="$HOME/.config"
export PATH="/Users/tsuno/.detaspace/bin:$PATH"

# Homebrew
eval "$(/opt/homebrew/bin/brew shellenv)"

# Rust
[ -s "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

# ssh-agent
ssh-add -l &>/dev/null || ssh-add --apple-use-keychain "$HOME/.ssh/github" 2>/dev/null

# Node (mise)
export PATH="/etc/profiles/per-user/$USER/bin:$HOME/.local/state/home-manager/gcroots/current-home/home-path/bin:$PATH"
if command -v mise >/dev/null 2>&1; then
  if [ -n "${ZSH_VERSION:-}" ]; then
    eval "$(mise activate zsh)"
  elif [ -n "${BASH_VERSION:-}" ]; then
    eval "$(mise activate bash)"
  fi
fi

# Bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# pnpm
export PNPM_HOME="/Users/tsuno/Library/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac

# Colima
export COLIMA_HOME="$HOME/.config/colima"
if [ -S "$HOME/.config/colima/default/docker.sock" ]; then
  export DOCKER_HOST="unix://$HOME/.config/colima/default/docker.sock"
else
  unset DOCKER_HOST
fi

# direnv
if [ -n "$BASH_VERSION" ] && command -v direnv >/dev/null 2>&1; then
  eval "$(direnv hook bash)"
fi
