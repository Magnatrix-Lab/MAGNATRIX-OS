---
name: mcp-builder
agent: architect
description: Build dan evaluate MCP servers dengan best practices dan evaluation harness
schedule: "0 0 * * 0"
---

# mcp-builder

## Objective
Design dan prototype MCP (Model Context Protocol) servers untuk extend MAGNATRIX capabilities. MCP adalah standard protocol untuk expose tools ke AI agents.

## Steps
1. Identifikasi capability gaps yang bisa di-fill via MCP server.
2. Design MCP server spec: tools, resources, prompts, schemas.
3. Implement server menggunakan Python SDK atau TypeScript SDK.
4. Write test harness untuk validate: tool invocation, error handling, schema compliance.
5. Evaluate: latency, reliability, security (input validation, rate limiting).
6. Jika pass evaluation, integrate ke MAGNATRIX skill registry.
7. Generate documentation dan usage examples.
8. Publish ke internal package registry atau GitHub.
9. Broadcast ke mesh untuk agent adoption.

## Output
- MCP server package
- Test report: {tools_count, test_coverage, avg_latency, security_score}
- Documentation
- Mesh broadcast: msg_type=MCP_SERVER_READY

## Exit Codes
- SKILL_OK: MCP server built, tested, documented
- SKILL_PARTIAL: Server built, needs security hardening
- SKILL_FAIL: Design flaw atau test failure
