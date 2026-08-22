{
  pkgs,
  lib,
  config,
  ...
}:
let
  # install.sh の既定と同じ場所。ここを変えると `codex-router update` などが
  # 見失うので、upstream の default_data_dir に合わせておく。
  installDir = "${config.home.homeDirectory}/.local/share/codex-router";

  codexHome = "${config.home.homeDirectory}/.codex";

  repositoryUrl = "https://github.com/duolahypercho/codex-router.git";

  # 追従する upstream の revision。Nix を source of truth にするため、
  # checkout はここで固定し、更新はこの値の bump で行う。
  # `codex-router update` は使わないこと (HEAD が動いて宣言とずれる)。
  rev = "866cb8b011fa8e16900c77c58249b71eec6436ca";

  # codex-router が要求する runtime。node は 22.19+ が必須で、python 依存は
  # uv が requirements/python.txt (hash 検証済み lock) から入れる。
  # codex 本体は enable が「ログイン済みか」を CLI に尋ねるために要る。
  #
  # home.packages には入れない。node はユーザーの mise が別途管理しており、
  # global PATH に nix の node を足すと版が競合する。codex-router にだけ
  # 既知の版を渡せば足りる。
  runtimePath = lib.makeBinPath [
    pkgs.git
    pkgs.nodejs_24
    pkgs.uv
    pkgs.llm-agents.codex
  ];

  # package manager が PATH に置くのは 1 つの名前で、bin/ の中身ではない。
  # upstream の bin/codex-router がその dispatcher なので、それを runtime 付きで叩く。
  codex-router = pkgs.writeShellScriptBin "codex-router" ''
    export PATH=${runtimePath}''${PATH:+:$PATH}
    exec ${installDir}/bin/codex-router "$@"
  '';
in
{
  home.packages = [ codex-router ];

  # home-manager は activation の各ブロックを 1 つの bash script に連結する。
  # そのため素の `exit` は activation 全体を打ち切ってしまう。ここでの失敗は
  # codex-router が使えないだけで、system の再構築を止める理由にはならないので、
  # 各ブロックは subshell に閉じ込めて早期 return を局所化する。

  # checkout を rev に固定し、依存だけ入れる。
  #
  # `install.sh --prepare-only` は node/python の依存を入れるだけで Codex の設定には
  # 触れない。認証情報と Codex への統合は `codex-router setup --guided` の仕事で、
  # そちらは対話的に API キーを受け取るため activation では絶対に実行しない。
  #
  # install.sh は checkout 内から起動すると git 処理を全部飛ばして自分自身の
  # checkout を対象にするので、revision 管理はここで完結する。
  home.activation.codexRouter = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    (
      export PATH=${runtimePath}''${PATH:+:$PATH}

      if [ ! -e "${installDir}/.git" ]; then
        if [ -e "${installDir}" ]; then
          echo "codex-router: ${installDir} exists but is not a checkout; skipping." >&2
          exit 0
        fi
        $DRY_RUN_CMD mkdir -p "$(dirname -- "${installDir}")"
        $DRY_RUN_CMD git clone ${repositoryUrl} "${installDir}" || {
          echo "codex-router: clone failed; skipping." >&2
          exit 0
        }
      fi

      if [ "$(git -C "${installDir}" rev-parse HEAD 2>/dev/null)" != "${rev}" ]; then
        $DRY_RUN_CMD git -C "${installDir}" fetch --depth 1 origin ${rev} || {
          echo "codex-router: fetch failed; leaving the checkout as it is." >&2
          exit 0
        }
        $DRY_RUN_CMD git -C "${installDir}" checkout --detach ${rev} || {
          echo "codex-router: checkout of ${rev} failed; leaving the checkout as it is." >&2
          exit 0
        }
      fi

      # stamp 済みなら中で skip されるので、毎回の switch では実質何もしない。
      $DRY_RUN_CMD "${installDir}/install.sh" --prepare-only || {
        echo "codex-router: --prepare-only failed; run it by hand to see why." >&2
        exit 0
      }
    )
  '';

  # codex.nix の writeCodexConfig が config.toml を毎回作り直すため、setup が書いた
  # codex-router-managed ブロックは switch のたびに必ず消える。ここで書き戻す。
  #
  # ブロックの base_url には router の caller token が入る。dotfiles は git 管理下
  # なので、中身を codex.nix の settings に転記してはいけない。書き戻しを
  # codex-router 自身にやらせるのが唯一の正しい方法で、秘密が repository に
  # 入らない理由でもある。
  #
  # 呼ぶのは bin/enable ではなく config-manager.mjs 単体。bin/enable は catalog の
  # 再構築、service の再インストール、health 待ちまで行い 16 秒かかる上に、
  # codex-router と無関係な switch のたびに router を再起動してしまう。ここで要るのは
  # config.toml を書く一段だけで、それは 0.1 秒で終わる。
  #
  # 自前でブロックを保存・復元しないのは、貼る位置が TOML の構造に依存するから。
  # codex-router-managed は table header より前の最上位キーで、
  # multi-agent-v2-managed は [features] の内側に入る。位置を間違えると
  # 壊れたことに気付けないまま設定だけが効かなくなる。upstream の配置ロジックに
  # 任せる。
  #
  # 未 setup の段階では state ごと無く、書くべきブロックも無いので何もしない。
  home.activation.codexRouterEnable =
    lib.hm.dag.entryAfter
      [
        "writeCodexConfig"
        "codexRouter"
      ]
      ''
        (
          export PATH=${runtimePath}''${PATH:+:$PATH}
          export CODEX_HOME="${codexHome}"

          if [ ! -d "${codexHome}/codex-router" ] || [ ! -e "${codexHome}/config.toml" ]; then
            exit 0
          fi
          if grep -q 'BEGIN codex-router' "${codexHome}/config.toml"; then
            exit 0
          fi

          $DRY_RUN_CMD ${pkgs.nodejs_24}/bin/node "${installDir}/src/config-manager.mjs" enable >/dev/null || {
            echo "codex-router: could not restore the managed config block." >&2
            echo "codex-router: Codex is on native models until 'codex-router enable' is run." >&2
            exit 0
          }
        )
      '';
}
