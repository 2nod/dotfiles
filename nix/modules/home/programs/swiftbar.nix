{
  dotfilesDir,
  ...
}:
{
  # SwiftBar 本体は homebrew.casks で管理（nix/modules/darwin/system.nix）。
  # plugin 置き場は dotfiles 作業ツリーを直接見せる（pi / starship と同じ方針で
  # rebuild なしに script を live 編集できる）。SwiftBar は初回起動時に plugin
  # folder を訊いてくるが、この default を先に書いておけば訊かれない。
  targets.darwin.defaults."com.ameba.SwiftBar" = {
    PluginDirectory = "${dotfilesDir}/swiftbar/plugins";
  };
}
