# pstack

Home Manager は [pstack 0.9.79](https://github.com/michael-denyer/pstack-claude/tree/60ae9e25610744bccd45bd405c211413a471aaf8) を commit と内容ハッシュで固定し、CodexとClaude Codeそれぞれのnative pluginとしてインストールする。取得元と配布パッケージは `nix/modules/home/programs/pstack.nix` で共通管理する。上流のライセンスは MIT。

配布版は `0.9.79-dotfiles.1` として登録する。上流版と同じバージョンではClaude Codeのcacheに旧hookが残るため、pluginのmanifestとmarketplaceのversionを分ける。配布内容を変える場合はこの配布版番号も更新する。

`nix run .#switch -- <profile>` で反映した後、新しいセッションで個別 skill を指定する。たとえば「pstack の interrogate でこの差分をレビューして」と依頼する。既存の共有 skill と同名の機能は、実行時カタログの plugin 名を含む名称で区別する。

配布パッケージでは `hooks/codex-hooks.json` と `hooks/hooks.json` の登録を空にし、skill 本体と参照資料は上流の内容を保持する。SessionStart からの常時ルーティング指示は注入しない。通常のskill選択には各エージェントの既存指示を適用する。`setup-pstack` でsheetのhook値を変更しても、このパッケージのSessionStart hookは有効にならない。

`pstack-models.md` は初回だけ初期値をコピーし、再activationでは既存の内容を保持する。Codexは単独処理がgpt-6.1-sol、強い判断がgpt-6-astra、比較・レビューがgpt-6-astraとgpt-6-sol、effortはhigh。Claude Codeは単独処理がopus、比較・レビューがopusとsonnet、effortはsession（親セッションを継承）を初期値とする。

モデル設定の正本は、Codexが `${CODEX_HOME:-$HOME/.codex}/pstack-models.md`、Claude Codeが `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/pstack-models.md`。各AGENTS.md／CLAUDE.mdはpstack利用時にそのsheetを読むよう指定する。sheetを編集するか `setup-pstack` で変更する。`setup-pstack` が指示ファイルにモデル行やincludeを保存すると、Home Managerのリンク先であるこのリポジトリの指示ファイルも変更される。

Home Managerの配布先はCodexが `~/.codex`、Claude Codeが `~/.config/claude`。Orcaなどで別のCODEX_HOMEを使う場合は、そのhomeへ別途pluginを登録し、sheetと読み込み指示を用意する。Cursorなど他のエージェントへの導入は含まない。
