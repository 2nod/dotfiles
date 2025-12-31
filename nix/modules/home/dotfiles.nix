{ ... }:
{
  xdg.enable = true;

  xdg.configFile."wezterm" = {
    source = ../../../wezterm;
    recursive = true;
  };

  xdg.configFile."nvim" = {
    source = ../../../nvim;
    recursive = true;
  };

  xdg.configFile."karabiner" = {
    source = ../../../karabiner;
    recursive = true;
  };
}
