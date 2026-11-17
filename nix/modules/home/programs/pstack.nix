{
  config,
  pkgs,
  lib,
  ...
}:
let
  pstackDir = "${config.xdg.dataHome}/pstack";
in
{
  # Fetch at activation, not evaluation: main stays current without a flake lock pin.
  home.activation.updatePstack = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    (
      set -euo pipefail
      pstackDir="${pstackDir}"
      mkdir -p "$pstackDir"
      pstackStage=$(mktemp -d)
      trap 'rm -rf "$pstackStage"' EXIT

      fetch_pstack() {
        name="$1"
        repo="$2"
        cache="$pstackDir/$name.git"
        if [ ! -d "$cache" ]; then
          ${pkgs.git}/bin/git init --bare "$cache"
        fi
        ${pkgs.git}/bin/git --git-dir="$cache" fetch --depth 1 "$repo" main
        mkdir -p "$pstackStage/$name"
        ${pkgs.git}/bin/git --git-dir="$cache" archive FETCH_HEAD | tar -x -C "$pstackStage/$name"
      }

      fetch_pstack marketplace https://github.com/michael-denyer/pstack-claude.git
      fetch_pstack cursor https://github.com/cursor/plugins.git

      # Hosts cache by version. Include the fetched commit and the local hook policy.
      revision=$(${pkgs.git}/bin/git --git-dir="$pstackDir/marketplace.git" rev-parse --short FETCH_HEAD)
      for manifest in .claude-plugin/plugin.json .codex-plugin/plugin.json; do
        file="$pstackStage/marketplace/plugins/pstack/$manifest"
        ${pkgs.jq}/bin/jq --arg suffix "-dotfiles.$revision" '.version += $suffix' "$file" > "$file.tmp"
        mv "$file.tmp" "$file"
      done
      file="$pstackStage/marketplace/.claude-plugin/marketplace.json"
      ${pkgs.jq}/bin/jq --arg suffix "-dotfiles.$revision" \
        '(.plugins[] | select(.name == "pstack").version) += $suffix' "$file" > "$file.tmp"
      mv "$file.tmp" "$file"
      for hook in hooks.json codex-hooks.json; do
        printf '%s\n' '{"hooks": {}}' > "$pstackStage/marketplace/plugins/pstack/hooks/$hook"
      done

      mkdir -p "$pstackStage/portable"
      cp -R "$pstackStage/marketplace/plugins/pstack/." "$pstackStage/portable/"
      for skill in "$pstackStage"/portable/skills/*/SKILL.md; do
        sed '2s/^name: /name: pstack-/' "$skill" > "$skill.tmp"
        mv "$skill.tmp" "$skill"
      done

      mkdir -p "$pstackDir/marketplace" "$pstackDir/portable" "$pstackDir/cursor"
      ${pkgs.rsync}/bin/rsync -r --checksum --delete "$pstackStage/marketplace/" "$pstackDir/marketplace/"
      ${pkgs.rsync}/bin/rsync -r --checksum --delete "$pstackStage/portable/" "$pstackDir/portable/"
      ${pkgs.rsync}/bin/rsync -r --checksum --delete "$pstackStage/cursor/pstack/" "$pstackDir/cursor/"

      rm -rf "$pstackStage"
      trap - EXIT
    )
  '';
}
