---
name: competitive-ads-extractor
agent: analyst
description: Analyze competitor ads dan extract structured insights untuk strategy
schedule: "0 2 * * *"
---

# competitive-ads-extractor

## Objective
Monitor competitor AI/agent projects dari GitHub, Product Hunt, Twitter. Extract positioning, features, pricing, dan gaps.

## Steps
1. Define competitor list dari knowledge graph (type=competitor).
2. Scrape latest updates: GitHub releases, Product Hunt launches, blog posts.
3. Extract structured data: {name, feature_highlight, pricing_change, launch_date, sentiment}.
4. Compare dengan MAGNATRIX capabilities — identify gaps dan differentiators.
5. Score threat level: high (direct competitor + recent funding), medium (similar space), low (indirect).
6. Generate competitive intelligence report.
7. Route ke analyst untuk strategy implications.
8. Broadcast ke mesh untuk swarm awareness.

## Output
- Competitor report: {competitors_tracked, updates_found, threat_assessment, recommended_actions}
- Mesh broadcast: msg_type=COMPETITIVE_INTEL

## Exit Codes
- SKILL_OK: Intel gathered, report generated
- SKILL_WARN: Partial data, some competitors tidak accessible
- SKILL_FAIL: Error scraping atau no competitor data
