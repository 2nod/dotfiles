{ pkgs, ... }:
let
  pstack = import ./pstack-portable.nix { inherit pkgs; };
in
{
  xdg.configFile = {
    "opencode/skills/pstack".source = "${pstack}/plugins/pstack/skills";
    "opencode/AGENTS.md".source = ../../../../opencode/AGENTS.md;
  };
}
