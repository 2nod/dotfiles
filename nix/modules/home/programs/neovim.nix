{
  lib,
  config,
  dotfilesDir,
  pkgs,
  ...
}:
let
  helpers = import ../../lib/helpers { inherit lib; };
  nvimDotfilesDir = "${dotfilesDir}/nvim";
  nvimConfigDir = "${config.xdg.configHome}/nvim";
  treesitterGrammars = pkgs.vimPlugins.nvim-treesitter.withAllGrammars;
in
{
  programs.neovim = {
    enable = true;
    withRuby = false;
    withPython3 = false;
    extraWrapperArgs = [
      "--set"
      "TREESITTER_GRAMMARS"
      "${treesitterGrammars}"
      "--set"
      "TELESCOPE_FZF_NATIVE"
      "${pkgs.vimPlugins.telescope-fzf-native-nvim}"
    ];
  };

  home.packages = [
    pkgs.efm-langserver
    pkgs.hadolint
    pkgs.oxfmt
    pkgs.oxlint
    pkgs.vimPlugins.telescope-fzf-native-nvim
    pkgs.typescript-go
  ];

  xdg.configFile."nvim/init.lua".enable = lib.mkForce false;

  home.activation.linkNvimConfig = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    ${helpers.activation.mkLinkForce}
    link_force "${nvimDotfilesDir}" "${nvimConfigDir}"
  '';
}
