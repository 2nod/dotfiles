{
  config,
  dotfilesDir,
  ...
}:
{
  # mise のグローバル設定を out-of-store symlink で dotfiles 作業ツリーへ張る
  # （rebuild なしで live 編集可、`mise use -g` の書き込みもここへ入る）。
  # package は packages.nix、fish への activate は fish/config.fish に置く。
  # programs.mise は shell 連携も追加して fish/config.fish の activate と重複するため使わない。
  xdg.configFile."mise/config.toml".source =
    config.lib.file.mkOutOfStoreSymlink "${dotfilesDir}/mise/config.toml";
}
