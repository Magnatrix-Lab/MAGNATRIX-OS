---
name: gh-address-comments
agent: ops
description: Address review or issue comments on open GitHub PR using gh CLI
schedule: "*/15 * * * *"
---

# gh-address-comments

## Objective
Scan open PRs di repository MAGNATRIX untuk review comments yang belum terjawab. Generate fix/reply dan push changes.

## Steps
1. Gunakan `gh pr list` untuk list open PRs.
2. Untuk setiap PR, gunakan `gh pr view --comments` untuk baca review comments.
3. Identifikasi comments yang unresolved atau belum ada reply.
4. Analyze comment — apakah bug report, suggestion, atau question.
5. Generate code fix atau reply yang sesuai.
6. Jika ada code fix, checkout branch PR, apply fix, commit, push.
7. Jika reply only, post comment via `gh pr comment`.
8. Log actions ke knowledge graph.

## Output
- Summary: {pr_count_scanned, comments_resolved, fixes_applied, timestamp}
- Mesh broadcast: msg_type=PR_COMMENTS_ADDRESSED

## Exit Codes
- SKILL_OK: Semua comments dihandle
- SKILL_PARTIAL: Sebagian dihandle, ada yang blocked
- SKILL_FAIL: Error dengan gh CLI atau repo access
