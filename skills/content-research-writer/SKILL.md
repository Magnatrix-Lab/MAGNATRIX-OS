---
name: content-research-writer
agent: writer
description: Research topics dan draft content dengan sourced citations
schedule: "0 */6 * * *"
---

# content-research-writer

## Objective
Research topik AI/tech dan draft content untuk MAGNATRIX blog, newsletter, atau social. Auto-cite sources.

## Steps
1. Terima topic dari mesh atau dari trend analysis (scout/analyst).
2. Search web untuk authoritative sources: arxiv, papers, GitHub repos, official docs.
3. Extract key findings, statistics, quotes.
4. Cek source credibility: domain authority, recency, citation count.
5. Draft content dalam format yang diminta: blog post, thread, newsletter, atau video script.
6. Include inline citations dengan links.
7. Generate social media snippets untuk cross-promotion.
8. Publish ke designated channel atau queue untuk editorial review.
9. Log ke knowledge graph.

## Output
- Draft content (markdown)
- Source bibliography
- Social snippets
- Mesh broadcast: msg_type=CONTENT_DRAFT_READY

## Exit Codes
- SKILL_OK: Draft complete, sources verified
- SKILL_PARTIAL: Draft complete dengan low-confidence sources flagged
- SKILL_FAIL: Research failed atau sources tidak credible
