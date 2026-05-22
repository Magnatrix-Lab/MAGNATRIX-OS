---
name: repo-health
agent: ops
description: Monitor repository health, CI status, dependency audit
schedule: "*/10 * * * *"
---

# repo-health

## Objective
Monitor health repository MAGNATRIX: CI pipeline, dependency vulnerabilities, disk space, test status.

## Steps
1. Cek status terakhir CI/CD pipeline (GitHub Actions atau self-hosted).
2. Jalankan dependency audit dengan safety atau npm audit.
3. Cek disk space dan log rotation.
4. Verifikasi backup integrity.
5. Generate health report dan broadcast OPS_STATUS ke mesh.

## Output
- JSON: {ci_status, vulnerabilities, disk_usage_pct, backup_ok, overall_health}
- Broadcast OPS_STATUS ke mesh

## Exit Codes
- SKILL_OK: Repo healthy
- SKILL_WARN: Ada warning tapi tidak critical
- SKILL_FAIL: Critical issue detected
