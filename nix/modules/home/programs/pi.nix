{
  config,
  dotfilesDir,
  ...
}:
let
  piDotfilesDir = "${dotfilesDir}/pi";
in
{
  # pi の config は runtime 書込のある settings.json 以外を out-of-store symlink で
  # dotfiles 作業ツリーへ張る（rebuild なしで live 編集可・書込可）。
  # - system-append.md: pi 用の global 行動規範（fish の pi ラッパで --append-system-prompt に渡す）
  # - model-router.json: pi-model-router 拡張の設定（拡張は読むだけ。状態は session 側に持つ）
  # settings.json の "packages" 追記だけは `pi install` が書く live 管理。
  # 導入済み package の一覧は pi/packages.txt にコミットしておく（唯一の入口）。
  # 新マシンでの復元: xargs -I{} pi install {} < pi/packages.txt
  home.file = {
    ".pi/agent/system-append.md".source =
      config.lib.file.mkOutOfStoreSymlink "${piDotfilesDir}/system-append.md";
    ".pi/agent/model-router.json".source =
      config.lib.file.mkOutOfStoreSymlink "${piDotfilesDir}/model-router.json";
  };

  # fish 関数（pi ラッパ / pi-review）は `fish/functions/*.fish` にコミット済み実ファイルとして置く。
  # fish dir 全体は dotfiles.nix の link_force で `~/.config/fish` に symlink 配備されるため、
  # ここで xdg.configFile.text 生成すると二重管理になり repo 作業ツリーへ書き出されてしまう。
  # 他の fish 関数と同じく repo ファイル一本で管理する。
}
