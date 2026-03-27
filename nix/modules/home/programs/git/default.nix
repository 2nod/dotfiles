{ lib, config, ... }:
let
  helpers = import ../../../lib/helpers { inherit lib; };
  user = helpers.mkUser config;
  aliasesFile = ./aliases;
in
{
  programs.git = {
    enable = true;
    signing.format = null;
    settings = {
      user = {
        name = user.username;
        email = user.email;
      };
    };
    includes = [
      { path = "${aliasesFile}"; }
    ];
  };
}
