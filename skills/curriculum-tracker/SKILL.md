---
name: curriculum-tracker
agent: researcher
description: Track AI Engineering course progress dan auto-update skill activation
schedule: "0 0 * * *"
---

# curriculum-tracker

## Objective
Monitor progress belajar dari course "AI Engineering From Scratch" dan auto-unlock MAGNATRIX skills berdasarkan completed lessons. Broadcast ke mesh jika milestone reached.

## Steps
1. Load curriculum_progress.json dari disk.
2. Untuk setiap phase, cek apakah ada lesson completion baru.
3. Hitung skill unlock threshold: skills di-unlock ketika lesson progress ≥ 50%.
4. Bandingkan dengan skill registry — identify skills yang belum active.
5. Auto-activate skills yang baru di-unlock ke agent yang sesuai.
6. Cek milestone: phase complete (100%), layer complete (all phases in layer ≥ 80%).
7. Jika milestone reached, broadcast ACHIEVEMENT ke mesh.
8. Generate weekly learning digest untuk operator.
9. Suggest next lesson/phase berdasarkan role priority.
10. Save updated progress.

## Output
- Progress report: {phases_completed, skills_unlocked, next_recommendation, milestones}
- Mesh broadcast: msg_type=CURRICULUM_MILESTONE atau ACHIEVEMENT
- Skill activation: activated_skills list

## Exit Codes
- SKILL_OK: Progress synced, skills updated
- SKILL_NO_CHANGE: No new progress detected
- SKILL_FAIL: Error reading progress file
