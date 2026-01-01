# Fish メモ

## プラグイン候補
- fzf: 履歴やファイル検索などのファジー検索を強化
- zoxide: 学習型のディレクトリジャンプで `cd` を高速化
- bass: bash/zsh の環境を fish に読み込む（nvm 併用時に便利）
- fish-abbreviation-tips: 省略コマンドのヒント表示
- autopair-fish: 括弧やクォートの自動ペア入力
- fish-bd: 上位ディレクトリへ素早く戻る

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
### ファイルマネージャ（oil）
- 開く: `<leader>e`（leaderはSpace）
- 開く/分割: `<CR>` / `<C-s>`(vsplit) / `<C-h>`(split) / `<C-t>`(tab)
- 移動: `-`(親) / `_`(cwd) / `g.`(隠し)
- プレビュー: `<C-p>` / `gp`(WezTermプレビュー) / `g<leader>`(QuickLook)

### Lazy
- 未インストールは起動時に自動インストール（`install.missing = true`）
- 更新/削除反映は手動: `:Lazy sync` / `:Lazy update` / `:Lazy clean`

### LSP
- `gd`: 定義へ
- `gr`: 参照一覧
- `K`: ホバー
- `<leader>rn`: リネーム
- `<leader>ca`: コードアクション
- `<leader>f`: フォーマット

### Diagnostics
- `<leader>de`: 浮動ウィンドウ
- `[d` / `]d`: 前/次

### Telescope
- `<leader>ff`: ファイル
- `<leader>fg`: grep
- `<leader>fb`: バッファ
- `<leader>fh`: ヘルプ

### telescopeとoilの使い分け
- Telescope: ファイル名/内容で素早く検索して開く
- oil: ディレクトリを見ながら移動・操作（作成/移動/削除/リネーム）
