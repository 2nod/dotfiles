# 正常系の目的達成を先に検証する

対象はinstalledのponytail-reviewとshow-me。本文やwrapperは変更しない。
既存purposeケースは情報不足時の振る舞いを含み、正常系の成功を示す証拠として不足していた。旧結果は保持し、新しいcase IDで比較する。

## ケースと採点

| ケース | 十分に与える材料 | 正常系の成功 |
|---|---|---|
| normal-ponytail-review | 全コード、追加差分、API契約、他callerなし、smoke test | 不要な抽象化・factory・loopを特定し、strip後lowerの等価な簡素化を根拠付きで提案 |
| normal-show-me | 3状態の定義、遷移契機、waitingの捕捉観測 | 図から受付と結果完了の違い、現在位置、結果がない理由が分かる |

purpose、grounding、scopeを成果物とtraceから独立に採点し、各項目へ根拠箇所を残す。AI/人、blind/non-blindの別も残す。
まずskillありの目的達成率を確認し、その後skillなしとの差と使用量を比較する。正常系失敗を情報不足への対応と混ぜない。

## ponytail-reviewの採点例

正解例: labels.pyのLabelOperation、具体operation、OperationFactory、normalize_label内loopを一つの変更として扱い、公開関数をvalue.strip().lower()へ置換する。別の等価な実装も可。smoke testは残す。
元の33行を3行の関数に置換するなら30行削減。部分的な提案ならその範囲で算定する。重複する削除候補を合算しない。数値を示さないことだけでpurposeを不合格にしない。
不正解例: stripを省略する、casefoldへ変える、内部空白を消す、必要なtestを削除する、実在しないplugin利用を断定する。
fixtureのunittestは元実装・最小置換・別の正解で成功し、strip省略とcasefold変更で失敗することを確認済み。レビューの提案を実際に適用して検査する場合は、隔離した複製にのみ適用する。

## show-meの採点例

正解例: waiting（現在・受付済み）からworker開始でprocessingへ、結果保存成功でresultへ進む図。worker未開始なので結果未保存と短く説明する。Mermaid、テキスト図、HTMLのどれでも可。
不正解例: waitingを処理中とする、現在位置をprocessingへ置く、受付時点で結果表示可能とする、状態名を列挙するだけで順序や契機が読めない。
見た目の豪華さや特定キーワードの存在を意味理解の代用にしない。読者理解そのものの改善は、この成果物レビューだけで実証したとはしない。

## 自動検査の範囲

既存purpose-verify.pyを再利用する。成果物なしで失敗、非空成果物で成功、別形式で成功、入力改変で失敗を確認済み。
この検査は意味的に間違った非空文章も通す。正常系の合否を自動検査だけで決めず、上記rubricの証拠付き採点を必須とする。

## 実行

各ケースは--runs 1 --dry-run成功済み。有料モデル比較は未実施。
初回はskill-loopのscreenで各ケース3反復、skillなし/ありの2条件（2ケース合計12回）を事前に固定する。candidateは指定しない。
正常系の成功と追加価値を確認した後に、境界・非適用を含むvalidateへ進む。正常系だけでskill全体を採用・無効化しない。
