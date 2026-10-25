# pstack

- pstackのskill名は `pstack-` で始まる。skill内の別skillへの参照も、この接頭辞を付けた名前で読み込む。
- pstackはskills-onlyで導入している。Claude固有のtoolやmodel名をそのまま使わず、現在のOpenCodeにある機能へ対応付ける。独立したレビューが必要なのにsubagentを利用できない場合は、その制約を報告する。
- pstackを使う前に、`~/.config/opencode/pstack-models.md` があれば読む。モデルとeffortはこのsheetを優先し、指定できない値を黙って別の値へ置き換えない。
