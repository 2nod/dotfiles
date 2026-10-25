{ pkgs }:
let
  version = "0.9.79-dotfiles.1";
  source = pkgs.fetchFromGitHub {
    owner = "michael-denyer";
    repo = "pstack-claude";
    rev = "60ae9e25610744bccd45bd405c211413a471aaf8";
    hash = "sha256-VBi1L9u4HoRWhiVw1B1ZZ56MqBEchLdTpwojVRT3sWo=";
  };
in
# Keep skills and references intact without session-wide routing in either host.
pkgs.runCommand "pstack-marketplace-${version}" { } ''
  cp -R ${source}/. "$out"
  chmod -R u+w "$out"
  # Hosts cache by version; keep an existing upstream install from retaining hooks.
  substituteInPlace "$out/.claude-plugin/marketplace.json" \
    "$out/plugins/pstack/.claude-plugin/plugin.json" \
    "$out/plugins/pstack/.codex-plugin/plugin.json" \
    --replace-fail '"version": "0.9.79"' '"version": "${version}"'
  for hook in hooks.json codex-hooks.json; do
    printf '%s\n' '{"hooks": {}}' > "$out/plugins/pstack/hooks/$hook"
  done
''
