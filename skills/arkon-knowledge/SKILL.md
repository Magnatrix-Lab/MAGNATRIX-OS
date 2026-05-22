---
name: arkon-knowledge
agent: researcher
description: Manage enterprise knowledge hub via Arkon MRP pipeline
schedule: "*/20 * * * *"
---

# arkon-knowledge

## Objective
Operasikan Arkon Knowledge Hub untuk MAGNATRIX: ingest dokumentasi, manage wiki pages, enforce RBAC, dan expose knowledge via MCP ke seluruh swarm.

## Steps
1. Cek Arkon health dan workspace availability.
2. Poll untuk pending reviews yang perlu approval.
3. Auto-ingest dokumentasi baru dari MAGNATRIX repo ke wiki.
4. Update knowledge graph visualization.
5. Enforce RBAC: verify agent hanya access scope yang diizinkan.
6. Query knowledge untuk swarm requests via semantic search.
7. Export wiki entities ke MAGNATRIX Knowledge Graph.
8. Log semua privileged actions ke audit trail.
9. Broadcast knowledge updates ke mesh.

## Output
- Wiki status: {pages, pending_reviews, last_ingest, graph_nodes}
- RBAC audit: {role_changes, permission_checks, violations}
- Mesh broadcast: msg_type=KNOWLEDGE_UPDATED

## Exit Codes
- SKILL_OK: Knowledge hub synced
- SKILL_WARN: Pending reviews need attention
- SKILL_FAIL: Arkon API unreachable
