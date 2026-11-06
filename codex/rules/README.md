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

- 通常の開発操作、パッケージ取得、HTTP通信、Docker、列挙したクラウド操作は allow にする
- 既存のDB削除などの破壊操作、Secret・トークンの直接表示は forbidden にする
- sudo は prompt にする
- `git push` はallowとし、push・PR作成はユーザーが明示依頼または承認した範囲で行う。PR作成の依頼は必要なcommit・pushの承認を含む
- 外部書き込みはdevと判別できる場合だけ実行する。stg/prodと環境不明時は禁止する。この環境判定はルールではなくAGENTS.mdの指示で行う
- `terraform apply` / `destroy` はdevでも、対象とplanの差分をチャットで提示し、その内容への明示承認を待つ。通常操作のallowは維持する

Gitのpush・PR作成とTerraformの事前承認は `codex/AGENTS.md` の実行手順であり、ルールが機械的に強制する確認ではない。`allow` や自動承認レビューの通過をユーザーの承認として扱わない。実行基盤が `AskForApproval=Never` の場合に `prompt` を置くと実行できなくなるため、ここではコマンド許可とチャットでの事前承認を分ける。

Codex は `rules/*.rules` を全部読み、当たったルールのうち一番厳しいものを使う（forbidden > prompt > allow）。管理外の `rules/default.rules` に allow があっても、`safety.rules` の forbidden と prompt が勝つ。通常操作を止める広いpromptは置かず、既存のDB削除・Secret表示・権限昇格などの制限を残す。

`allow` は通常設定の `workspace-write` でsandbox外実行を許可するために残す。`danger-full-access` のセッションでは追加のallowは不要だが、通常設定との共用を続ける。allowルールには説明文を重ねず、実行条件はAGENTS.mdにまとめる。

ルールの `match` / `not_match` は読み込み時に検証される。手で確かめるときは次のようにする。

```sh
codex execpolicy check -r ~/.codex/rules/dotfiles-safety.rules -- gcloud run services describe api
```

## Claude と Codex の対応

| 分類 | Claude | Codex | 差分 |
|---|---|---|---|
| `git push`（force 含む） | deny（組織の設定は ask） | allow + AGENTS.mdで承認範囲を確認 | PR作成依頼は必要なpushの承認を含む。force pushは対象と操作への別途明示承認が必要 |
| `--no-verify` | deny（git 全般） | forbidden（commit `-n` を含む、merge/rebase/am/cherry-pick/revert） | Claude の方が広い。`commit -n` を止めるのは Codex だけ |
| `rm -rf` | deny（`-rf`、`-fr`、`*/rm -rf`） | forbidden（フラグの並び 6 通り） | `rm -r -f` はどちらも止められない |
| `terraform apply` / `destroy` | deny | allow + AGENTS.mdで事前承認 | devと確認した対象とplanを提示し、明示承認後に実行する。承認UIによる強制ではない |
| Terraformの通常操作（init/validate/plan/workspace/state/importなど） | なし（動く） | allow | 外部書き込みはdevのみ。Secret・トークンを含む値は表示しない |
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
| npx / bunx | ask は npx だけ（組織の設定） | allow | Codexでは通常のツール実行を許可 |
| パッケージの install | ask（組織の設定。apt/brew/npm/yarn/pip） | allow（pnpm/cargo/go/uv なども） | Codexでは開発用の依存取得を許可 |
| クラウドの書き込み（gcloud/kubectl/bq/gsutil） | なし | allow | devのみ実行可。stg/prod・環境不明時は禁止という指示を適用 |
| クラウドの読み取り | なし（動く） | allow | 実質同じ |
| `curl` | なし | allow | 外部書き込みとSecret表示の指示は適用 |
| docker / compose の変更系 | なし | allow | 開発操作を許可。既存データの削除は依頼範囲内に限定 |
| `.env`、`credentials.json` などの読み取り | deny `Read(...)`（組織の設定） | なし | Claude のみ。Codex のルールはファイルの読み取りを書けない |

Claude Codeの組織の設定では `terraform apply` の deny の綴りが違う（`terrafrom`）ので効いていない。Claude Codeではdotfiles側のdenyで止めている。

## 既知の制約

- どちらも止められないもの:
  - `bash -lc "..."`、`eval`、`xargs` に包んだコマンド
  - `env`、`echo $X`、設定ファイルの `cat` で値を出すこと
  - 対象がどの環境か見分けること（AGENTS.md / CLAUDE.md の指示に頼る）
- Codex は先頭一致だけで判定する。
  - Terraformは通常のサブコマンドをallowとして列挙する。`-chdir=...` を先に書く形や未知のサブコマンドには一致せず、sandboxと確認役の判定に従う。ディレクトリは実行ツールの作業ディレクトリ指定で切り替える
  - allowは環境や出力内容を識別しない。書き込みはdevのみ、stg/prodと環境不明時は禁止、Secret・トークンは表示しないというAGENTS.mdの指示を実行時に適用する
  - Terraformのapply/destroyもルール上は全環境でallowとなる。AGENTS.mdの手順でdevの対象とplanを提示し、明示承認を待つ。対象やplanが変われば再確認する。backendや接続先project/accountなどを照合し、workspace名だけで環境を断定しない。stg/prodへの書き込みを機械的に防ぐには、認証情報や権限も環境別に分離する
  - フラグを先に書いた形（`gcloud --project p ...`、`kubectl -n ns get secret x`）と、まとめた指定（`kubectl get pods,secrets`）は forbidden にできない
  - これらは allow にもならず、確認役に回る
- Claude の `*` は広く当たる。`kubectl * secret*` は、名前に secret を含む別のリソースへの操作も止める。
- Claude は `bypassPermissions` で動く。deny は効くが、組織の設定の ask が実際に確認を出すかは確かめていない。
- localhost 用の proxy（`features.network_proxy`）は experimental で、`~/.codex` にだけ入る。
