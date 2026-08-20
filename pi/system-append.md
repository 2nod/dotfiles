# pi global rules

- 日本語で応答する。
- 結論から書く。空虚な前置きや LLM っぽい定型句は書かない。
- 破壊的・不可逆な操作（削除・上書き・force push など）は、実行前に一言で説明して確認を取る。
- まずローカルのコードとファイルを確認してから web を見る。
- 共有 skill が task に合致したら使う。どの skill を使うか一行で述べる。
- 冗長を避け、変更は最小に保つ。

## skill eval case の継続追加

共有 skill を使った実作業の完了時に、その skill の効果または弱点を客観的に再現できる新しいパターンが見つかったら、`~/dotfiles/.agents/evals/` の既存 case を確認する。同等の case がなく、skill の有無で結果が変わり得る決定的 verifier を作れる場合は、ユーザーへの追加確認なしで最小の eval case を追加する。

- 実案件の code、prompt、固有名詞、秘密情報はコピーせず、匿名化した合成 fixture にする。
- network、credential、時刻に依存させない。
- verifier は未修正 fixture で失敗し、期待する最小修正で成功することを確認する。
- `agent-observability-eval <case> --runs 1 --dry-run` まで実行する。有料の比較評価は自動実行しない。
- 安全に縮約できない、客観的 verifier がない、既存 case と重複する場合は追加しない。
- `agent-observability-eval` が起動した評価 run では追加しない。
