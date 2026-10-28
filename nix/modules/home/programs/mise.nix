{
  config,
  dotfilesDir,
  lib,
  ...
}:
{
  # mise のグローバル設定を out-of-store symlink で dotfiles 作業ツリーへ張る
  # （rebuild なしで live 編集可、`mise use -g` の書き込みもここへ入る）。
  # package は packages.nix、fish への activate は fish/config.fish に置く。
  # programs.mise は shell 連携も追加して fish/config.fish の activate と重複するため使わない。
  xdg.configFile."mise/config.toml" = {
    source = config.lib.file.mkOutOfStoreSymlink "${dotfilesDir}/mise/config.toml";
    force = true;
  };

  # Skip the collision check only after arranging a backup before replacement.
  home.activation.backupMiseConfig =
    lib.hm.dag.entryBetween [ "linkGeneration" ] [ "writeBoundary" ]
      ''
        miseConfig="${config.xdg.configHome}/mise/config.toml"
        if [ -e "$miseConfig" ] || [ -L "$miseConfig" ]; then
          case "$(readlink "$miseConfig" || true)" in
            ${builtins.storeDir}/*-home-manager-files/*) ;;
            *)
              run mv --backup=numbered --no-target-directory -- "$miseConfig" "$miseConfig.before-home-manager"
              ;;
          esac
        fi
      '';
}
