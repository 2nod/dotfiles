# エージェントの安全設定

Codex と Claude Code で、危ないコマンドの扱いを揃えるための設定。

## ファイルと配置先

| 何 | リポジトリ内 | 配置先 | 配り方 |
|---|---|---|---|
| Codex のコマンドルール | `codex/rules/safety.rules` | `~/.codex/rules/dotfiles-safety.rules` と、Orca の各アカウント home の `rules/dotfiles-safety.rules` | `programs/codex.nix` の activation `installCodexSafetyRules` がコピーする |
| Codex の設定（確認役、sandbox、localhost 用の proxy） | `nix/modules/home/programs/codex.nix` | `~/.codex/config.toml` | activation `writeCodexConfig` が生成する。Orca 側の `config.toml` は生成しない |
| Claude の deny | `nix/modules/home/programs/claude-code/default.nix` の `permissions.deny` | `~/.config/claude/settings.json` | activation が JSON を生成してコピーする |
| エージェント向けの指示 | `codex/AGENTS.md`、`claude/CLAUDE.md` の「クラウド・外部環境」 | `~/.codex/AGENTS.md`、`~/.config/claude/CLAUDE.md` | リポジトリへの symlink |

組織が配る Claude の設定（`~/.config/claude/remote-settings.json`）は管理外。読むだけで、ここからは変えない。

この README は `.rules` ではないので、Codex は読み込まない。

## Codex の判定

`safety.rules` の `prefix_rule` は、コマンドの先頭のトークンを順に比べる。決まり方は 3 つ。

- allow: 確認なしで、sandbox の外で動く
- prompt: 確認役（`approvals_reviewer = "auto_review"`）が判断する
- forbidden: 実行しない

どのルールにも当たらないコマンドは sandbox の中で動く。sandbox から繋がるのは localhost だけなので、外部に繋ぐコマンドは失敗する。その後で昇格を求め、確認役が判断する。

方針:

- クラウドの読み取りは allow にする
- 書き込みは prompt にする
- Secret とトークンを読む操作は forbidden にする

Codex は `rules/*.rules` を全部読み、当たったルールのうち一番厳しいものを使う（forbidden > prompt > allow）。そのため、承認のたびに Codex が書き足す管理外の `rules/default.rules` に allow があっても、`safety.rules` の forbidden と prompt が勝つ。逆に、`safety.rules` に広い prompt（例: `["gcloud"]`）を置くと、読み取りの allow が全部効かなくなる。そこで読み取りも書き込みも、動詞の位置で列挙している。

ルールの `match` / `not_match` は読み込み時に検証される。手で確かめるときは次のようにする。

```sh
codex execpolicy check -r ~/.codex/rules/dotfiles-safety.rules -- gcloud run services describe api
```

## Claude と Codex の対応

| 分類 | Claude | Codex | 差分 |
|---|---|---|---|
| `git push`（全形、force 含む） | deny（組織の設定は ask） | forbidden | Codex は `git -C x push` と絶対パスの git を止められない |
| `--no-verify` | deny（git 全般） | forbidden（commit `-n` を含む、merge/rebase/am/cherry-pick/revert） | Claude の方が広い。`commit -n` を止めるのは Codex だけ |
| `rm -rf` | deny（`-rf`、`-fr`、`*/rm -rf`） | forbidden（フラグの並び 6 通り） | `rm -r -f` はどちらも止められない |
| `terraform apply` / `destroy` | deny | forbidden | 同じ |
| `terraform import` | なし | forbidden | Codex のみ |
| `terraform plan` など | なし | prompt | Codex のみ |
| `prisma migrate reset` | deny | forbidden（npx/yarn/pnpm/bunx 経由も） | 同じ |
| `dropdb` | deny | forbidden | 同じ |
| `mysqladmin` | なし | forbidden | Codex のみ |
| `gcloud auth print-*` | deny | forbidden（identity/access token、`application-default`） | `application-default` は Codex のみ |
| `gh auth token`、`printenv` | deny | forbidden | 同じ |
| `gcloud secrets versions access` | deny（途中に語が入る形も） | forbidden（そのままと alpha/beta） | フラグを先に書いた形は Claude だけが止める |
| `gcloud kms decrypt` | deny | forbidden（`asymmetric-decrypt` も） | `asymmetric-decrypt` は Codex のみ |
| `kubectl get/describe/edit secret` | deny（`kubectl * secret*` も） | forbidden（3 語目が secret のとき） | `-n ns get secret`、`get secret/x` は Claude だけが止める。Codex ではどのルールにも当たらず、sandbox を経て確認役に回る |
| `kubectl create token`、`config view --raw` | deny | forbidden | 同じ |
| `sudo` | ask（組織の設定） | prompt | 同じ |
| npx / bunx | ask は npx だけ（組織の設定） | prompt | bunx は Codex のみ |
| パッケージの install | ask（組織の設定。apt/brew/npm/yarn/pip） | prompt（pnpm/cargo/go/uv なども） | Codex の方が広い |
| クラウドの書き込み（gcloud/kubectl/bq/gsutil） | なし | prompt | Codex のみ。Claude はそのまま動く |
| クラウドの読み取り | なし（動く） | allow | 実質同じ |
| `curl` | なし | prompt | Codex のみ |
| docker / compose の変更系 | なし | prompt | Codex のみ |
| `.env`、`credentials.json` などの読み取り | deny `Read(...)`（組織の設定） | なし | Claude のみ。Codex のルールはファイルの読み取りを書けない |

組織の設定の `terraform apply` の deny は綴りが違う（`terrafrom`）ので効いていない。dotfiles 側の deny で止めている。

## 既知の制約

- どちらも止められないもの:
  - `bash -lc "..."`、`eval`、`xargs` に包んだコマンド
  - `env`、`echo $X`、設定ファイルの `cat` で値を出すこと
  - 対象がどの環境か見分けること（AGENTS.md / CLAUDE.md の指示に頼る）
- Codex は先頭一致だけで判定する。
  - フラグを先に書いた形（`gcloud --project p ...`、`kubectl -n ns get secret x`）と、まとめた指定（`kubectl get pods,secrets`）は forbidden にできない
  - これらは allow にもならず、確認役に回る
- Claude の `*` は広く当たる。`kubectl * secret*` は、名前に secret を含む別のリソースへの操作も止める。
- Claude は `bypassPermissions` で動く。deny は効くが、組織の設定の ask が実際に確認を出すかは確かめていない。
- localhost 用の proxy（`features.network_proxy`）は experimental で、`~/.codex` にだけ入る。
