{
  pkgs,
  ...
}:
let
  jsonFormat = pkgs.formats.json { };

  settings = {
    auths = { };
    currentContext = "colima";
  };
in
{
  home.file.".docker/config.json".source = jsonFormat.generate "config.json" settings;
}
