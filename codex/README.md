# Codex pstack

Home Manager は [pstack 0.9.79](https://github.com/michael-denyer/pstack-claude/tree/60ae9e25610744bccd45bd405c211413a471aaf8) を commit と内容ハッシュで固定し、Codex native plugin として `~/.codex` にインストールする。上流のライセンスは MIT。

`nix run .#switch -- <profile>` で反映した後、新しいセッションで個別 skill を指定する。たとえば「pstack の interrogate でこの差分をレビューして」と依頼する。既存の共有 skill と同名の機能は、実行時カタログの plugin 名を含む名称で区別する。

配布パッケージでは `hooks/codex-hooks.json` の登録だけを空にし、skill 本体と参照資料は上流の内容を保持する。SessionStart からの常時ルーティング指示は注入しない。通常の skill 選択には既存の `AGENTS.md` のルールが適用される。`setup-pstack` で sheet の hook 値を変更しても、このパッケージの SessionStart hook は有効にならない。

`pstack-models.md` は初回だけ初期値をコピーし、再 activation では既存の内容を保持する。単独処理は gpt-6.1-sol、強い判断は gpt-6-astra、比較・レビューは gpt-6-astra と gpt-6-sol、reasoning effort は high が初期値となる。

モデル設定の正本は `${CODEX_HOME:-$HOME/.codex}/pstack-models.md`。Codex の `AGENTS.md` は、pstack 利用時にこの sheet を読み込むよう指定する。sheet を編集するか `setup-pstack` を使って変更する。`setup-pstack` が `AGENTS.md` にモデル行を保存する場合、Home Manager のリンク先であるこのリポジトリの `codex/AGENTS.md` に変更が生じる。

Orca などで別の `CODEX_HOME` を使う場合は、その home に plugin を登録し、sheet と読み込み指示を用意する。Home Manager が配布するのは `~/.codex` のみ。
