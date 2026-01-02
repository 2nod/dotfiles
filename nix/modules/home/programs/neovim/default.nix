{ lib, config, dotfilesDir, pkgs, ... }:
let
  helpers = import ../../../lib/helpers { inherit lib; };
  nvimDotfilesDir = "${dotfilesDir}/nvim";
  nvimConfigDir = "${config.xdg.configHome}/nvim";
  treesitterGrammars = pkgs.vimPlugins.nvim-treesitter.withAllGrammars;
in
{
  programs.neovim = {
    enable = true;
    extraWrapperArgs = [
      "--set"
      "TREESITTER_GRAMMARS"
      "${treesitterGrammars}"
    ];
  };

  home.packages = [
    pkgs.efm-langserver
    pkgs.hadolint
  ];

  home.activation.linkNvimConfig = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
    ${helpers.activation.mkLinkForce}
    link_force "${nvimDotfilesDir}" "${nvimConfigDir}"
  '';
}
