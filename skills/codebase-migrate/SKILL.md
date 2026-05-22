---
name: codebase-migrate
agent: ops
description: Migrate codebase antara versi, framework, atau language dengan planning dan validation
schedule: "0 0 * * 0"
---

# codebase-migrate

## Objective
Plan dan execute codebase migration untuk MAGNATRIX. Support: version upgrade (Python, Node), framework migration, dependency replacement, structural refactor.

## Steps
1. Terima migration request: {target, source_version, target_version, scope}.
2. Scan codebase untuk identify affected files dan breaking changes.
3. Research migration guide untuk target framework/version.
4. Generate step-by-step migration plan dengan rollback strategy.
5. Execute migration per module — test suite harus pass setelah setiap step.
6. Jika test fail, rollback dan adjust plan.
7. Update documentation dan changelog.
8. Commit dengan message: `migrate: {scope} {source} → {target}`.
9. Broadcast ke mesh untuk swarm awareness.

## Output
- Migration report: {scope, files_changed, tests_status, rollback_available}
- Commit hash dan branch reference
- Mesh broadcast: msg_type=CODEBASE_MIGRATED

## Exit Codes
- SKILL_OK: Migration selesai, all tests pass
- SKILL_PARTIAL: Migration selesai dengan known issues documented
- SKILL_FAIL: Migration aborted, rollback executed
