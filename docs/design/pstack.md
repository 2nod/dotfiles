# pstack

Home Manager は activation のたびに公式の [cursor/plugins](https://github.com/cursor/plugins/tree/main/pstack) の `main` を取得し、その `pstack/` を全環境へ配布する。version・commit・内容ハッシュは固定しない。取得と配布前の加工は `nix/modules/home/programs/pstack.nix` で共通管理する。ライセンスは MIT。

`statechart` などの追加skillも、pstackの更新とともに配布する。

| 実行環境 | 配布方式と配置先 |
| --- | --- |
| Codex | native plugin、`~/.codex` |
| OrcaのCodex | activation時に存在する `~/Library/Application Support/orca/codex-accounts/*/home` へnative pluginを登録 |
| Claude Code | native plugin、`~/.config/claude` |
| Pi | `~/.pi/agent/skills/pstack` へ更新可能なskillsをリンク |
| OpenCode | `~/.config/opencode/skills/pstack` へ更新可能なskillsをリンク。tool・agentの追加は行わない |
| Cursor | `~/.cursor/plugins/local/pstack` へ専用版の実ファイルをコピー |

取得した内容は `${XDG_DATA_HOME:-$HOME/.local/share}/pstack` に置く。`marketplace` はnative plugin用、`portable` はPi・OpenCode用、`cursor` はCursor用の配布元となる。native pluginには公式の `plugin.json` をもとに登録用manifestを生成し、skill本文は変更しない。登録済みpluginを引き継ぐため、ローカルmarketplaceの識別子は `pstack-claude` を維持する。native pluginの配布版は上流versionに `-dotfiles.<取得commitの短縮形>` を付ける。同じ上流versionのまま内容が更新されても、Codex・Claude Codeのcacheを更新できる。

`nix run .#switch -- <profile>` で最新版を取得・反映した後、新しいセッションで個別skillを指定する。更新にはGitHubへの接続が必要で、取得に失敗した場合は既存の配布内容を保持してactivationを失敗させる。たとえば「pstackのinterrogateでこの差分をレビューして」と依頼する。Codex・Claude Code・Cursorでは実行時カタログのplugin名を含む名称を使う。Pi・OpenCodeでは `pstack-interrogate` のように接頭辞を付ける。両環境向けには名前の衝突を避けるためfrontmatterの `name` だけを変更し、本文と相対パスを保持する。

公式版にはPi専用extensionがないため、fork由来のextensionは配布しない。PiとOpenCodeはskillの検出までを導入範囲とし、委譲・複数モデルの実行は未検証。公式skill中のCursor用tool名・model名は、現在の環境と既存のモデルsheetへ対応付ける指示をglobalのAGENTS.mdに置く。Claude Codeは同梱の公式adapter `docs/harness/claude-code.md` を読み、Codexはセッションで利用できるtoolへ対応付ける。既存のPi package一覧は変更しない。

Cursorは外部symlinkのpluginを読み込まないため、activationで内容を比較してコピーする。同期対象は `.dotfiles-managed` がある専用ディレクトリに限り、未管理の既存pluginやsymlinkは上書きせずエラーにする。反映にはCursorの再起動またはReload Windowが必要。Enterpriseのlocal plugin制限や、同名のmarketplace版がある場合の優先順位は[Cursorの仕様](https://prod.cursor.com/docs/plugins#test-plugins-locally)に従う。

公式版はSessionStart hookを登録しない。通常のskill選択には各エージェントの既存指示を適用する。fork専用の `session hook` 設定は公式版では使用しない。

`pstack-models.md` は初回だけ初期値をコピーし、再activationでは既存の内容を保持する。Codexは単独処理がgpt-6.1-sol、強い判断がgpt-6-astra、比較・レビューがgpt-6-astraとgpt-6-sol、effortはhigh。Claude Codeは単独処理がopus、比較・レビューがopusとsonnet、effortはsession（親セッションを継承）を初期値とする。

モデル設定の正本は、Codexが `${CODEX_HOME:-$HOME/.codex}/pstack-models.md`、Claude Codeが `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/pstack-models.md`、Piが `${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/pstack-models.md`。各AGENTS.md／CLAUDE.mdがこのsheetを読む。公式skillやClaude Code adapterに記載されたモデルの保存先より、この既存sheetを優先する。OpenCodeのsheetは作成済みの場合だけAGENTS.mdの指示で読む。Cursorは公式の `setup-pstack` を使う。

Orcaのアカウントhomeではplugin登録と初期sheetだけを追加し、認証情報と既存設定は保持する。AGENTS.mdはOrcaが用意する共通指示へのリンクを使う。独自のAGENTS.mdを使う場合は、そのhomeのsheetを読む指示を用意する。activation後に作ったアカウントは、次のswitchで対象になる。これ以外の独自CODEX_HOME・PI_CODING_AGENT_DIRへの配布は手動で行う。
