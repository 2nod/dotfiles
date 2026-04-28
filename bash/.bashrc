export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"

if [ -x /opt/homebrew/bin/brew ]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi

export BUN_INSTALL="$HOME/.bun"
export PNPM_HOME="$HOME/Library/pnpm"
export COLIMA_HOME="$HOME/.config/colima"

path_prepend() {
  case ":$PATH:" in
    *":$1:"*) ;;
    *) PATH="$1${PATH:+:$PATH}" ;;
  esac
}

path_prepend "$HOME/.nix-profile/bin"
path_prepend "$HOME/.cargo/bin"
path_prepend "$HOME/.detaspace/bin"
path_prepend "$HOME/.deno/bin"
path_prepend "$BUN_INSTALL/bin"
path_prepend "$HOME/.cache/.bun/bin"
path_prepend "/etc/profiles/per-user/$USER/bin"
path_prepend "$HOME/.local/state/home-manager/gcroots/current-home/home-path/bin"
path_prepend "/run/current-system/sw/bin"
path_prepend "$HOME/.local/bin"
path_prepend "$PNPM_HOME"
path_prepend "/usr/local/opt/curl/bin"
path_prepend "/usr/local/opt/coreutils/libexec/gnubin"
path_prepend "/opt/homebrew/sbin"
path_prepend "/opt/homebrew/bin"
export PATH

if command -v mise >/dev/null 2>&1; then
  eval "$(mise activate bash --shims)"
fi

export DOCKER_HOST="unix://$HOME/.config/colima/default/docker.sock"

export EDITOR=nvim
export GIT_EDITOR=nvim
export VISUAL=nvim

if command -v direnv >/dev/null 2>&1; then
  eval "$(direnv hook bash)"
fi

if [[ $- == *i* ]]; then
  ssh-add -l &>/dev/null || ssh-add --apple-use-keychain "$HOME/.ssh/github" 2>/dev/null
fi
