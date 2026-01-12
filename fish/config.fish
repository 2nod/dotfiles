set -q XDG_CONFIG_HOME || set -gx XDG_CONFIG_HOME "$HOME/.config"
set -q XDG_DATA_HOME || set -gx XDG_DATA_HOME "$HOME/.local/share"
set -q XDG_CACHE_HOME || set -gx XDG_CACHE_HOME "$HOME/.cache"

# home-manager session variables
set -l HM_SESSION_VARS "$HOME/.local/state/home-manager/gcroots/current-home/home-path/etc/profile.d/hm-session-vars.sh"
if test -f $HM_SESSION_VARS
  for line in (grep '^export ' $HM_SESSION_VARS)
    set -l kv (string replace 'export ' '' $line)
    set -l key (string split -m1 '=' $kv)[1]
    set -l value (string split -m1 '=' $kv)[2]
    set value (string trim -c '"' $value)
    set -gx $key $value
  end
end

if type -q direnv
  direnv hook fish | source
end

set -g FISH_CONFIG_DIR "$XDG_CONFIG_HOME/fish"
set -g FISH_CONFIG "$FISH_CONFIG_DIR/config.fish"
set -g FISH_CACHE_DIR "/tmp/fish-cache"

for file in $FISH_CONFIG_DIR/config/*.fish
  source $file
end

if status is-interactive
  if not set -q __ABBR_TIPS_KEYS; and functions -q __abbr_tips_init
    emit abbr_tips_install
  end
end

set -gx theme_nerd_fonts yes
set -gx BIT_THEME monochrome

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

set -gx NVM_DIR "$XDG_CONFIG_HOME/nvm"

set -gx BUN_INSTALL "$HOME/.bun"
fish_add_path "$BUN_INSTALL/bin"
fish_add_path "$HOME/.cache/.bun/bin"

set -gx PNPM_HOME "$HOME/Library/pnpm"
fish_add_path "$PNPM_HOME"

fish_add_path "$HOME/.deno/bin"

fish_add_path "$HOME/.local/state/home-manager/gcroots/current-home/home-path/bin"

set -gx EDITOR nvim
set -gx GIT_EDITOR nvim
set -gx VISUAL nvim
