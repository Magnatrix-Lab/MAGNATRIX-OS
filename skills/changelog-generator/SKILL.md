---
name: changelog-generator
agent: writer
description: Generate clear changelogs dari commits atau summaries
schedule: "0 0 * * 0"
---

# changelog-generator

## Objective
Generate weekly changelog untuk MAGNATRIX dari git commits dan PR merges. Format: Keep a Changelog standard.

## Steps
1. Query git log untuk period (default: seminggu terakhir).
2. Group commits by category: Added, Changed, Deprecated, Removed, Fixed, Security.
3. Filter noise commits: merge commits, dependency bumps (kecuali security-related).
4. Summarize setiap grup menjadi human-readable entries.
5. Extract breaking changes dan flag dengan BREAKING label.
6. Format sebagai CHANGELOG.md section.
7. Cek apakah ada security fixes yang perlu urgent publish.
8. Commit changelog dan broadcast ke mesh.

## Output
- CHANGELOG.md update
- Summary: {entries_count, breaking_changes, security_fixes}
- Mesh broadcast: msg_type=CHANGELOG_PUBLISHED

## Exit Codes
- SKILL_OK: Changelog generated dan committed
- SKILL_FAIL: Error query git atau no commits in period
