{
  pkgs,
  ...
}:
let
  jsonFormat = pkgs.formats.json { };

  settings = {
    auths = { };
    # Use the DOCKER_HOST-based default context so Docker does not depend on
    # a persisted colima context record that can disappear across reinstalls.
    currentContext = "default";
  };
in
{
  home.file.".docker/config.json".source = jsonFormat.generate "config.json" settings;
}
