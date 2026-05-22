---
name: issue-triage
agent: ops
description: Triage GitHub issues dengan kategorisasi, priority scoring, dan routing ke agent
schedule: "*/20 * * * *"
---

# issue-triage

## Objective
Auto-triage GitHub issues untuk repo MAGNATRIX: kategorisasi bug/feature/security, priority scoring, dan assign ke agent yang sesuai.

## Steps
1. Fetch open issues dari GitHub API: `gh issue list --limit 50`.
2. Untuk setiap issue, extract: title, body, labels, assignees, comments count, age.
3. Klasifikasi issue: bug, feature-request, security, documentation, question.
4. Priority scoring:
   - Critical: security, crash, data loss → score 10
   - High: bug affecting core functionality → score 7
   - Medium: feature request dengan banyak votes → score 4
   - Low: typo, docs → score 2
5. Route ke agent:
   - security → guardian
   - bug/crash → ops + architect
   - feature → analyst untuk feasibility check
   - docs → writer
6. Apply label dan assign ke agent virtual account.
7. Generate triage report.
8. Broadcast ke mesh.

## Output
- Triage report: {issues_scanned, categorized_by_type, priority_distribution, assigned_agents}
- Mesh broadcast: msg_type=ISSUE_TRIAGE_COMPLETE

## Exit Codes
- SKILL_OK: Triage selesai, issues routed
- SKILL_FAIL: GitHub API error
