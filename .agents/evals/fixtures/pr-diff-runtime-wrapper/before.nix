{ pkgs, lib, config, ... }:
let
  installDir = "${config.home.homeDirectory}/.local/share/example-router";
  runtimePath = lib.makeBinPath [ pkgs.nodejs_24 ];
  router = pkgs.writeShellScriptBin "example-router" ''
    export PATH=${runtimePath}''${PATH:+:$PATH}
    exec ${installDir}/bin/dispatcher "$@"
  '';
in
{
  home.packages = [ router ];
}
