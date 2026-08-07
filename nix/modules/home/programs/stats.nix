{
  ...
}:
{
  # Stats (menu bar system monitor) 本体は homebrew.casks の stats、常駐は
  # launchd.user.agents.stats で管理（どちらも nix/modules/darwin/system.nix）。
  # Stats 自身のログイン登録は無効なので、あの agent が起動を担っている。
  #
  # ここで持つのは Combined modules だけ。有効にすると CPU や RAM が個別の
  # NSStatusItem ではなく1つにまとまるので、モジュール間に menu bar の
  # item spacing が挟まらなくなる。
  #
  # ウィジェット構成やモジュールの有効・無効 (CPU_state, RAM_widget など) は
  # 同じドメインに Stats 自身が書き込む。ここで宣言を広げると GUI での変更が
  # activation のたびに戻るので、意図的にこのキーだけに絞っている。
  targets.darwin.defaults."eu.exelban.Stats" = {
    CombinedModules = true;
  };
}
