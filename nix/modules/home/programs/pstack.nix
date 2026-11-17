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

      cache="$pstackDir/cursor.git"
      if [ ! -d "$cache" ]; then
        ${pkgs.git}/bin/git init --bare "$cache"
      fi
      ${pkgs.git}/bin/git --git-dir="$cache" fetch --depth 1 https://github.com/cursor/plugins.git main
      mkdir -p "$pstackStage/upstream"
      ${pkgs.git}/bin/git --git-dir="$cache" archive FETCH_HEAD pstack | tar -x -C "$pstackStage/upstream"

      plugin="$pstackStage/marketplace/plugins/pstack"
      mkdir -p "$plugin"
      cp -R "$pstackStage/upstream/pstack/." "$plugin/"
      mkdir -p "$plugin/.claude-plugin" "$plugin/.codex-plugin" "$pstackStage/marketplace/.claude-plugin"
      # Hosts cache by version, so include the commit even when upstream keeps its version.
      revision=$(${pkgs.git}/bin/git --git-dir="$cache" rev-parse --short FETCH_HEAD)
      for manifest in plugin.json .cursor-plugin/plugin.json; do
        file="$plugin/$manifest"
        ${pkgs.jq}/bin/jq --arg suffix "-dotfiles.$revision" '.version += $suffix' "$file" > "$file.tmp"
        mv "$file.tmp" "$file"
      done
      cp "$plugin/plugin.json" "$plugin/.claude-plugin/plugin.json"
      ${pkgs.jq}/bin/jq '{name, version, description, author, homepage, repository, license, skills: "./skills/"}' \
        "$plugin/.claude-plugin/plugin.json" > "$plugin/.codex-plugin/plugin.json"
      # Retain the installed marketplace ID while replacing its contents with official pstack.
      ${pkgs.jq}/bin/jq '{name: "pstack-claude", owner: .author, plugins: [{name, version, source: "./plugins/pstack"}]}' \
        "$plugin/.claude-plugin/plugin.json" > "$pstackStage/marketplace/.claude-plugin/marketplace.json"

      mkdir -p "$pstackStage/portable"
      cp -R "$plugin/." "$pstackStage/portable/"
      for skill in "$pstackStage"/portable/skills/*/SKILL.md; do
        sed '2s/^name: /name: pstack-/' "$skill" > "$skill.tmp"
        mv "$skill.tmp" "$skill"
      done

      mkdir -p "$pstackDir/marketplace" "$pstackDir/portable" "$pstackDir/cursor"
      ${pkgs.rsync}/bin/rsync -r --checksum --delete "$pstackStage/marketplace/" "$pstackDir/marketplace/"
      ${pkgs.rsync}/bin/rsync -r --checksum --delete "$pstackStage/portable/" "$pstackDir/portable/"
      ${pkgs.rsync}/bin/rsync -r --checksum --delete "$pstackStage/upstream/pstack/" "$pstackDir/cursor/"

      rm -rf "$pstackStage"
      trap - EXIT
    )
  '';
}
