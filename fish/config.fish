set -q XDG_CONFIG_HOME || set -gx XDG_CONFIG_HOME "$HOME/.config"
set -q XDG_DATA_HOME || set -gx XDG_DATA_HOME "$HOME/.local/share"
set -q XDG_CACHE_HOME || set -gx XDG_CACHE_HOME "$HOME/.cache"

set -g FISH_CONFIG_DIR "$XDG_CONFIG_HOME/fish"
set -g FISH_CONFIG "$FISH_CONFIG_DIR/config.fish"
set -g FISH_CACHE_DIR /tmp/fish-cache

if type -q direnv
    direnv hook fish | source
end

for file in $FISH_CONFIG_DIR/config/*.fish
    source $file
end

if status is-interactive
    if not set -q __ABBR_TIPS_KEYS; and functions -q __abbr_tips_init
        emit abbr_tips_install
    end
end

set -gx ABBR_TIPS_PROMPT "\n[abbr] {{ .abbr }} => {{ .cmd }}"

set -gx theme_nerd_fonts yes
set -gx BIT_THEME monochrome
set -gx COLIMA_HOME "$HOME/.config/colima"
if test -S "$HOME/.config/colima/default/docker.sock"
    set -gx DOCKER_HOST "unix://$HOME/.config/colima/default/docker.sock"
else
    if set -q DOCKER_HOST
        set -e DOCKER_HOST
    end
end

set -l theme_file "$FISH_CONFIG_DIR/themes/kanagawa.fish"
if test -f $theme_file
    source $theme_file
end

if test -f /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.fish
    source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.fish
end

# PATH
fish_add_path "/etc/profiles/per-user/$USER/bin"
fish_add_path "$HOME/.local/bin"
fish_add_path /usr/local/opt/coreutils/libexec/gnubin
fish_add_path /usr/local/opt/curl/bin
fish_add_path /opt/homebrew/bin
fish_add_path "$HOME/.detaspace/bin"
fish_add_path "$HOME/.cargo/bin"

set -gx BUN_INSTALL "$HOME/.bun"
fish_add_path "$BUN_INSTALL/bin"
fish_add_path "$HOME/.cache/.bun/bin"

set -gx PNPM_HOME "$HOME/Library/pnpm"
fish_add_path "$PNPM_HOME"

fish_add_path "$HOME/.deno/bin"

fish_add_path "$HOME/.local/state/home-manager/gcroots/current-home/home-path/bin"

if type -q mise
    if status is-interactive
        mise activate fish | source
    else
        mise activate fish --shims | source
    end
end

set -gx EDITOR nvim
set -gx GIT_EDITOR nvim
set -gx VISUAL nvim
