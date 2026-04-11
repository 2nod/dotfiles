{
  pkgs,
  lib,
  ...
}:
{
  xdg.configFile."lazygit/config.yml" = {
    text = ''
      # yaml-language-server: $schema=https://raw.githubusercontent.com/jesseduffield/lazygit/master/schema/config.json
      gui:
        nerdFontsVersion: '3'
        skipRewordInEditorWarning: true
      git:
        pagers:
          - colorArg: always
            pager: ${lib.getExe pkgs.delta} --color-only --paging=never
    '';
  };
}
