# pstack

Home Manager は activation のたびに [michael-denyer/pstack-claude](https://github.com/michael-denyer/pstack-claude) の `main` を取得し、Codex・Claude Code・Pi・OpenCodeへ配布する。Cursorには [cursor/plugins](https://github.com/cursor/plugins/tree/main/pstack) の `main` から専用版を取得する。version・commit・内容ハッシュは固定しない。取得と配布前の加工は `nix/modules/home/programs/pstack.nix` で共通管理する。両方のライセンスは MIT。

`statechart` などの追加skillも、pstackの更新とともに配布する。

| 実行環境 | 配布方式と配置先 |
| --- | --- |
| Codex | native plugin、`~/.codex` |
| OrcaのCodex | activation時に存在する `~/Library/Application Support/orca/codex-accounts/*/home` へnative pluginを登録 |
| Claude Code | native plugin、`~/.config/claude` |
| Pi | `~/.pi/agent/skills/pstack` と `extensions/pstack` へ更新可能なskillsと専用extensionをリンク |
| OpenCode | `~/.config/opencode/skills/pstack` へ更新可能なskillsをリンク。tool・agentの追加は行わない |
| Cursor | `~/.cursor/plugins/local/pstack` へ専用版の実ファイルをコピー |

取得した内容は `${XDG_DATA_HOME:-$HOME/.local/share}/pstack` に置く。`marketplace` はnative plugin用、`portable` はPi・OpenCode用、`cursor` はCursor用の配布元となる。native pluginの配布版は上流versionに `-dotfiles.<取得commitの短縮形>` を付ける。同じ上流versionのまま内容が更新されても、Codex・Claude Codeのcacheを更新できる。

`nix run .#switch -- <profile>` で最新版を取得・反映した後、新しいセッションで個別skillを指定する。更新にはGitHubへの接続が必要で、取得に失敗した場合は既存の配布内容を保持してactivationを失敗させる。たとえば「pstackのinterrogateでこの差分をレビューして」と依頼する。Codex・Claude Code・Cursorでは実行時カタログのplugin名を含む名称を使う。Pi・OpenCodeでは `pstack-interrogate` のように接頭辞を付ける。両環境向けには名前の衝突を避けるためfrontmatterの `name` だけを変更し、本文と相対パスを保持する。

Piのextensionはagent・質問・wake-upのtoolと `/loop` を登録する。初期sheetはopus／sonnet、effortはsessionで、モデルaliasは上流extensionが現在のproviderに応じて解決する。既存のPi package一覧は変更しない。OpenCodeはskillの検出までを導入範囲とし、委譲・複数モデルの実行は未検証。現在のtoolとmodelへ対応付ける指示をglobalのAGENTS.mdに置く。

Cursorは外部symlinkのpluginを読み込まないため、activationで内容を比較してコピーする。同期対象は `.dotfiles-managed` がある専用ディレクトリに限り、未管理の既存pluginやsymlinkは上書きせずエラーにする。反映にはCursorの再起動またはReload Windowが必要。Enterpriseのlocal plugin制限や、同名のmarketplace版がある場合の優先順位は[Cursorの仕様](https://prod.cursor.com/docs/plugins#test-plugins-locally)に従う。

共通パッケージでは `hooks/codex-hooks.json` と `hooks/hooks.json` の登録を空にする。Codex・Claude CodeのSessionStartから常時ルーティング指示を注入しない。`setup-pstack` でsheetのhook値を変更しても、この2つのhookは有効にならない。Piは初期sheetの `session hook: off` でルーティングを止め、extensionによるtool対応表の案内とsheetの読み込みは続ける。Piでこの値をonに変更するとルーティングが有効になる。Cursor版にはSessionStart hookがない。通常のskill選択には各エージェントの既存指示を適用する。

`pstack-models.md` は初回だけ初期値をコピーし、再activationでは既存の内容を保持する。Codexは単独処理がgpt-6.1-sol、強い判断がgpt-6-astra、比較・レビューがgpt-6-astraとgpt-6-sol、effortはhigh。Claude Codeは単独処理がopus、比較・レビューがopusとsonnet、effortはsession（親セッションを継承）を初期値とする。

モデル設定の正本は、Codexが `${CODEX_HOME:-$HOME/.codex}/pstack-models.md`、Claude Codeが `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/pstack-models.md`、Piが `${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/pstack-models.md`。各AGENTS.md／CLAUDE.mdまたはPi extensionがこのsheetを読む。sheetを編集するか `setup-pstack` で変更する。OpenCodeのsheetは作成済みの場合だけAGENTS.mdの指示で読む。Cursorは専用版の設定手順を使う。`setup-pstack` が指示ファイルにモデル行やincludeを保存すると、Home Managerのリンク先であるこのリポジトリの指示ファイルも変更される。

Orcaのアカウントhomeではplugin登録と初期sheetだけを追加し、認証情報と既存設定は保持する。AGENTS.mdはOrcaが用意する共通指示へのリンクを使う。独自のAGENTS.mdを使う場合は、そのhomeのsheetを読む指示を用意する。activation後に作ったアカウントは、次のswitchで対象になる。これ以外の独自CODEX_HOME・PI_CODING_AGENT_DIRへの配布は手動で行う。
