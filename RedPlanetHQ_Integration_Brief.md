# RedPlanetHQ/core Integration — Task Brief

## Context
MAGNATRIX-OS is a private, uncensored, open-source AI operating system (296 modules, pure Python stdlib). We are integrating features from RedPlanetHQ/core (a Personal AI OS with 1.7k stars, webapp + Tauri desktop + CLI + 50+ integrations).

## Core Directive
AMATI-PELAJARI-TIRU (Observe-Learn-Imitate). All modules must be pure Python standard library only.

## Module Requirements (Every Module)
- Pure Python stdlib (no pip install dependencies)
- Dataclass-based models
- JSON persistence via pathlib
- `to_dict()` method for dashboard integration
- `get_stats()` method for telemetry
- `__all__` export list
- Self-contained with proper error handling

## Module Groups

### Group A: Mission Control & Dashboard (5 modules)
1. `mission_control_native.py` — Central command dashboard. Aggregates system status, active tasks, alerts, and provides unified control surface. Methods: `get_overview()`, `alert()`, `dispatch_command()`.
2. `scratchpad_engine_native.py` — Daily scratchpad surface where tasks/ideas start. Natural-language task parsing, checkboxes, priority auto-detection. Methods: `parse_entry()`, `promote_to_task()`, `get_daily_board()`.
3. `notification_hub_native.py` — Central notification dispatcher. Routes notifications to appropriate channels (dashboard, TUI, webhook). Methods: `notify()`, `subscribe()`, `dismiss()`, `get_unread()`.
4. `status_board_native.py` — Real-time status board showing all subsystem health. Methods: `register_source()`, `update_status()`, `get_health_map()`.
5. `context_aggregator_native.py` — Aggregates context from all sources (memory, connectors, tasks, chat) into unified context window. Methods: `gather()`, `summarize()`, `inject()`.

### Group B: Voice, Messaging, Personality, Autonomy (5 modules)
6. `voice_interface_native.py` — Voice command interface. Speech-to-text simulation, command parsing, wake word detection. Methods: `listen()`, `parse_command()`, `execute_voice_command()`.
7. `messaging_bridge_native.py` — Bridge for WhatsApp, Slack, Telegram messaging. Message formatting, routing, reply handling. Methods: `send_message()`, `receive_message()`, `format_for_channel()`.
8. `personality_engine_native.py` — Personality engine with 5 built-in personas (TARS=dry efficiency, Alfred=loyal formality, Hudson=warm practicality, JARVIS=analytical precision, Friday=proactive assistant). Methods: `set_persona()`, `speak()`, `get_tone()`.
9. `autonomy_governor_native.py` — Human-in-the-loop autonomy control. Configurable autonomy levels per task/app/action: full_auto, suggest_approve, manual_only. Methods: `request_approval()`, `set_level()`, `check_permission()`.
10. `action_dispatcher_native.py` — Dispatches actions to appropriate handlers. Queuing, retry, confirmation routing. Methods: `dispatch()`, `queue()`, `cancel()`, `get_queue()`.

### Group C: Gateway, Agents, Skills, Connectors (5 modules)
11. `gateway_executor_native.py` — Gateway for executing external agents (Claude Code, Codex, terminal). Session management, output capture. Methods: `spawn_session()`, `capture_output()`, `terminate_session()`.
12. `browser_agent_native.py` — Browser automation agent. Simulated navigation, form filling, screenshot planning, DOM parsing. Methods: `navigate()`, `fill_form()`, `extract_data()`, `click()`.
13. `terminal_agent_native.py` — Terminal command agent. Safe command execution, sandboxing, output parsing. Methods: `execute()`, `validate_command()`, `stream_output()`, `get_history()`.
14. `skills_library_native.py` — Extensive skills library (100+ skill patterns). Auto-triggered skills based on context. Methods: `match_skill()`, `execute_skill()`, `add_skill()`, `list_skills()`.
15. `connector_registry_native.py` — Registry for 50+ app connectors (GitHub, Linear, Slack, Gmail, Notion, etc.). Connection management, API abstraction. Methods: `register()`, `connect()`, `disconnect()`, `get_connector()`.

### Group D: UI/TUI, Infrastructure, Hooks (5 modules)
16. `dashboard_widget_native.py` — Dashboard widget system. Widget creation, layout, data binding. Methods: `create_widget()`, `update_widget()`, `render_layout()`, `get_widgets()`.
17. `tui_renderer_native.py` — TUI rendering engine. Box drawing, color support, layout engine, keybinding. Methods: `render()`, `handle_input()`, `add_component()`, `refresh()`.
18. `email_client_native.py` — Email client. IMAP/SMTP simulation, inbox management, filtering, auto-reply. Methods: `send_email()`, `fetch_inbox()`, `filter()`, `auto_reply()`.
19. `hook_system_native.py` — Event hook system. Pre/post action hooks, chainable middleware, event bus. Methods: `register_hook()`, `trigger()`, `remove_hook()`, `list_hooks()`.
20. `webhook_trigger_native.py` — Webhook trigger system for proactive automation. Ingestion, signature verification, routing. Methods: `ingest()`, `verify_signature()`, `route()`, `register_endpoint()`.

## Deliverable
For each module: write the complete `.py` file to `/mnt/agents/MAGNATRIX-OS/core/` with `class *Native` naming convention (matching previous modules). Then confirm completion with file list and sizes.

## Important
- Search for best-fit skills in your environment first
- Use keywords: system programming, module design, stdlib architecture, Python module patterns
- All code must be pure stdlib
- File names must follow existing convention: `feature_name_native.py`
- Save directly to disk, don't wait for review
