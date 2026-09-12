---
name: skill-maintenance
description: shared skillの作成、更新、install、SOURCE.mdのprovenance補完、Codexなどへの配布を依頼されたときに使う。
metadata:
  tags: [skills, dotfiles, maintenance, agents]
---

# Skill Maintenance

依頼されたshared skillをdotfilesで作成、修正、配布する。
パスはrepo rootからの相対で扱う。
自作は `.agents/skills/<category>/<skill-name>`、upstream由来は `.agents/installed-skills/<category>/<skill-name>` に置き、公開pathを重複させない。
installed skillの本文と同梱資料は保持し、出典を `SOURCE.md` へ残す。

## 作業に必要な資料

- 作成や構造の変更: [skill-requirements.md](references/skill-requirements.md)。単純な誤字修正のために全資料を読み直さない。
- 指示の整理やモデル更新に伴う見直し: [スキルと指示の見直し](../skill-governance/references/skill-review.md)。
- install、bundle、配布: [dotfiles-workflow.md](references/dotfiles-workflow.md)。
- 効果比較や採否の判断: [目的別評価](../skill-governance/references/purpose-evaluation.md)。実験を行う場合に `agent-observability/skill-loop.py` を使う。

## 完了まで進める

依頼範囲の編集と必要な検証、その失敗修正まで進め、変更理由と未検証範囲を伝える。
文書保守だけの依頼を有料比較やruntimeへの配布へ広げない。
新規ファイルをNixで検証する場合は対象を明示してstageする。
commit、push、配布は、セッション内で許可された範囲に従う。

配布を行った場合は [check_inventory.py](scripts/check_inventory.py) で配布元と各配布先の名前と同梱内容を照合する。
文書だけの変更は「未配布」と明示し、配布検査を文書修正の前提にしない。
