---
name: one-api-management
agent: ops
description: Manage One-API channels, keys, and monitor LLM provider health
schedule: "*/10 * * * *"
---

# one-api-management

## Objective
Monitor dan manage One-API LLM gateway (songquanpeng/one-api) yang digunakan MAGNATRIX sebagai primary API router. Pantau channel health, usage, dan auto-rotate key jika perlu.

## Steps
1. Cek One-API status via /api/status.
2. List active channels dan model availability.
3. Cek usage per channel — identify yang rate limit approaching.
4. Jika channel error rate > 20%, flag untuk ops review.
5. Jika semua channel down, broadcast ke mesh untuk fallback ke FreeLLMRouter.
6. Log analytics ke knowledge graph.

## Output
- JSON report: {status, channels_count, models_available, total_usage_today, alerts}
- Mesh broadcast: msg_type=ROUTER_STATUS
- Knowledge entity: type=llm_router_status

## Exit Codes
- SKILL_OK: One-API healthy, report generated
- SKILL_WARN: Ada channel issues tapi masih operational
- SKILL_FAIL: One-API unreachable atau semua channel down
