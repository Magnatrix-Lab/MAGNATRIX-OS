---
name: security-audit
agent: researcher
description: Full whitebox security audit dengan OpenHack methodology
schedule: "0 2 * * *"
---

# security-audit

## Objective
Jalankan full whitebox security review pada target repository menggunakan OpenHack methodology (Hadrian). Workflow: init-run → recon → scenarios → expert proof → triage → findings.

## Steps
1. Tentukan target repository dan expert scope (12 OWASP/MITRE families).
2. Jalankan `openhack_bridge.init_run()` untuk clone dan setup workspace.
3. Jalankan `openhack_bridge.run_recon()` untuk discover routes, inputs, sinks, auth boundaries, exposures.
4. Jalankan `openhack_bridge.create_scenarios()` untuk generate router prompt.
5. Dapatkan router answer (via LLM) dan record scenario backlog.
6. Untuk setiap scenario, render prompt dan kirim ke expert agent via FreeLLM Router.
7. Record scenario result dan materialize finding candidates.
8. Untuk setiap candidate, render triage prompt dan kirim ke triage agent.
9. Record triage decision — accepted/downgraded → materialize finding markdown.
10. Export findings ke Knowledge Graph dan broadcast ke Mesh.
11. Jika critical finding detected, broadcast HALT ke swarm untuk review.

## Output
- Full findings report di `offensive/runs/<target>/<run-id>/findings/`
- Knowledge graph entities: `type=security_finding`
- Mesh broadcast: `msg_type=SECURITY_AUDIT_COMPLETE`
- Critical alert: `msg_type=HALT` jika severity=critical

## Exit Codes
- SKILL_OK: Audit complete, findings materialized
- SKILL_PARTIAL: Audit complete dengan beberapa scenario failed
- SKILL_FAIL: Error dalam workflow atau recon gagal
