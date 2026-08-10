# oxlint 1.76+ fails to build on aarch64-darwin: @napi-rs/cli reads the process
# start time by shelling out to /bin/ps, which the build sandbox denies. Node
# raises that denial as a synchronous `spawn EPERM` from execFile, which escapes
# napi's callback-based error handling and aborts the build. Hydra fails the same
# way, so there is no cache hit to fall back on either.
#
# The lookup is only used to detect stale lock files, so any ps will do; point it
# at one from the store so the sandbox allows the exec.
#
# Drop this overlay once https://github.com/NixOS/nixpkgs/issues/551003 is fixed.
final: prev: {
  oxlint = prev.oxlint.overrideAttrs (oldAttrs: {
    preBuild = (oldAttrs.preBuild or "") + ''
      for cli in node_modules/.pnpm/@napi-rs+cli@*/node_modules/@napi-rs/cli/dist/cli.js; do
        substituteInPlace "$cli" \
          --replace-fail '"/bin/ps"' '"${final.darwin.adv_cmds}/bin/ps"'
      done
    '';
  });
}
