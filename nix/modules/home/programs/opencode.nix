{ config, ... }:
let
  pstack = "${config.xdg.dataHome}/pstack/portable";
in
{
  xdg.configFile = {
    "opencode/skills/pstack".source = config.lib.file.mkOutOfStoreSymlink "${pstack}/skills";
    "opencode/AGENTS.md".source = ../../../../opencode/AGENTS.md;
  };
}
