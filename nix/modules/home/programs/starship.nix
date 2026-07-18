{
  config,
  dotfilesDir,
  ...
}:
{
  # starship の設定は pi と同様に out-of-store symlink で dotfiles 作業ツリーへ
  # 張る（rebuild なしで live 編集可）。package は packages.nix、fish への
  # init は fish/config.fish に置く（fish dir は link_force 管理のため）。
  xdg.configFile."starship.toml".source =
    config.lib.file.mkOutOfStoreSymlink "${dotfilesDir}/starship/starship.toml";
}
