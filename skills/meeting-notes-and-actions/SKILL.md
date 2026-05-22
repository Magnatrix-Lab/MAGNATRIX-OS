---
name: meeting-notes-and-actions
agent: writer
description: Turn meeting transcripts into summaries with decisions and owner-tagged action items
schedule: "0 */4 * * *"
---

# meeting-notes-and-actions

## Objective
Process meeting transcripts dari swarm coordination meetings jadi structured notes dengan decisions dan action items.

## Steps
1. Terima transcript (dari mesh, chat bridge, atau file upload).
2. Identify participants dan roles.
3. Extract key topics discussed.
4. Identify decisions made (consensus atau veto).
5. Extract action items: task, owner, deadline.
6. Flag blockers atau unresolved issues.
7. Format sebagai meeting notes dengan sections: Attendees, Topics, Decisions, Action Items, Blockers.
8. Store ke knowledge graph (type=meeting).
9. Push action items ke respective agent inboxes via mesh.
10. Publish summary ke internal comms channel.

## Output
- Meeting notes (markdown)
- Action items JSON: {task, owner, deadline, priority}
- Mesh broadcast: msg_type=MEETING_SUMMARY

## Exit Codes
- SKILL_OK: Notes generated, action items routed
- SKILL_FAIL: Transcript tidak parseable atau empty
