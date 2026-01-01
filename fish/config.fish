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

set -g FISH_CONFIG_DIR "$XDG_CONFIG_HOME/fish"
set -g FISH_CONFIG "$FISH_CONFIG_DIR/config.fish"
set -g FISH_CACHE_DIR "/tmp/fish-cache"

for file in $FISH_CONFIG_DIR/config/*.fish
  source $file
end

set -gx theme_nerd_fonts yes
set -gx BIT_THEME monochrome

set -l theme_file "$FISH_CONFIG_DIR/themes/kanagawa.fish"
if test -f $theme_file
  source $theme_file
end
