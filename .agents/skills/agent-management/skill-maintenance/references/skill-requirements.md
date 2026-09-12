# Skillの作成と更新

skillが提供する固有の情報と、扱う依頼を確認してから構成を選ぶ。
指示の取捨選択には [スキルと指示の見直し](../../skill-governance/references/skill-review.md) を使う。

## 配置とmetadata

- `SKILL.md` のfrontmatterに `name` と `description` を置く。
- descriptionは能力と使う場面を短く示す。詳細な手順、類義語の列挙、周辺作業への広い発火条件を含めない。
- 公開pathは `<category>/<skill-name>` の2 segment、名前はlowercase hyphen-caseにする。
- 自作とinstalledで公開pathを重複させない。
- 個人環境の絶対パスを新たに埋め込まず、repo rootまたはskill基準の相対パスを使う。
- 既存の有効なmetadataと呼び出し設定を保持する。必要な場合だけtagsやrelated_skillsを追加する。

## 本文と同梱資料

名前とdescriptionはdiscovery時に提示され、本文はskillを使うときに読まれる。
本文に固定の最低文字数を設けず、目的と固有の制約を伝える長さにする。
一つの短い作業なら単独の `SKILL.md` でよい。
複数の作業モードがある場合は、必要な資料と読む条件が分かる入口にする。

| 内容 | 置き場所 |
|---|---|
| 必要時だけ読む契約、長い例、判断材料 | `references/` |
| コピーして成果物に使う雛形 | `templates/` |
| 繰り返す変換や決定論的な検査 | `scripts/` |
| 成果物へ組み込む固定素材 | `assets/` |

本文から参照先と用途が分かるようにし、同じ説明を重複させない。
使い道がないrouter、空のdirectory、README、quick referenceを作らない。
script化は繰り返し処理や確実な実行が必要な箇所に限り、入力、出力、失敗、再実行、検証方法を定義する。
文書の整理だけで新しいscriptや比較実験を要求しない。

日本語の本文や参照資料を執筆、推敲するときはjapanese-tech-writingを使う。
shared skillにはagent共通の契約を残し、特定モデルの一般的な能力を前提に制約を削除しない。

## 検証

frontmatter、変更した参照先、残す契約との整合を確認する。
descriptionを変更した場合は `.agents/bin/check-skill-triggers` を使うが、語彙上の順位を実際の選択精度とは扱わない。
scriptを変更した場合は、その挙動を確認する。
効果の実証が必要な変更は、対象モデルと実行条件を定めて目的別評価へ進める。

## Installed skill

upstreamの本文と同梱資料を保持し、`SOURCE.md` にrepository、source path、pinned commit、取得元URLを記録する。
ローカル都合の本文修正は別名wrapperかagent固有の指示で扱う。
同名shadowingを導入する場合は、skill-governanceで方針を決め、bundleとdiscoveryの優先順位を実装してから使う。
