{
  config,
  dotfilesDir,
  ...
}:
{
  # herdr / hunk 本体は homebrew.brews で管理（nix/modules/darwin/system.nix）。
  # ここでは herdr の設定を宣言的に張る。
  #
  # herdr プラグイン本体（edmundmiller/herdr-plugin-hunk）は herdr の plugin registry が
  # 状態管理するため runtime install（NOTES.md に pin 付き手順を記録）。Nix 管理外。

  # hunk の配色を dark 系で統一。herdr の hunk プラグイン経由の diff pane にも効く
  # （プラグインは HUNK_THEME を読む）。値は fish にも export される
  # （fish/conf.d/02-hm-session-vars.fish）。
  home.sessionVariables = {
    HUNK_THEME = "catppuccin-mocha";
  };

  # config.toml は custom keybindings のみ（組み込みデフォルトに追加される方式）。
  # out-of-store symlink で dotfiles 作業ツリーへ張る（rebuild なしで live 編集可）。
  # 変更反映は `herdr server reload-config`。
  xdg.configFile."herdr/config.toml".source =
    config.lib.file.mkOutOfStoreSymlink "${dotfilesDir}/herdr/config.toml";
}
