{
  ...
}:
{
  # Ice (menu bar manager) 本体は homebrew.casks の jordanbaird-ice、常駐は
  # launchd.user.agents.ice で管理（どちらも nix/modules/darwin/system.nix）。
  #
  # ここで持つのは挙動のスカラ値だけ。どのアイコンを隠すかの仕分けは各アプリ
  # 自身の "NSStatusItem Preferred Position <name>" に保存されるため、Ice 側にも
  # ここにも持てない（menu bar 上で cmd + ドラッグする手作業）。
  # IceIcon / MenuBarAppearanceConfigurationV2 / Hotkeys は JSON や binary の
  # blob なので宣言化の対象外にしてある。
  #
  # 型は `defaults read-type com.jordanbaird.Ice <key>` に合わせること。float の
  # キーに整数を書くと型が変わる。
  #
  # 注意: ここに書いたキーは activation のたびに上書きされる。GUI で変えたい
  # 項目が出てきたら、この一覧から外すか、ここの値ごと変えること。
  targets.darwin.defaults."com.jordanbaird.Ice" = {
    # Ice アイコン自体の表示と、隠したセクションの開き方
    ShowIceIcon = true;
    ShowOnClick = true;
    ShowOnHover = false;
    ShowOnHoverDelay = 0.2;
    ShowOnScroll = true;
    ShowSectionDividers = false;

    # 開いたセクションを畳み直す挙動
    AutoRehide = true;
    RehideStrategy = 0;
    RehideInterval = 15.0;
    TempShowInterval = 15.0;

    # always-hidden セクション（3段目）
    EnableAlwaysHiddenSection = false;
    CanToggleAlwaysHiddenSection = true;
    ShowAllSectionsOnUserDrag = true;

    # その他
    HideApplicationMenus = true;
    UseIceBar = false;
    IceBarLocation = 0;
    ItemSpacingOffset = 0.0;
  };
}
