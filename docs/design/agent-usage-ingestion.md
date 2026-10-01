# エージェントの保存ログから利用を観測する

Codex、Claude Code、Piが通常保存する会話ログをローカルで読み、skillの見直しに必要なメタデータへ変換する。
分析用hookやPi拡張の登録は不要で、trust設定にも依存しない。
会話の本文をモデルへ送信したり、skillを自動修正したり、有料評価を起動したりはしない。

## 入力と保存

`collect-usage.py` が既知の保存先を探索し、`usage_native.py` がruntime別の形式を解析する。
既定の対象は通常のCodex homeとOrcaのruntime/account home、Claude Codeのprojects、Piのsessions。
各runtimeのhome環境変数にも対応する。
対象を限定する場合は `~/.config/agent-observability/sources.json` にruntime名からディレクトリ配列への対応を書く。
指定ファイルがある場合は既定値と混ぜず、その内容だけを使う。空配列や省略されたruntimeは未設定になる。

`usage_store.py` が `~/.local/share/agent-observability/usage.sqlite3` に観測と読取位置を保存する。
環境変数 `AGENT_OBSERVABILITY_DIR` またはCLIの `--root` で派生データの保存先を変更できる。
DBはユーザーだけが読める権限で作成する。
会話の本文、推論、コマンド全文、tool出力は複製しない。
projectは表示用basenameとpathのhashを持つ。
根拠の参照には元ログのpath、行番号、行内容のSHA-256を残す。
元ログを削除すると、派生記録は残るが根拠本文へ戻れなくなる。

## 増分処理と再実行

SQLiteの同一transactionで観測とcheckpointを更新し、processの中断で二重加算しない。
writer lockによりcollectorの同時実行を避ける。
既定の1回の処理量は256MiB、1ファイルの処理単位は32MiB、時間の目安は45秒。
1行の読み取り完了まで進めるため、上限を厳密な実行時間保証としては扱わない。
大きな初回取り込みは複数回に分け、処理済みのログは追記分だけを読む。

ファイル置換、縮小、先頭とcheckpoint付近のhash変化、同サイズでの更新、parser版の変更で再解析する。
再解析が完了するまでは前の世代を参照し、完了時に世代を切り替える。
追記型ログが契約であり、サイズが増えると同時に中間部分だけを書き換える形式は完全には検出できない。
そのようなruntimeへ対応する場合は別の変更検知が必要になる。

最後の改行がない行は書き込み途中として待つ。
途中の不正JSON、未対応形式、16MiBを超える活動記録は欠落理由を記録する。
巨大な行は一定量ずつ読み飛ばし、後続の処理を継続する。
外側のtypeを確認できる圧縮履歴（`compacted`）は、解析対象の活動記録ではないため欠落に数えない。
ファイル単位の読取エラーは他ファイルから分離する。
元ログが消えても保存済みの観測を自動削除しない。

同じruntime、session、actor、native IDの観測は複数保存先から読んでも一つにする。
開始・終了の観測で時刻だけが違う複製は、開始には最早時刻、終了には最遅時刻を使い、両方の根拠参照を残す。
同一IDで内容が矛盾する場合は集計から外し、入力エラーへ残す。
分岐元の範囲を検証できないfork履歴は `branch_unverified` とし、skill利用回数から除く。
fork後の新規作業だけを切り出すことは現時点の対応範囲に含まない。

## 証拠の強さ

新しい観測はschema 3。
runtime、actor、turn、モデル、観測時刻、parser版、native IDと取り込み時刻を保持する。
Claude CodeとPiのturnはユーザーメッセージを起点とする推定IDとして区別する。
Piのentry treeと呼出IDを使い、分岐や後着の結果を現在のturnへ誤って付けない。
tool結果は呼出時のturnとモデルへ対応付ける。

skillは明示指定、読取要求、読取確認を分ける。
利用回数に含めるのは読取を確認できた作業だけで、要求と指定の件数は別に表示する。
読めたことは指示の適用や有用性の証明ではない。
過去のskill版を現在のファイル内容から補わない。

Codexでは構造化されたCommandExecutionと古い直接tool呼出を読む。
外側のJavaScriptやshellを実行せず、構造化された内側の実行結果を優先する。
ラッパーより先に内部形式が判明しない場合は、対応する応答まで確認を保留する。
内部のCommandExecutionが確認できたラッパー、ファイル編集、単独のFunctionCallOutputは未対応の入力に数えない。
内部の実行結果がない旧ラッパーは未対応として残す。外側の出力本文から読み込み成功を推測しない。
Claude CodeとPiはtool_use/toolCallと対応するtool_result/toolResultを読む。
Claude CodeのReadは構造化されたfile結果も読取の根拠にする。
単純な読取コマンドを解析し、変数展開、command substitution、heredocの実行や推定はしない。
複合コマンドでは個別の読取成功を確定しない。

検証の成功は構造化された終了コードやdiagnosticsから判定する。
「テスト成功」という出力文や、会話終了だけから成功を推測しない。
Claude CodeとPiのログに終了コードがないtest/buildは未確認になる。
schema 3では検証呼出ごとの結果を保持し、並行した別の検証で失敗を上書きしない。

## 分析と運用

`usage_input.py` を分析CLIと既存レポートの共通readerにする。
`--source auto` はDBがあればnative、なければ旧hookの保存記録を選ぶ。
`--source native` と `--source legacy` で対象を固定できる。
両者の件数や版を混ぜず、DB異常時に旧記録へ自動で切り替えない。

Home Managerがuser launchd agentを配布し、ログイン時と60秒ごとにcollectorを起動する。
配布するCLIもNixの同じPythonを指定し、shellのPATHによって処理系が変わらないようにする。
スリープ中の即時収集は保証せず、復帰後に追いつく。
collectorの最終開始と正常完了を保存し、doctorとSwiftBarが独立して鮮度を確認する。
180秒を超えて開始も完了も更新されない場合は停止の疑いとして表示する。

doctorは未設定、保存元未発見、収集停止、未読の追記、書きかけの行、解析の欠落を分ける。
`issues`は未対応形式や読取エラー、`limitations`はシェル構文の解析対象外や分岐履歴の除外を示す。
後者だけで収集をpartialにはしない。分析CLIと利用履歴にも両者を別々に表示し、根拠参照を保持する。
古い未対応形式が残る間はpartial表示が続くため、未読bytesと最終収集時刻も併せて確認する。
ログの最終観測時刻とcollectorの稼働時刻は別の値である。
何も更新されていない正常な状態を、skill未使用の証拠にはしない。

今後の対象runtimeは、実際の保存形式と合成fixtureを確認して追加する。
Gemini CLIとOpenCodeは未対応。
