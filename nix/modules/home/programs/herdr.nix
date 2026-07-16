{ ... }:
{
  # herdr / hunk 本体は homebrew.brews で管理（nix/modules/darwin/system.nix）。
  # hunk の配色を dark 系で統一する。herdr の hunk プラグイン経由の diff pane にも効く
  # （プラグインは HUNK_THEME を読む）。値は home.sessionVariables 経由で fish にも export
  # される（fish/conf.d/02-hm-session-vars.fish）。
  #
  # herdr プラグイン本体（edmundmiller/herdr-plugin-hunk）は herdr の plugin registry が
  # 状態管理するため runtime install（NOTES.md に pin 付き手順を記録）。Nix 管理外。
  home.sessionVariables = {
    HUNK_THEME = "catppuccin-mocha";
  };
}
