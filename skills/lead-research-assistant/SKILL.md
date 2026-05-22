---
name: lead-research-assistant
agent: researcher
description: Research leads dan enrich records dengan firmographic data
schedule: "0 */12 * * *"
---

# lead-research-assistant

## Objective
Research potential collaborators, investors, atau users untuk MAGNATRIX. Enrich lead records dengan firmographic dan technographic data.

## Steps
1. Terima lead list dari scout atau external source.
2. Untuk setiap lead, research: company size, funding stage, tech stack, open source activity, key people.
3. Cek apakah lead punya problem yang MAGNATRIX solve: AI infrastructure needs, multi-agent coordination, security audit requirements.
4. Score fit: 0-100 berdasarkan problem-solution alignment, budget signal, decision-maker accessibility.
5. Prioritize leads dengan fit > 70.
6. Generate personalized outreach brief untuk setiap high-fit lead.
7. Store enriched records ke knowledge graph (type=lead).
8. Broadcast high-priority leads ke mesh.

## Output
- Lead enrichment report: {leads_processed, high_fit_count, avg_fit_score, outreach_briefs}
- Mesh broadcast: msg_type=LEADS_READY

## Exit Codes
- SKILL_OK: Leads enriched, briefs generated
- SKILL_PARTIAL: Some leads tidak ditemukan info
- SKILL_FAIL: Research API error atau no leads
