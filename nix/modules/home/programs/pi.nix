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
  home.file = {
    ".pi/agent/system-append.md".source =
      config.lib.file.mkOutOfStoreSymlink "${piDotfilesDir}/system-append.md";
    ".pi/agent/model-router.json".source =
      config.lib.file.mkOutOfStoreSymlink "${piDotfilesDir}/model-router.json";
  };

  # pi 起動時に global 行動規範を自動付与する fish ラッパ。
  # install/update などの subcommand には --append-system-prompt を付けない。
  xdg.configFile."fish/functions/pi.fish".text = ''
    function pi --wraps pi --description 'pi with global system-prompt append'
        set -l append "$HOME/.pi/agent/system-append.md"
        switch "$argv[1]"
            case install remove uninstall update list config
                command pi $argv
            case '*'
                if test -f "$append"
                    command pi --append-system-prompt "$append" $argv
                else
                    command pi $argv
                end
        end
    end
  '';

  # 読み取り専用レビュー用ショートカット。
  xdg.configFile."fish/functions/pi-review.fish".text = ''
    function pi-review --wraps pi --description 'pi in read-only mode (no edits)'
        pi --tools read,grep,find,ls $argv
    end
  '';
}
