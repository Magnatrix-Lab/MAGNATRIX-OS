---
name: gh-fix-ci
agent: ops
description: Inspect failing GitHub Actions checks, summarize failures, propose fixes
schedule: "*/10 * * * *"
---

# gh-fix-ci

## Objective
Monitor GitHub Actions CI pipeline untuk repo MAGNATRIX. Deteksi failing checks, diagnose root cause, dan apply fix otomatis atau buat PR.

## Steps
1. Query GitHub API untuk latest workflow runs: `gh run list --limit 20`.
2. Identifikasi runs dengan status failure/cancelled.
3. Ambil logs dari failing job: `gh run view --log-failed RUN_ID`.
4. Analyze error pattern: compile error, test failure, lint error, dependency issue.
5. Search codebase untuk file yang terkait error.
6. Generate fix: patch, config update, atau dependency version bump.
7. Jika fix aman (testable), apply dan push ke branch fix-ci-{run-id}.
8. Buat PR dengan summary error dan fix description.
9. Broadcast ke mesh untuk guardian review jika critical path affected.

## Output
- CI report: {failing_runs, root_causes, fixes_applied, pr_created}
- Mesh broadcast: msg_type=CI_FIXED atau msg_type=CI_ALERT

## Exit Codes
- SKILL_OK: CI failures diagnosed dan fixed
- SKILL_WARN: Failures identified tapi fix memerlukan manual review
- SKILL_FAIL: Error query GitHub API atau repo access denied
