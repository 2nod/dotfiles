---
name: ask-claude
description: 別 agent である Claude Code に相談してセカンドオピニオンを得る。実装方針・設計・コードレビュー・詰まった問題について、重要な判断の前に独立した視点が欲しいときに使う。ユーザーが「Claude に聞いて」「Claude の意見は？」「別の agent の見解が欲しい」と依頼したときにも使う。
metadata:
  tags: [agents, consultation, claude, second-opinion]
  related_skills:
    - agent-management/ask-codex
---

# Ask Claude

別 agent である Claude Code に相談し、独立したセカンドオピニオンを得るための skill。
自分の分析を Claude の見解と突き合わせ、両論をユーザーに提示する。

## まず: 自分はどの agent か

この skill は複数 agent で共有される。今動いている session に合わせて経路を選ぶ。

- **自分が Claude ではない**（Codex など）→ 下記の [Claude CLI 経路](#claude-cli-経路) を使う。`claude -p` に shell out することで、別 engine からの独立した視点が得られる。
- **自分が Claude**（Claude Code session）→ `claude -p` で自分自身を呼び直すのは無意味。shell out せず、subagent に投げるか、そのまま自分で答える。

## Claude CLI 経路

Claude Code を非対話（print）モードで実行する:

```bash
claude -p "ここに相談内容"
```

### モデル選択

**既定では `--model` を指定しない。** Claude Code の設定（`~/.config/claude/settings.json`）のモデルに任せることで、ユーザーの設定と一貫させる。ユーザーが特定モデルを明示的に求めたときだけ指定する:

```bash
claude -p --model MODEL "ここに相談内容"
```

## 相談の手順

1. **問いを組み立てる**: Claude は自分の会話履歴を共有していないので、判断に必要な背景・制約・対象コードを自己完結した prompt にまとめる。
2. **相談を実行する**: `claude -p` を上記の prompt で走らせる。
3. **批判的に評価する**: 返答を鵜呑みにしない。自分の分析やコードベースの実情と突き合わせる。
4. **統合する**: 自分の元の見解と Claude の見解を、一致点・相違点を明示してユーザーに提示する。最終判断はユーザーに委ねる。

## 使いどころ

- 重要な設計上の決定に踏み切る前
- 問題に詰まっていて、別の視点が欲しいとき
- 複雑な計画を検証したいとき
- ユーザーが明示的にセカンドオピニオンを求めたとき

## 注意

- prompt には十分な背景を必ず含める（相手は会話を見ていない）。
- prompt は焦点を絞る。コードベース全体を丸ごと渡さない。
- 返答は「一つのデータ点」であって権威ある正解ではない。
- Claude の助言がプロジェクトの既存パターンと衝突する場合は、既存パターンを優先する。
- 両方の見解を透明にユーザーへ報告する。
