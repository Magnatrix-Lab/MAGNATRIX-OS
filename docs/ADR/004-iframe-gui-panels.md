# ADR-004: iframe-Based Standalone GUI Panels

## Status
Accepted

## Context
Dashboard HTML grew to 3,700+ lines — a monolith that's hard to maintain, review, and debug. Adding a new panel required editing the same file, increasing merge conflicts.

## Decision
Convert every panel to a standalone HTML file. Dashboard becomes a thin shell that embeds panels via `<iframe>`. 20 panels = 20 independent files.

## Architecture
```
dashboard.html (shell, ~1,200 lines)
├── iframe → panels/panel_chat.html (standalone)
├── iframe → panels/panel_kanban.html (standalone)
├── iframe → panels/panel_trading.html (standalone)
└── ... 17 more panels
```

## Consequences

**Positive:**
- Each panel is independently maintainable (300-800 lines vs 3,700).
- Panels can be opened standalone (useful for multi-monitor setups).
- No CSS/JS conflicts between panels (iframe isolation).
- Easier to test individual panels in browser.
- New panel = new file, no touch to dashboard.

**Negative:**
- iframe cross-communication requires `postMessage` (not implemented yet — panels are read-only for now).
- Each panel repeats some CSS boilerplate.
- Slightly higher memory usage per iframe.

## Mitigations
- CSS uses CSS variables (`:root`) — consistent theming across all panels.
- Common patterns (cards, tables, topbars) are copy-paste templates.
- Future: extract shared CSS to `panels/common.css`.
