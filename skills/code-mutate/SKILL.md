---
name: code-mutate
agent: architect
description: Mutasi kode untuk self-improvement dengan test validation
schedule: "0 */6 * * *"
---

# code-mutate

## Objective
Identifikasi bottleneck dan mutate kode MAGNATRIX untuk performance improvement. AST-based mutation dengan test-suite validation.

## Steps
1. Scan codebase untuk performance bottleneck (slow functions, memory leaks).
2. Generate AST mutations: loop unroll, memoization, algorithm substitution.
3. Jalankan test suite untuk setiap mutation.
4. Compare benchmark: jika mutation improves speed > 10% tanpa breaking tests, accept.
5. Apply mutation dan commit dengan auto-commit message.

## Output
- Mutation report: {mutations_attempted, mutations_accepted, performance_delta, tests_passed}
- Broadcast EVOLVE_COMPLETE ke mesh

## Exit Codes
- SKILL_OK: Mutations applied successfully
- SKILL_NO_IMPROVEMENT: No beneficial mutations found
- SKILL_FAIL: Error dalam mutation atau tests fail
