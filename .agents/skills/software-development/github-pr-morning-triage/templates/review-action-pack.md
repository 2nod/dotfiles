# Review Action Pack

## {{pr_title}}

Target: {{pr_url}}

Comment: {{comment_url}}

Status:
- Review: {{review_state}}
- CI: {{ci_state}}
- Mergeability: {{mergeability}}
- Dependency: {{dependency_state}}

Asked:
- {{asked}}

Decision Needed:
- {{decision_needed}}

Likely Work Area:
- Repo: {{repo}}
- Branch: {{branch}}
- Base: {{base_branch}}
- Files / packages: {{files_or_packages}}
- Tests: {{tests}}

Session:
- {{codex_session}}

Start Prompt:

```text
{{repo}} の PR #{{pr_number}} の review 対応をしてください。

対象コメント:
- {{comment_url}}

確認してほしいこと:
- {{asked}}

前提:
- base/head: {{base_branch}} <- {{branch}}
- 依存 PR: {{dependency_state}}
- CI: {{ci_state}}
- review: {{review_state}}

進め方:
1. PR diff と対象コメントを確認
2. 必要なら関連 PR も確認
3. 修正案または返信方針を整理
4. 実装が必要なら最小変更で対応
5. 実行した確認と reviewer 返信案を出す
```

Reply Draft:

```text
{{reply_draft}}
```
