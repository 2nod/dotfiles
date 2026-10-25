{ pkgs }:
let
  marketplace = import ./pstack.nix { inherit pkgs; };
in
pkgs.runCommand "pstack-portable-0.9.79" { } ''
  cp -R ${marketplace}/. "$out"
  chmod -R u+w "$out"
  # These hosts do not namespace plugin skills. Keep sibling paths intact.
  for skill in "$out"/plugins/pstack/skills/*/SKILL.md; do
    sed -i '2s/^name: /name: pstack-/' "$skill"
    sed -n '2p' "$skill" | grep -q '^name: pstack-'
  done
''
