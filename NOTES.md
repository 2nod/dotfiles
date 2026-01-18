# Fish メモ
## 方針
- nix-darwin 側はログインシェル指定のみで、`programs.fish.*` は使わない（`nix/modules/darwin/system.nix`）
- 環境変数/パス/初期化は `config.fish` に直書きで管理（`fish/config.fish`）
- プラグインは Home Manager が `conf.d` を生成して読み込む方式（`nix/modules/home/programs/fish/default.nix`）
- alias/abbr は `abbrs_aliases.fish` に集約（`fish/config/abbrs_aliases.fish`）

## プラグイン候補
- fzf: 履歴やファイル検索などのファジー検索を強化
- zoxide: 学習型のディレクトリジャンプで `cd` を高速化
- bass: bash/zsh の環境を fish に読み込む（nvm 併用時に便利）
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
- Leader: Ctrl-;
- Pane: Cmd-d(左右) / Cmd-Shift-d(上下) / Cmd-hjkl(移動) / Cmd-Shift-hjkl(サイズ) / Cmd-z(ズーム) / Cmd-w or Leader+x(閉じる)
- タブ: Cmd-t(新規) / Cmd-Shift-W(閉じる) / Leader+1..9(移動) / Cmd-Shift-( / Cmd-Shift-)(並べ替え)
- Workspace: Cmd-Shift-S(作成) / Cmd-s(一覧/切替) / Cmd-Shift-n/p(前後) / Leader+s(改名)
- その他: Leader+Space(QuickSelect) / Leader+;(フルスクリーン) / Cmd-Shift-f(ぼかし切替) / Leader+Ctrl+a(Ctrl-A送信)

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
- 開く/分割: `<CR>` / `<C-s>`(vsplit) / `<C-h>`(split) / `<C-t>`(tab)
- 移動: `-`(親) / `_`(cwd) / `g.`(隠し)
- プレビュー: `<C-p>` / `gp`(WezTermプレビュー) / `g<leader>`(QuickLook)

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
- `gd`: 定義へ
- `gr`: 参照一覧
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
