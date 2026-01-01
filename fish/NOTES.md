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
