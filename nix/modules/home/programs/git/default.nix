{ lib, config, ... }:
let
  helpers = import ../../../lib/helpers { inherit lib; };
  user = helpers.mkUser config;
  aliasesFile = ./aliases;
in
{
  programs.git = {
    enable = true;
    package = null;
    signing.format = null;
    settings = {
      core.hooksPath = "${config.home.homeDirectory}/.config/git/hooks";
      user = {
        name = user.username;
        email = user.email;
      };
    };
    includes = [
      { path = "${aliasesFile}"; }
    ];
  };

  xdg.configFile."git/hooks/pre-push" = {
    source = ./pre-push;
    executable = true;
  };

  xdg.configFile."git/hooks/pre-push.allowlist" = {
    source = ./pre-push.allowlist;
  };
}
