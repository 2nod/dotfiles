# Skill Scout Audit Checklist

## ローカル inventory

- `.agents/skills` と `.agents/installed-skills` の `SKILL.md` を列挙する。
- 各 `SKILL.md` に `name` と `description` の frontmatter があるか確認する。
- `description` が「何の skill か」だけでなく「いつ使うか」を説明しているか確認する。
- 自作 skill と installed skill の公開 path が衝突していないか確認する。
- 参照されている `references/`, `templates/`, `scripts/`, `assets/` が存在するか確認する。
- installed skill に `SOURCE.md` があるか確認する。

## 品質シグナル

- Trigger overlap: 同じ依頼文で複数 skill が発火しそう。
- Thin skill: description や本文が曖昧で、使いどころを判断しにくい。
- Bloated skill: `SKILL.md` 本体に、長い例・template・checklist が入りすぎている。
- Missing validation: ファイル変更や判断を伴うのに、検証手順がない。
- Unsafe automation: 明示承認なしで state-changing action を促している。

## 安全シグナル

installed skill と外部由来の skill では、次の項目を優先して確認する。

- `scripts/` や実行可能ファイルが同梱されている。
- `curl`, `wget`, `gh`, `gcloud`, `docker`, `ssh`, package manager など、外部通信や外部 system に触れる command を促している。
- token、credential、secret、cookie、SSH key、環境変数、認証ファイルを読む指示がある。
- `rm`, `mv`, `chmod`, `chown`, `git push`, deploy、DB 更新など、state-changing command を促している。
- source、pinned commit、取得元 URL が `SOURCE.md` で確認できない。

該当する場合は、ただちに危険と断定せず、何が危険面になり得るか、どの承認や隔離が必要かを report に書く。

## skill 化シグナル

次のうち 2 つ以上が当てはまるなら、skill 化候補として扱う。

- ユーザーが同じタスクや言い回しを繰り返している。
- 複数の command、tool、判断ステップをまたぐ。
- checklist、template、script があると安定する。
- 複数 repo または複数 agent で使える。
- 明示的な guardrail がないとミスしやすい。

次の場合は skill 化を避ける。

- 一回きりの project knowledge である。
- 既存 skill に吸収した方がよい。
- 安全に記述しにくい、変動しやすい private state に依存している。

## 外部シグナル

次の情報源から候補を探す。

- Codex の公式 documentation / changelog
- Claude Code の公式 documentation / changelog
- Cursor と MCP ecosystem の更新
- agent workflow に関する信頼できる engineering post
- skill ecosystem、agent safety、eval、automation loop に関する論文や report

流行そのものではなく、この dotfiles repo の反復作業に対応するものだけを local proposal にする。
