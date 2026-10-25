{
  config,
  dotfilesDir,
  pkgs,
  lib,
  ...
}:
let
  piDotfilesDir = "${dotfilesDir}/pi";
  pstack = import ./pstack-portable.nix { inherit pkgs; };
  piAgentDir = "${config.home.homeDirectory}/.pi/agent";
in
{
  # pi の config は runtime 書込のある settings.json 以外を out-of-store symlink で
  # dotfiles 作業ツリーへ張る（rebuild なしで live 編集可・書込可）。
  # - system-append.md: pi 用の global 行動規範（fish の pi ラッパで --append-system-prompt に渡す）
  # - model-router.json: pi-model-router 拡張の設定（拡張は読むだけ。状態は session 側に持つ）
  # settings.json の "packages" 追記だけは `pi install` が書く live 管理。
  # pstack は下の Nix 配布、それ以外の package は pi/packages.txt で復元する。
  # 新マシンでの復元: xargs -I{} pi install {} < pi/packages.txt
  home.file = {
    ".pi/agent/AGENTS.md".source = config.lib.file.mkOutOfStoreSymlink "${piDotfilesDir}/AGENTS.md";
    ".pi/agent/system-append.md".source =
      config.lib.file.mkOutOfStoreSymlink "${piDotfilesDir}/system-append.md";
    ".pi/agent/model-router.json".source =
      config.lib.file.mkOutOfStoreSymlink "${piDotfilesDir}/model-router.json";
    ".pi/agent/skills/pstack".source = "${pstack}/plugins/pstack/skills";
    ".pi/agent/extensions/pstack".source = "${pstack}/plugins/pstack/pi";
  };

  home.activation.installPiPstack = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
    if [ ! -e "${piAgentDir}/pstack-models.md" ]; then
      cp ${../../../../claude/pstack-models.md} "${piAgentDir}/pstack-models.md"
      chmod 600 "${piAgentDir}/pstack-models.md"
    fi
  '';

  # fish 関数（pi ラッパ / pi-review）は `fish/functions/*.fish` にコミット済み実ファイルとして置く。
  # fish dir 全体は dotfiles.nix の link_force で `~/.config/fish` に symlink 配備されるため、
  # ここで xdg.configFile.text 生成すると二重管理になり repo 作業ツリーへ書き出されてしまう。
  # 他の fish 関数と同じく repo ファイル一本で管理する。
}
