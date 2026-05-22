---
name: deploy-pipeline
agent: ops
description: Manage deployment pipeline: build, test, deploy ke staging/production
schedule: "*/10 * * * *"
---

# deploy-pipeline

## Objective
Orchestrate full deployment pipeline untuk MAGNATRIX: build artifacts, run integration tests, deploy ke staging, promote ke production jika test pass.

## Steps
1. Poll git untuk new commits di main branch.
2. Trigger build: docker-compose build atau language-specific build.
3. Run test suite: unit tests, integration tests, security scan.
4. Jika semua pass, deploy ke staging environment.
5. Run smoke tests di staging: health checks, API tests.
6. Jika smoke tests pass, broadcast ke mesh untuk guardian approval.
7. Jika approved (atau auto-promote enabled), deploy ke production.
8. Monitor production untuk 10 menit post-deploy: error rate, latency.
9. Jika anomaly detected, trigger automatic rollback.
10. Log semua ke knowledge graph.

## Output
- Pipeline report: {build_id, commit, test_results, staging_status, production_status, rollback_triggered}
- Mesh broadcast: msg_type=DEPLOY_COMPLETE atau msg_type=DEPLOY_ROLLBACK

## Exit Codes
- SKILL_OK: Deploy production berhasil, monitoring green
- SKILL_PARTIAL: Deploy staging berhasil, production pending approval
- SKILL_FAIL: Build/test fail atau deploy error, rollback executed
