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
runtimeの`state`は現在の収集状態を示し、ファイルの読取失敗または欠落でpartialになる。
`issues`は保存ログ全体の未対応・不正な記録、`limitations`はシェル構文の解析対象外や分岐履歴の除外を示す。
保存済みの解析不足だけで収集をpartialにはしない。分析CLIと利用履歴にも両者を別々に表示し、根拠参照を保持する。
SwiftBarの「!」は収集停止、読取失敗・欠落、取り込み遅延、DBや解析CLIの異常を示す。
過去ログの解析不足は詳細に残し、取り込み済みという状態から全利用を網羅したと判断しない。
ログの最終観測時刻とcollectorの稼働時刻は別の値である。
何も更新されていない正常な状態を、skill未使用の証拠にはしない。

### 実ログからの評価ケース候補

`usage_cases.py` は分析済みの終了作業から、共有catalogにあるskillと観測パターンごとの候補を作る。
検証失敗、結果未確認、検証成功、通常利用の順に各群から交互に並べる。未終了・旧schema 1・catalog外の名前は対象外。
IDはskillとパターンから安定生成し、件数、最新3作業の参照、併用・版情報の不足を保持する。
パターンの一致は原因の一致ではなく、同じskillの既存ケースも意味上の重複とは判定しない。
シナリオの不足はreadyなケース定義の有無だけを示し、実測や品質の保証には使わない。
ケース一覧の読取エラー時は不足を未確認にする。

分析CLIの `--prepare-cases` は表示件数で切る前の全候補を、収集先の `eval-candidates.json` へ0600でatomic保存する。
期間・skill・入力元の選択を添える。SwiftBarの1分更新もこの操作を呼ぶ。
入力DBが読めないときは更新せず、保存失敗時は前のファイルを保持して失敗を返す。
これは再生成できる候補一覧で、作成済みのレビューやケースを上書きしない。

`--case-proposal ID` は元作業の根拠と未記入の設計欄を返す。
元の会話から実作業・評価準備・期待した失敗を区別し、既存ケースと照合してから合成fixtureと独立したverifierを作る。
終了コードから正解やskillの寄与を生成しない。未修正で失敗、最小修正と別解で成功することを確かめ、dry-runへ渡す。
候補抽出にはモデルを使わず、採点・採否変更・有料比較は実行しない。

### SwiftBarでの表示

常駐表示は `Skills` と現在の収集異常の印だけにする。件数はメニューの先頭で
「N作業 · 直近30日」と期間・単位を付け、nativeでは読み込みを確認できた作業であることを示す。
旧hookを参照している場合は別の説明を出す。取得失敗は未確認とし、利用0件と区別する。

先頭には利用の要約と収集状態、続いて利用内訳・レビュー候補・利用履歴への操作を置く。
正常時のagent別収集状況と、異常時の未読・読取失敗・消失ファイルは収集状態のsubmenuで確認する。
利用内訳にはagent別の件数、利用の多いskill、作業内の検証記録を置く。
検証記録はskillの評価やタスク完了率には変換しない。

「レビューと評価ケース」にログ由来の候補を最大4組示し、`--case-proposal ID` で設計と根拠を開く。
候補の下には元の作業を最大3件示す。作業の見出しは日時・agent・検証状態に絞る。skill名は次の階層へ置き、
候補ごとの `--review-template ID` でその作業の根拠を開く。
長いskill名はSwiftBar標準の `length` で幅を抑え、tooltipに全文を残す。
配置・採否と比較評価のページは「その他のレポート」から開く。

「記録の信頼性」には、直近30日の版情報欠落・検証結果未確認・矛盾する観測と、
保存ログ全体の未対応記録・解析上の制限を別の欄に置く。
異なる範囲を合算した入力エラー総数は、このメニューには出さず分析CLIに残す。
旧ログの場合は「読取対象の旧ログ」と表示し、全期間のnative解析と混同しない。

構成の参考は [CodexBar](https://github.com/steipete/CodexBar) の利用・状態・履歴の分離と、
[Claude Status Touch Bar](https://github.com/korrio/claude-status-touch-bar#menu-bar-widget-swiftbar) の期間付き要約とdashboardへの導線。
描画は [SwiftBar標準の出力形式](https://github.com/swiftbar/SwiftBar#script-output) のsubmenu、SF Symbols、文字サイズ、文字数制限を使う。
重複するAbout・端末実行・plugin更新時刻の標準項目はmetadataで隠し、SwiftBarの管理メニューとplugin無効化は残す。

今後の対象runtimeは、実際の保存形式と合成fixtureを確認して追加する。
Gemini CLIとOpenCodeは未対応。
