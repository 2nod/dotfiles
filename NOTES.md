# Fish メモ
## 方針
- nix-darwin 側はログインシェル指定のみで、`programs.fish.*` は使わない（`nix/modules/darwin/system.nix`）
- 環境変数/パス/初期化は `config.fish` に直書きで管理（`fish/config.fish`）
- プラグインは Home Manager が `conf.d` を生成して読み込む方式（`nix/modules/home/programs/fish/default.nix`）
- alias/abbr は `abbrs_aliases.fish` に集約（`fish/config/abbrs_aliases.fish`）

## プラグイン候補
- fzf: 履歴やファイル検索などのファジー検索を強化
- zoxide: 学習型のディレクトリジャンプで `cd` を高速化
- mise: Node.js などの言語バージョン管理を `fish` で扱う
- fish-abbreviation-tips: 省略コマンドのヒント表示
- autopair-fish: 括弧やクォートの自動ペア入力
- fish-bd: 上位ディレクトリへ素早く戻る

## Nixメモ
### packagesの分け方
- 汎用CLIは `nix/modules/home/packages.nix`（シェルから使うもの）
- エディタ専用のLSP/formatter/linterは `nix/modules/home/programs/neovim/default.nix`
### バージョン確認（構造）
- Nixパッケージ一覧: `nix/modules/home/packages.nix` / `nix/modules/darwin/packages.nix`
- Nixの固定元: `flake.lock` の `nixpkgs.locked.rev`
- brew-nix cask一覧: `nix/modules/darwin/packages.nix` の `pkgs.brewCasks.*`
- brew-nixの固定元: `flake.lock` の `brew-api.locked.rev`
- Homebrew直管理: `nix/modules/darwin/system.nix` の `homebrew.*`（固定なし）
### GUIアプリの方針（macOS）
- GUIアプリは `homebrew.casks` で管理（/Applications 配置で永続化しやすい）
- brew-nixの `pkgs.brewCasks.*` はGUIを避け、CLI/軽量ツールに限定する
- 背景: `/nix/store` 配置の `.app` に ACL が付くと GC 時に `Operation not permitted` が発生しやすい
### バイナリキャッシュ
- `nixos-25.11` stable を使用（unstable はキャッシュミスが多い）
- `llm-agents.nix`（codex / cursor-agent / opencode）は `cache.numtide.com` からキャッシュ取得
- キャッシュ設定は `/etc/nix/nix.custom.conf` にシステムレベルで記述（Determinate Nix の管理外）
  ```
  extra-trusted-substituters = https://cache.numtide.com
  extra-trusted-public-keys = niks3.numtide.com-1:DTx8wZduET09hRmMtKdQDxNNthLQETkc/yaX7M4qK0g=
  ```
- 新規マシンセットアップ時にこの2行を `/etc/nix/nix.custom.conf` に追加してデーモン再起動が必要
  ```bash
  sudo sh -c 'printf "extra-trusted-substituters = https://cache.numtide.com\nextra-trusted-public-keys = niks3.numtide.com-1:DTx8wZduET09hRmMtKdQDxNNthLQETkc/yaX7M4qK0g=\n" > /etc/nix/nix.custom.conf'
  sudo launchctl kickstart -k system/systems.determinate.nix-daemon
  ```

### バージョン確認（コマンド）
- Nixパッケージ: `nix eval --raw ".#darwinConfigurations.<profile>.pkgs.<name>.version"`
- brew-nix cask: `nix eval --raw ".#darwinConfigurations.<profile>.pkgs.brewCasks.<cask>.version"`
- Homebrew直管理: `brew info <brew>` / `brew info --cask <name>`
- snapshot確認: `git log --oneline -- flake.lock` / `git show <commit>:flake.lock`

## direnvメモ
- 初回は `direnv allow` が必要（`.envrc` を変更したら再度実行、または `direnv reload`）
- このrepoの `.envrc` は `.envrc.local` があれば読み込む
- `NIX_DARWIN_PROFILE` は `.envrc.local` に置く
- 秘密情報は `.envrc.local` / `.env` に分離して gitignore
- 無効化したい時は `direnv deny` か `.envrc` を削除

## WezTermキーと開発コマンド
### WezTermキー
- Leader: Ctrl+q
- Pane: Cmd-d(左右) / Cmd-Shift-d(上下) / Cmd-hjkl(移動) / Cmd-Shift-hjkl(サイズ) / Cmd-z(ズーム) / Cmd-w or Leader+x(閉じる)
- タブ: Cmd-t(新規) / Cmd-Shift-W(閉じる) / Leader+1..9(移動) / Cmd-Shift-( / Cmd-Shift-)(並べ替え)
- Workspace: Cmd-Shift-S(作成) / Cmd-s(一覧/切替) / Cmd-Shift-n/p(前後) / Leader+s(改名)
- その他: Leader+Space(QuickSelect) / Leader+;(フルスクリーン) / Cmd-Shift-f(ぼかし切替) / Leader+Ctrl+a(Ctrl-A送信)

### Macキー
- Option+h/l: Space切り替え / Option+j/k: Mission Control・App Expose

### Copy mode
- 入る: `Leader+[`
- 選択: `v` でセル選択 / `V` で行選択 / `Ctrl+v` で矩形選択
- 移動: `h j k l` / 矢印 / `Home` / `End` / `PageUp` / `PageDown`
- コピーして終了: `y`（選択をクリアして終了）
- 終了: `Esc` / `q`（選択をクリアして終了）

### よく使うコマンド
- 開発起動: `pnpm dev` / `bun run dev` / `deno task dev`
- 依存追加: `pnpm add <pkg>` / `bun add <pkg>` / `deno add <pkg>`
- テスト: `pnpm test` / `bun test` / `deno test` / `uv run pytest`
- ビルド: `pnpm build` / `bun run build` / `deno task build`
- Git: `git status`, `git diff`, `git switch -c <name>`, `git add -p`, `git commit -m "msg"`
- PR/TUI: `gh pr create`, `gh pr view`, `lazygit`, `yazi`
- 通知: 30秒超コマンドは通知→クリックで元paneへ復帰（fish_right_prompt）

### よく使うTUI
- `lazygit`: Git操作
- `yazi`: ファイルマネージャ
- `gh` + `fzf`: PR/Issue一覧
- `top` / `htop` / `bottom`: 監視

## Neovimメモ
### プラグイン
#### 使い方
- which-key.nvim: `<leader>` を押して少し待つとキーマップ候補が表示（`timeoutlen=400`）
- dropbar.nvim: winbar にパンくず表示、`<leader>;` でパンくず選択

#### 候補
- Comment.nvim + nvim-ts-context-commentstring: コメント切替＋言語別コメント自動判定
- nvim-insx: 括弧/クォートの自動補完
- mini.surround: surround の追加/変更/削除
- nvim-treesitter-textobjects: 関数/引数などのテキストオブジェクト拡張
- todo-comments.nvim: TODO/FIXME の強調と検索
- vim-illuminate: 同一語ハイライト
- inc-rename.nvim: LSP リネームのプレビュー
- diffview.nvim（or vim-gin）: Git の差分/履歴ビュー
- nvim-navic: パンくず表示（ステータスライン等）

#### treesitter 候補
- nvim-treesitter-textobjects: TSベースのテキストオブジェクト（選択/移動/入れ替え）
- nvim-treesitter-textsubjects: 文脈を見て賢く選択
- treesitter-unit: TSノード単位の選択
- nvim-treesitter-context: 画面上部に現在の文脈を固定表示
- nvim_context_vt: 文脈を行末に仮想テキスト表示
- nvim-treesitter-clipping + vim-partedit: TSノード単位の部分編集
- nvim-ts-autotag: HTML/JSXのタグ自動閉じ/リネーム
- nvim-ts-context-commentstring: 言語別コメント判定（Comment.nvim連携）
- rainbow-delimiters.nvim: 括弧ネストの色分け
- cmp-treesitter: 補完にTS情報を利用

### プラグイン管理（Lazy）
- 未インストールは起動時に自動インストール（`install.missing = true`）
- 更新/削除反映は手動: `:Lazy sync` / `:Lazy update` / `:Lazy clean`

### ファイル/検索
#### oil（ファイルマネージャ）
- 開く: `<leader>e`（leaderはSpace）
- 開く/分割: `<CR>` / `<C-s>`(vsplit) / `gh`(split) / `<C-t>`(tab)
- 移動: `-`(親) / `_`(cwd) / `g.`(隠し)
- プレビュー/更新: `<C-p>` / `gp`(WezTermプレビュー) / `g<leader>`(QuickLook) / `gr`(refresh)

#### Telescope
- `<leader>ff`: ファイル
- `<leader>fg`: grep
- `<leader>fb`: バッファ
- `<leader>fh`: ヘルプ

#### 使い分け
- Telescope: ファイル名/内容で素早く検索して開く
- oil: ディレクトリを見ながら移動・操作（作成/移動/削除/リネーム）

### 開発支援
#### LSP
- `gd`: 定義へ（Telescope）
- `gt`: 型定義へ（Telescope）
- `gI`: 実装へ（Telescope）
- `gr`: 参照一覧（Telescope）
- `K`: ホバー
- `<leader>rn`: リネーム
- `<leader>ca`: コードアクション
- `<leader>f`: フォーマット

#### JS/TS LSP構成
- 役割: 型/補完/定義=tsgo、lint=oxlint、format=oxfmt、Dockerfileのみ=efm+hadolint
- 有効化/設定: `nvim/lua/plugin/nvim-lspconfig.lua` / `nvim/after/lsp/tsgo.lua` / `nvim/after/lsp/oxlint.lua` / `nvim/after/lsp/oxfmt.lua` / `nvim/after/lsp/efm.lua`
- Nix: `nix/modules/home/programs/neovim/default.nix` に `pkgs.typescript-go` / `pkgs.oxlint` / `pkgs.oxfmt` / `pkgs.efm-langserver` / `pkgs.hadolint`
- フォーマット: `<leader>f` は `oxfmt` を優先（`nvim/lua/config/lsp.lua`）
- 起動/ルート: tsgo=`tsgo --lsp --stdio`(lockfile+`.git`/Deno除外)、oxlint=`oxlint --lsp`(`.oxlintrc.json`/`package.json`/`.git`)、oxfmt=`oxfmt --lsp`(`.oxfmtrc.json(c)`/`package.json`/`.git`); いずれも `node_modules/.bin` 優先
- filetypes: oxlint=js/ts/tsx/jsx+vue/svelte/astro、oxfmt=それに加えて css/scss/less/html/json/jsonc/json5/yaml/toml/markdown/mdx/graphql/handlebars
#### JS/TS LSP運用メモ
- Nix反映後にNeovim再起動
- プロジェクトに `.oxlintrc.json` / `.oxfmtrc.json` を用意（Ultraciteの `ultracite init` でもOK）
- JS/TSは tsgo+oxlint+oxfmt が動作、Dockerfileは efm+hadolint
- フォーマットは `<leader>f`

#### Diagnostics
- `<leader>de`: 浮動ウィンドウ
- `[d` / `]d`: 前/次

#### Markdown
- `<leader>mp`: Markdown/MDX ライブプレビューの開始/停止（トグル, Markdown/MDX バッファのみ）
- `<leader>mo`: Markdown/MDX ライブプレビュー開始（Markdown/MDX バッファのみ）
- `<leader>mc`: Markdown/MDX ライブプレビュー停止（Markdown/MDX バッファのみ）

#### Git (gitsigns)
- `md`: diffビュー（右分割）
- `mh` / `mp`: hunkプレビュー
- `ms`: hunkステージ / `mS`: バッファ全体ステージ
- `mu`: hunkステージ取り消し / `mr`: hunkリセット / `mR`: バッファリセット
- `mb`: 行blame / `mB`: blame一覧
- 現在行blameは常時表示
- diffビュー終了: `:diffoff`（全体解除） / ウィンドウを閉じるなら `:q`
- stageの使い方: 変更箇所にカーソル → `ms`（hunk）/ `mS`（バッファ）
- diffビュー移動: `]c`（次） / `[c`（前） / `sh/sj/sk/sl`（ウィンドウ移動）

#### Satellite
- 右端のスクロールバーに差分位置が表示される

### ウィンドウ
- `ss`: split（上下）
- `sv`: vsplit（左右）
- `sh` / `sj` / `sk` / `sl`: ウィンドウ移動

# Agentツールメモ（herdr / hunk / pi）

## 管理方針
- herdr / hunk: `homebrew.brews` で管理（`nix/modules/darwin/system.nix`）
  - herdr: nixpkgs unstable の 0.7.1 は darwin で `DarwinSdkNotFound` によりビルド不可。brew は bottled で新しい
  - hunk: nixpkgs 未収録
- pi: `llm-agents` overlay（`nix/modules/home/programs/ai-tools.nix`、cursor-agent / opencode と同じ）
- pi の skill collision 対策: `~/dotfiles` 内で pi を起動すると、authoring 元（`.agents/skills` = project）と
  switch 時の配備コピー（`~/.agents/skills` = global）の両方が見つかり衝突警告が出る。
  `.pi/settings.json` の `"skills": ["!**"]` で project 側の自動探索を除外し、配備コピーだけ読む構成にした
  - 注意: dotfiles 内の pi は switch 時点の skill を読む。作業ツリーの編集中 skill を pi で試すなら
    `pi --skill .agents/skills/<category>/<name>` で明示指定
  - pi は SKILL.md の realpath が同一なら黙って重複排除する。配備を out-of-store symlink 化すれば
    settings なしで解決できるが、agent-skills-nix の bundle 方式を崩すので見送り

## pi の設定（`nix/modules/home/programs/pi.nix`）
- 方針: pi の config は「runtime 書込のある `~/.pi/agent/settings.json` 以外」を
  `mkOutOfStoreSymlink` で dotfiles 作業ツリー（`pi/`）へ張る（claude-code の `CLAUDE.md` と同じ手法）。
  rebuild なしで live 編集可・書込可。
  - `pi/system-append.md` → `~/.pi/agent/system-append.md`: pi 用の global 行動規範
  - `pi/model-router.json` → `~/.pi/agent/model-router.json`: pi-model-router 拡張の設定
- global 行動規範の効かせ方: pi は `~/.config/claude/CLAUDE.md` を読まないので、fish 関数 `pi`
  （`fish/functions/pi.fish`）が対話 / `-p` 実行時のみ `--append-system-prompt system-append.md` を付与。
  `install`/`update` などの subcommand には付けない。
  - `pi-review`: 読み取り専用（`--tools read,grep,find,ls`）ショートカット
- model routing: 拡張 `@yeliu84/pi-model-router` を `pi install npm:@yeliu84/pi-model-router` で導入。
  - settings.json の `"packages"` 追記は pi install が書く **live 管理**（Nix seed していない。必要になったら
    claude-code の activation cp 方式で seed する）
  - `model-router.json`: 全 tier を `openai-codex` 内に収めた叩き（課金事故回避）。high=gpt-5.6-sol /
    medium=gpt-5.5 / low=gpt-5.4-mini、classifier=mini。`claude` profile（opus/sonnet）は per-token 課金なので
    使うとき `/router profile claude` で明示切替
  - 拡張の pin/profile/cost 状態は session 側（`router-state`）に持つので config ファイルは読み取り専用でよい
  - 使い方: TUI で `/router profile auto` で有効化 → `/router` で状態確認 / `/router pin high` で固定 /
    `/router debug on` で毎ターンの判定表示

## herdr（agent multiplexer）
- prefix は `Ctrl+B`（tmux互換）。wezterm leader は `Ctrl+Q` なので衝突しない
- 注意: herdr 内の nvim ではページアップ（`Ctrl+B`）が prefix に食われる。困ったら
  `herdr --default-config > ~/.config/herdr/config.toml` で書き出して `prefix` を変更
- 基本操作: `prefix+c` 新tab / `prefix+1-9` tab切替 / `prefix+v` 縦split / `prefix+-` 横split /
  `prefix+h/j/k/l` pane移動 / `prefix+w` workspace picker / `prefix+q` detach / `prefix+?` ヘルプ
- セッション: `herdr --session <name>` → detach しても agent は動き続ける → `herdr session attach <name>`

### herdr のプラグイン機構と hunk プラグイン
- `herdr plugin ...` は `herdr integration ...`（＝agent CLI の管理）とは別系統。プラグインは
  manifest（`herdr-plugin.toml`）＋実行ファイルで action / event hook を提供する。要 herdr ≥0.7.0
- 導入済み: **`edmundmiller/herdr-plugin-hunk`**（herdr の pane/tab に hunk diff を出す薄いラッパ、Python3）
  - 再現手順（ref 固定・**runtime install**。plugin registry が状態管理するため Nix 管理外）:
    ```
    herdr plugin install edmundmiller/herdr-plugin-hunk \
      --ref 11ba5dcca4358203ca68f160becf6870cf016c18 --yes
    ```
  - 検証: `herdr plugin list` / `herdr plugin action list`。格納: `~/.config/herdr/plugins/`
  - 提供 action（6種）: `hunk.diff.{worktree,staged,branch}-{split,tab}`
  - 呼び方:
    - CLI: `herdr plugin action invoke worktree-split`
    - TUI キー割当（`herdr/config.toml` を `herdr.nix` で symlink 管理。`[[keys.command]]` は
      組み込みデフォルトに追加される方式）。空きキー d/i/u（+alt で tab 版）を使用:
      | キー | action | 意味 |
      |---|---|---|
      | `prefix+d` / `prefix+alt+d` | worktree-split / -tab | 作業ツリー diff |
      | `prefix+i` / `prefix+alt+i` | staged-split / -tab | staged(index) diff |
      | `prefix+u` / `prefix+alt+u` | branch-split / -tab | branch(upstream) diff |
    - 変更反映は `herdr server reload-config`。カスタムキーを消すなら `herdr config reset-keys`
  - 配色: `HUNK_THEME` を `nix/modules/home/programs/herdr.nix` で `catppuccin-mocha` に固定
    （home.sessionVariables → fish に export）。プラグイン経由の diff pane にも効く
  - 安全性: manifest は `python3 hunk_herdr.py <type> <mode>` を呼ぶだけ。スクリプトは herdr/git/hunk を
    実行するのみ（`shell=True` なし、`shlex.quote`、mode/target を allowlist 検証、ネットワークなし）

## hunk（diffビューアTUI）
- `hunk diff`（作業ツリー、未追跡含む）/ `hunk diff --staged` / `hunk show`（直近コミット）/ `hunk diff --watch`（自動リロード）
- agent 連携: `hunk skill path` が返す SKILL.md を Claude Code などの skill に登録できる
- 配色は `HUNK_THEME`（`herdr.nix` で `catppuccin-mocha`）。他候補: graphite / midnight / ember / zenburn / catppuccin-latte

### hks（自作 fish 関数: 開いている hunk の表示切り替え）
- TUI 内にソース切り替えキーは無いので、別ペインから `hunk session reload` を叩く。そのラッパが `hks`（`fish/functions/hks.fish`）
- `hks` / `hks wt`: 作業ツリー / `hks staged`（`hks s`）: ステージ済み
- `hks main`: branch 名は `diff main...HEAD`（PR 視点、自分の変更だけ）になる
- `hks main..HEAD` / `hks v1..v2`: `..` を含む引数はそのまま範囲 diff（log は 2点、diff は 3点が普段使い）
- `hks HEAD~1` / `hks <hash>`: branch 名でない ref はその commit 単体の表示（`show`）
- 同一リポジトリでセッションが複数あると fzf で選択（起動が新しい順、Enter で最新）
- `hks clean`: 端末を失ったゾンビ hunk セッションを kill
  - hunk 0.17 はペインごと閉じると SIGHUP を無視して残る。`q` で終了してから閉じるか、溜まったら `hks clean`

## 組み合わせ
- wezterm の tab で herdr 起動 → pane で agent（claude / codex / pi）、隣の pane で `hunk diff --watch`
- または herdr の hunk プラグインで pane/tab に diff を出す（`herdr plugin action invoke worktree-split`）
