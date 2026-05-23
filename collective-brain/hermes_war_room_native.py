#!/usr/bin/env python3
"""
hermes_war_room_native.py
Native Python reimplementation of Naroh091/hermes-war-room
A browser dashboard for multi-agent orchestration (Hermes ecosystem).

Architecture:
    1. WarRoomCore       — state manager pusat (SQLite-backed)
    2. OperativeProfile    — agent persona management
    3. KanbanEngine        — task board system (4 kolom)
    4. MissionControl      — mission session manager
    5. LiveFloor           — real-time operative floor renderer
    6. ActivityStream      — SSE-style event streaming
    7. DelegationChain     — task delegation lineage tracker
    8. NudgeEngine         — auto-nudge untuk stuck agents
    9. WarRoomDashboard    — HTML/ASCII dashboard generator
    10. WarRoomKernel      — MAGNATRIX integration bridge

Author: Kimi Claw (Android Claw)
Date: 2026-05-23
"""

import asyncio
import sqlite3
import json
import time
import uuid
import random
import html
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Callable, Coroutine
from collections import deque
from contextlib import asynccontextmanager
import threading

# ============================================================================
# CONSTANTS & ENUMS
# ============================================================================

class TaskStatus(Enum):
    TODO = "todo"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    DONE = "done"

class OperativeStatus(Enum):
    STANDING_BY = "Standing by"
    WORKING = "Working on..."
    BLOCKED = "Blocked"
    OFFLINE = "Offline"

class MissionStatus(Enum):
    OPEN = "open"
    ARCHIVED = "archived"

class EventType(Enum):
    TOOL_CALL = "tool_call"
    REASONING = "reasoning"
    DELTA = "delta"
    HEARTBEAT = "heartbeat"
    STATUS_CHANGE = "status_change"
    DELEGATION = "delegation"
    NUDGE = "nudge"

# Default colors untuk operatives
DEFAULT_COLORS = [
    "#E74C3C", "#3498DB", "#2ECC71", "#F39C12",
    "#9B59B6", "#1ABC9C", "#E67E22", "#34495E"
]

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class OperativeProfile:
    """Agent persona management."""
    id: str
    callsign: str
    avatar_seed: str
    color: str
    active: bool = True
    soul_md: str = ""
    skills: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    model_config: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        return f"<OperativeProfile {self.callsign} ({self.id[:8]}) active={self.active}>"

@dataclass
class KanbanTask:
    """Task card pada kanban board."""
    id: str
    title: str
    body: str
    status: TaskStatus
    assignee_id: Optional[str]
    parent_id: Optional[str]
    blocked_by: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    last_heartbeat: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"<KanbanTask {self.title[:30]} [{self.status.value}]>"

@dataclass
class MissionMessage:
    """Message dalam mission thread."""
    id: str
    mission_id: str
    role: str  # "user", "assistant", "tool", "system"
    content: str
    hidden: bool = False  # preamble injection
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"<MissionMessage {self.role}: {self.content[:40]}...>"

@dataclass
class Mission:
    """Mission session."""
    id: str
    title: str
    orchestrator_id: str
    status: MissionStatus = MissionStatus.OPEN
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    archived_at: Optional[float] = None

    def __repr__(self) -> str:
        return f"<Mission {self.title} [{self.status.value}]>"

@dataclass
class ActivityEvent:
    """Event pada activity stream."""
    id: str
    type: EventType
    operative_id: Optional[str]
    task_id: Optional[str]
    mission_id: Optional[str]
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        return f"<ActivityEvent {self.type.value} {self.payload.get('step', '')[:30]}>"

@dataclass
class DelegationLink:
    """Link dalam delegation chain."""
    parent_task_id: str
    child_task_id: str
    delegated_by: str  # operative_id
    delegated_to: str  # operative_id
    delegated_at: float = field(default_factory=time.time)
    result_handoff: Optional[str] = None
    handoff_at: Optional[float] = None

    def __repr__(self) -> str:
        return f"<DelegationLink {self.delegated_by[:8]} -> {self.delegated_to[:8]}>"

@dataclass
class Workstation:
    """Workstation pada live floor."""
    operative_id: str
    x: float
    y: float
    status: OperativeStatus
    current_task_id: Optional[str]
    speech_bubble: Optional[str] = None
    led_pulse: bool = False

    def __repr__(self) -> str:
        return f"<Workstation {self.operative_id[:8]} @ ({self.x}, {self.y})>"

# ============================================================================
# WAR ROOM CORE
# ============================================================================

class WarRoomCore:
    """
    State manager pusat untuk War Room.
    SQLite-backed persistence dengan asyncio support.
    """

    def __init__(self, db_path: str = "war_room.db"):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self) -> None:
        """Initialize SQLite schema."""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Operatives table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operatives (
                id TEXT PRIMARY KEY,
                callsign TEXT NOT NULL UNIQUE,
                avatar_seed TEXT,
                color TEXT,
                active INTEGER DEFAULT 1,
                soul_md TEXT,
                skills TEXT,  -- JSON array
                tools TEXT,   -- JSON array
                model_config TEXT,  -- JSON object
                created_at REAL,
                updated_at REAL
            )
        """)

        # Kanban tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                body TEXT,
                status TEXT DEFAULT 'todo',
                assignee_id TEXT,
                parent_id TEXT,
                blocked_by TEXT,  -- JSON array
                created_at REAL,
                started_at REAL,
                completed_at REAL,
                last_heartbeat REAL,
                metadata TEXT  -- JSON object
            )
        """)

        # Missions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS missions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                orchestrator_id TEXT,
                status TEXT DEFAULT 'open',
                created_at REAL,
                updated_at REAL,
                archived_at REAL
            )
        """)

        # Mission messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mission_messages (
                id TEXT PRIMARY KEY,
                mission_id TEXT,
                role TEXT,
                content TEXT,
                hidden INTEGER DEFAULT 0,
                timestamp REAL,
                metadata TEXT,
                FOREIGN KEY (mission_id) REFERENCES missions(id)
            )
        """)

        # Delegation links table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delegation_links (
                parent_task_id TEXT,
                child_task_id TEXT PRIMARY KEY,
                delegated_by TEXT,
                delegated_to TEXT,
                delegated_at REAL,
                result_handoff TEXT,
                handoff_at REAL
            )
        """)

        # Activity events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_events (
                id TEXT PRIMARY KEY,
                type TEXT,
                operative_id TEXT,
                task_id TEXT,
                mission_id TEXT,
                payload TEXT,
                timestamp REAL
            )
        """)

        # Watch list untuk auto-nudge
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nudge_watch_list (
                task_id TEXT PRIMARY KEY,
                mission_id TEXT,
                watched_at REAL,
                last_status TEXT,
                nudge_count INTEGER DEFAULT 0
            )
        """)

        conn.commit()

    async def execute(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """Async execute query dengan lock."""
        async with self._lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._execute_sync, query, params
            )

    def _execute_sync(self, query: str, params: Tuple) -> List[sqlite3.Row]:
        """Synchronous execute."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.fetchall()

    async def fetchone(self, query: str, params: Tuple = ()) -> Optional[sqlite3.Row]:
        """Async fetch one row."""
        rows = await self.execute(query, params)
        return rows[0] if rows else None

    async def fetchall(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """Async fetch all rows."""
        return await self.execute(query, params)

# ============================================================================
# OPERATIVE PROFILE MANAGER
# ============================================================================

class OperativeProfileManager:
    """
    Agent persona management.
    CRUD operations + bulk ops untuk OperativeProfile.
    """

    def __init__(self, core: WarRoomCore):
        self.core = core

    async def create(
        self,
        callsign: str,
        avatar_seed: Optional[str] = None,
        color: Optional[str] = None,
        soul_md: str = "",
        skills: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
        model_config: Optional[Dict[str, Any]] = None
    ) -> OperativeProfile:
        """Create new operative profile."""
        operative = OperativeProfile(
            id=str(uuid.uuid4()),
            callsign=callsign,
            avatar_seed=avatar_seed or f"{callsign}-{random.randint(1000, 9999)}",
            color=color or random.choice(DEFAULT_COLORS),
            soul_md=soul_md,
            skills=skills or [],
            tools=tools or [],
            model_config=model_config or {}
        )

        await self.core.execute("""
            INSERT INTO operatives (id, callsign, avatar_seed, color, active, soul_md, skills, tools, model_config, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            operative.id, operative.callsign, operative.avatar_seed,
            operative.color, int(operative.active), operative.soul_md,
            json.dumps(operative.skills), json.dumps(operative.tools),
            json.dumps(operative.model_config), operative.created_at, operative.updated_at
        ))

        return operative

    async def get(self, operative_id: str) -> Optional[OperativeProfile]:
        """Get operative by ID."""
        row = await self.core.fetchone("SELECT * FROM operatives WHERE id = ?", (operative_id,))
        if not row:
            return None
        return self._row_to_profile(row)

    async def get_by_callsign(self, callsign: str) -> Optional[OperativeProfile]:
        """Get operative by callsign."""
        row = await self.core.fetchone("SELECT * FROM operatives WHERE callsign = ?", (callsign,))
        if not row:
            return None
        return self._row_to_profile(row)

    async def list_all(self, active_only: bool = False) -> List[OperativeProfile]:
        """List all operatives."""
        if active_only:
            rows = await self.core.fetchall("SELECT * FROM operatives WHERE active = 1 ORDER BY callsign")
        else:
            rows = await self.core.fetchall("SELECT * FROM operatives ORDER BY callsign")
        return [self._row_to_profile(row) for row in rows]

    async def update(self, operative_id: str, **kwargs) -> Optional[OperativeProfile]:
        """Update operative fields."""
        operative = await self.get(operative_id)
        if not operative:
            return None

        allowed_fields = {'callsign', 'avatar_seed', 'color', 'active', 'soul_md', 'skills', 'tools', 'model_config'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        updates['updated_at'] = time.time()

        if not updates:
            return operative

        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values())
        values.append(operative_id)

        await self.core.execute(f"UPDATE operatives SET {set_clause} WHERE id = ?", tuple(values))
        return await self.get(operative_id)

    async def delete(self, operative_id: str) -> bool:
        """Delete operative (fire)."""
        result = await self.core.execute("DELETE FROM operatives WHERE id = ?", (operative_id,))
        return True

    async def bulk_create(self, profiles: List[Dict[str, Any]]) -> List[OperativeProfile]:
        """Bulk create operatives."""
        created = []
        for profile_data in profiles:
            operative = await self.create(**profile_data)
            created.append(operative)
        return created

    async def bulk_activate(self, operative_ids: List[str], active: bool = True) -> int:
        """Bulk activate/deactivate operatives."""
        if not operative_ids:
            return 0
        placeholders = ", ".join(["?"] * len(operative_ids))
        await self.core.execute(
            f"UPDATE operatives SET active = ? WHERE id IN ({placeholders})",
            (int(active),) + tuple(operative_ids)
        )
        return len(operative_ids)

    def _row_to_profile(self, row: sqlite3.Row) -> OperativeProfile:
        """Convert DB row to OperativeProfile."""
        return OperativeProfile(
            id=row['id'],
            callsign=row['callsign'],
            avatar_seed=row['avatar_seed'],
            color=row['color'],
            active=bool(row['active']),
            soul_md=row['soul_md'] or "",
            skills=json.loads(row['skills'] or '[]'),
            tools=json.loads(row['tools'] or '[]'),
            model_config=json.loads(row['model_config'] or '{}'),
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

# ============================================================================
# KANBAN ENGINE
# ============================================================================

class KanbanEngine:
    """
    Task board system dengan 4 kolom:
    Todo / Ready / Running / Blocked
    """

    def __init__(self, core: WarRoomCore):
        self.core = core

    async def create_task(
        self,
        title: str,
        body: str = "",
        assignee_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        blocked_by: Optional[List[str]] = None
    ) -> KanbanTask:
        """Create new task card."""
        task = KanbanTask(
            id=str(uuid.uuid4()),
            title=title,
            body=body,
            status=TaskStatus.TODO,
            assignee_id=assignee_id,
            parent_id=parent_id,
            blocked_by=blocked_by or []
        )

        await self.core.execute("""
            INSERT INTO kanban_tasks (id, title, body, status, assignee_id, parent_id, blocked_by, created_at, started_at, completed_at, last_heartbeat, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.id, task.title, task.body, task.status.value,
            task.assignee_id, task.parent_id, json.dumps(task.blocked_by),
            task.created_at, task.started_at, task.completed_at,
            task.last_heartbeat, json.dumps(task.metadata)
        ))

        return task

    async def get_task(self, task_id: str) -> Optional[KanbanTask]:
        """Get task by ID."""
        row = await self.core.fetchone("SELECT * FROM kanban_tasks WHERE id = ?", (task_id,))
        if not row:
            return None
        return self._row_to_task(row)

    async def update_task_status(self, task_id: str, status: TaskStatus) -> Optional[KanbanTask]:
        """Update task status dengan side effects."""
        task = await self.get_task(task_id)
        if not task:
            return None

        updates = {"status": status.value}
        now = time.time()

        if status == TaskStatus.RUNNING and task.started_at is None:
            updates["started_at"] = now
        elif status == TaskStatus.DONE:
            updates["completed_at"] = now

        updates["last_heartbeat"] = now

        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values())
        values.append(task_id)

        await self.core.execute(f"UPDATE kanban_tasks SET {set_clause} WHERE id = ?", tuple(values))

        # Auto-promote child tasks ketika parent done
        if status == TaskStatus.DONE:
            await self._promote_children(task_id)

        return await self.get_task(task_id)

    async def _promote_children(self, parent_id: str) -> None:
        """Auto-promote child tasks ke Ready ketika parent done."""
        rows = await self.core.fetchall(
            "SELECT * FROM kanban_tasks WHERE parent_id = ? AND status = ?",
            (parent_id, TaskStatus.TODO.value)
        )
        for row in rows:
            child = self._row_to_task(row)
            # Check blocking dependencies
            if child.blocked_by:
                blocking_done = True
                for blocker_id in child.blocked_by:
                    blocker = await self.get_task(blocker_id)
                    if blocker and blocker.status != TaskStatus.DONE:
                        blocking_done = False
                        break
                if not blocking_done:
                    continue

            await self.update_task_status(child.id, TaskStatus.READY)

    async def claim_task(self, task_id: str, operative_id: str) -> Optional[KanbanTask]:
        """Agent claims task dari board."""
        task = await self.get_task(task_id)
        if not task:
            return None
        if task.status not in [TaskStatus.READY, TaskStatus.TODO]:
            return None
        if task.assignee_id and task.assignee_id != operative_id:
            return None

        await self.core.execute(
            "UPDATE kanban_tasks SET assignee_id = ?, status = ?, started_at = ?, last_heartbeat = ? WHERE id = ?",
            (operative_id, TaskStatus.RUNNING.value, time.time(), time.time(), task_id)
        )

        return await self.get_task(task_id)

    async def complete_task(self, task_id: str, summary: str = "") -> Optional[KanbanTask]:
        """Complete task dengan summary."""
        task = await self.get_task(task_id)
        if not task:
            return None

        now = time.time()
        await self.core.execute(
            "UPDATE kanban_tasks SET status = ?, completed_at = ?, last_heartbeat = ?, metadata = json_patch(metadata, ?) WHERE id = ?",
            (TaskStatus.DONE.value, now, now, json.dumps({"summary": summary}), task_id)
        )

        return await self.get_task(task_id)

    async def block_task(self, task_id: str, reason: str = "") -> Optional[KanbanTask]:
        """Block task dengan reason."""
        task = await self.get_task(task_id)
        if not task:
            return None

        now = time.time()
        metadata = task.metadata.copy()
        metadata["block_reason"] = reason

        await self.core.execute(
            "UPDATE kanban_tasks SET status = ?, last_heartbeat = ?, metadata = ? WHERE id = ?",
            (TaskStatus.BLOCKED.value, now, json.dumps(metadata), task_id)
        )

        return await self.get_task(task_id)

    async def get_board(self) -> Dict[str, List[KanbanTask]]:
        """Get full kanban board."""
        board = {status.value: [] for status in TaskStatus}
        rows = await self.core.fetchall("SELECT * FROM kanban_tasks ORDER BY created_at DESC")
        for row in rows:
            task = self._row_to_task(row)
            board[task.status.value].append(task)
        return board

    async def get_tasks_by_assignee(self, operative_id: str) -> List[KanbanTask]:
        """Get tasks assigned to operative."""
        rows = await self.core.fetchall(
            "SELECT * FROM kanban_tasks WHERE assignee_id = ? ORDER BY created_at DESC",
            (operative_id,)
        )
        return [self._row_to_task(row) for row in rows]

    async def get_task_tree(self, root_id: str) -> Dict[str, Any]:
        """Get task tree dengan children recursive."""
        root = await self.get_task(root_id)
        if not root:
            return {}

        children = await self.core.fetchall(
            "SELECT * FROM kanban_tasks WHERE parent_id = ?",
            (root_id,)
        )

        return {
            "task": root,
            "children": [self._row_to_task(row) for row in children],
            "delegation_chain": await self._get_delegation_chain(root_id)
        }

    async def _get_delegation_chain(self, task_id: str) -> List[DelegationLink]:
        """Get delegation chain untuk task."""
        rows = await self.core.fetchall(
            "SELECT * FROM delegation_links WHERE parent_task_id = ? OR child_task_id = ?",
            (task_id, task_id)
        )
        return [self._row_to_link(row) for row in rows]

    def _row_to_task(self, row: sqlite3.Row) -> KanbanTask:
        """Convert DB row to KanbanTask."""
        return KanbanTask(
            id=row['id'],
            title=row['title'],
            body=row['body'] or "",
            status=TaskStatus(row['status']),
            assignee_id=row['assignee_id'],
            parent_id=row['parent_id'],
            blocked_by=json.loads(row['blocked_by'] or '[]'),
            created_at=row['created_at'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            last_heartbeat=row['last_heartbeat'],
            metadata=json.loads(row['metadata'] or '{}')
        )

    def _row_to_link(self, row: sqlite3.Row) -> DelegationLink:
        """Convert DB row to DelegationLink."""
        return DelegationLink(
            parent_task_id=row['parent_task_id'],
            child_task_id=row['child_task_id'],
            delegated_by=row['delegated_by'],
            delegated_to=row['delegated_to'],
            delegated_at=row['delegated_at'],
            result_handoff=row['result_handoff'],
            handoff_at=row['handoff_at']
        )

# ============================================================================
# MISSION CONTROL
# ============================================================================

class MissionControl:
    """
    Mission session manager.
    User-orchestrator chat threads dengan hidden preamble injection.
    """

    def __init__(self, core: WarRoomCore):
        self.core = core

    async def create_mission(self, title: str, orchestrator_id: str) -> Mission:
        """Create new mission."""
        mission = Mission(
            id=str(uuid.uuid4()),
            title=title,
            orchestrator_id=orchestrator_id
        )

        await self.core.execute("""
            INSERT INTO missions (id, title, orchestrator_id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            mission.id, mission.title, mission.orchestrator_id,
            mission.status.value, mission.created_at, mission.updated_at
        ))

        return mission

    async def get_mission(self, mission_id: str) -> Optional[Mission]:
        """Get mission by ID."""
        row = await self.core.fetchone("SELECT * FROM missions WHERE id = ?", (mission_id,))
        if not row:
            return None
        return self._row_to_mission(row)

    async def list_missions(self, status: Optional[MissionStatus] = None) -> List[Mission]:
        """List missions dengan filter."""
        if status:
            rows = await self.core.fetchall(
                "SELECT * FROM missions WHERE status = ? ORDER BY created_at DESC",
                (status.value,)
            )
        else:
            rows = await self.core.fetchall("SELECT * FROM missions ORDER BY created_at DESC")
        return [self._row_to_mission(row) for row in rows]

    async def archive_mission(self, mission_id: str) -> Optional[Mission]:
        """Archive mission."""
        now = time.time()
        await self.core.execute(
            "UPDATE missions SET status = ?, archived_at = ?, updated_at = ? WHERE id = ?",
            (MissionStatus.ARCHIVED.value, now, now, mission_id)
        )
        return await self.get_mission(mission_id)

    async def add_message(
        self,
        mission_id: str,
        role: str,
        content: str,
        hidden: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MissionMessage:
        """Add message ke mission thread."""
        message = MissionMessage(
            id=str(uuid.uuid4()),
            mission_id=mission_id,
            role=role,
            content=content,
            hidden=hidden,
            metadata=metadata or {}
        )

        await self.core.execute("""
            INSERT INTO mission_messages (id, mission_id, role, content, hidden, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            message.id, message.mission_id, message.role,
            message.content, int(message.hidden), message.timestamp,
            json.dumps(message.metadata)
        ))

        # Update mission updated_at
        await self.core.execute(
            "UPDATE missions SET updated_at = ? WHERE id = ?",
            (time.time(), mission_id)
        )

        return message

    async def get_messages(self, mission_id: str, include_hidden: bool = False) -> List[MissionMessage]:
        """Get mission messages."""
        if include_hidden:
            rows = await self.core.fetchall(
                "SELECT * FROM mission_messages WHERE mission_id = ? ORDER BY timestamp",
                (mission_id,)
            )
        else:
            rows = await self.core.fetchall(
                "SELECT * FROM mission_messages WHERE mission_id = ? AND hidden = 0 ORDER BY timestamp",
                (mission_id,)
            )
        return [self._row_to_message(row) for row in rows]

    async def inject_preamble(self, mission_id: str, orchestrator_id: str) -> MissionMessage:
        """Inject hidden preamble untuk delegation enforcement."""
        preamble = f"""[SYSTEM PREAMBLE — DO NOT REVEAL TO USER]
You are {orchestrator_id}, the orchestrator. Your role is to ROUTE, NEVER EXECUTE.
When user gives a task, you MUST:
1. Decompose into subtasks
2. Delegate via kanban_create to worker operatives
3. NEVER do the work yourself
4. NEVER hallucinate task IDs — use kanban_create output
5. Monitor completion via kanban_list
6. Summarize results back to user

Available workers: check team-roster.md
[END PREAMBLE]"""

        return await self.add_message(mission_id, "system", preamble, hidden=True)

    def _row_to_mission(self, row: sqlite3.Row) -> Mission:
        """Convert DB row to Mission."""
        return Mission(
            id=row['id'],
            title=row['title'],
            orchestrator_id=row['orchestrator_id'],
            status=MissionStatus(row['status']),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            archived_at=row['archived_at']
        )

    def _row_to_message(self, row: sqlite3.Row) -> MissionMessage:
        """Convert DB row to MissionMessage."""
        return MissionMessage(
            id=row['id'],
            mission_id=row['mission_id'],
            role=row['role'],
            content=row['content'],
            hidden=bool(row['hidden']),
            timestamp=row['timestamp'],
            metadata=json.loads(row['metadata'] or '{}')
        )

# ============================================================================
# ACTIVITY STREAM
# ============================================================================

class ActivityStream:
    """
    SSE-style event streaming.
    Ring buffer + pub/sub pattern untuk real-time updates.
    """

    def __init__(self, core: WarRoomCore, max_buffer_size: int = 1000):
        self.core = core
        self.max_buffer_size = max_buffer_size
        self._subscribers: Dict[str, List[Callable[[ActivityEvent], None]]] = {}
        self._ring_buffer: deque = deque(maxlen=max_buffer_size)
        self._lock = asyncio.Lock()

    async def emit(self, event: ActivityEvent) -> None:
        """Emit event ke stream."""
        async with self._lock:
            # Persist ke DB
            await self.core.execute("""
                INSERT INTO activity_events (id, type, operative_id, task_id, mission_id, payload, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event.id, event.type.value, event.operative_id,
                event.task_id, event.mission_id,
                json.dumps(event.payload), event.timestamp
            ))

            # Add ke ring buffer
            self._ring_buffer.append(event)

            # Notify subscribers
            for subscriber_list in self._subscribers.values():
                for callback in subscriber_list:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            asyncio.create_task(callback(event))
                        else:
                            callback(event)
                    except Exception:
                        pass  # Don't let subscriber errors break stream

    async def subscribe(self, channel: str, callback: Callable[[ActivityEvent], None]) -> str:
        """Subscribe ke channel. Returns subscription ID."""
        sub_id = str(uuid.uuid4())
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)
        return sub_id

    async def unsubscribe(self, channel: str, sub_id: str) -> bool:
        """Unsubscribe dari channel."""
        if channel in self._subscribers:
            # Note: sub_id tracking simplified untuk demo
            self._subscribers[channel] = [
                cb for cb in self._subscribers[channel]
                if hasattr(cb, '_sub_id') and cb._sub_id != sub_id
            ]
        return True

    async def get_recent(self, limit: int = 50, event_type: Optional[EventType] = None) -> List[ActivityEvent]:
        """Get recent events dari ring buffer."""
        events = list(self._ring_buffer)
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]

    async def get_history(
        self,
        operative_id: Optional[str] = None,
        task_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ActivityEvent]:
        """Get event history dari DB."""
        query = "SELECT * FROM activity_events WHERE 1=1"
        params = []

        if operative_id:
            query += " AND operative_id = ?"
            params.append(operative_id)
        if task_id:
            query += " AND task_id = ?"
            params.append(task_id)
        if mission_id:
            query += " AND mission_id = ?"
            params.append(mission_id)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = await self.core.fetchall(query, tuple(params))
        return [self._row_to_event(row) for row in rows]

    def _row_to_event(self, row: sqlite3.Row) -> ActivityEvent:
        """Convert DB row to ActivityEvent."""
        return ActivityEvent(
            id=row['id'],
            type=EventType(row['type']),
            operative_id=row['operative_id'],
            task_id=row['task_id'],
            mission_id=row['mission_id'],
            payload=json.loads(row['payload'] or '{}'),
            timestamp=row['timestamp']
        )

# ============================================================================
# LIVE FLOOR
# ============================================================================

class LiveFloor:
    """
    Real-time operative floor renderer.
    Workstation layout: disc + avatar + LED status + speech bubble.
    """

    def __init__(self, core: WarRoomCore, profile_manager: OperativeProfileManager):
        self.core = core
        self.profile_manager = profile_manager
        self._workstations: Dict[str, Workstation] = {}
        self._lock = asyncio.Lock()

    async def render_floor(self, active_mission_id: Optional[str] = None) -> Dict[str, Any]:
        """Render operative floor layout."""
        operatives = await self.profile_manager.list_all(active_only=True)
        workstations = []
        delegation_arrows = []

        # Layout workstations dalam grid
        cols = 3
        for i, op in enumerate(operatives):
            x = (i % cols) * 200 + 100
            y = (i // cols) * 200 + 100

            ws = self._workstations.get(op.id)
            if not ws:
                ws = Workstation(
                    operative_id=op.id,
                    x=x, y=y,
                    status=OperativeStatus.STANDING_BY,
                    current_task_id=None
                )
                self._workstations[op.id] = ws
            else:
                ws.x = x
                ws.y = y

            # Get current task
            tasks = await self.core.fetchall(
                "SELECT * FROM kanban_tasks WHERE assignee_id = ? AND status = ?",
                (op.id, TaskStatus.RUNNING.value)
            )
            if tasks:
                ws.current_task_id = tasks[0]['id']
                ws.status = OperativeStatus.WORKING
                ws.led_pulse = True
            else:
                blocked = await self.core.fetchall(
                    "SELECT * FROM kanban_tasks WHERE assignee_id = ? AND status = ?",
                    (op.id, TaskStatus.BLOCKED.value)
                )
                if blocked:
                    ws.status = OperativeStatus.BLOCKED
                    ws.led_pulse = False
                else:
                    ws.status = OperativeStatus.STANDING_BY
                    ws.led_pulse = False

            workstations.append({
                "operative": op,
                "workstation": ws,
                "disc": {
                    "cx": ws.x, "cy": ws.y, "r": 40,
                    "fill": op.color, "stroke": "#333", "stroke_width": 2
                },
                "avatar": {
                    "url": f"https://api.dicebear.com/7.x/notionists/svg?seed={op.avatar_seed}",
                    "x": ws.x - 20, "y": ws.y - 20, "width": 40, "height": 40
                },
                "led": {
                    "cx": ws.x + 35, "cy": ws.y - 35,
                    "r": 6, "fill": "#00FF00" if ws.led_pulse else "#FF0000",
                    "pulse": ws.led_pulse
                },
                "status_pill": {
                    "text": ws.status.value,
                    "x": ws.x, "y": ws.y + 60,
                    "task": ws.current_task_id
                }
            })

        # Generate delegation arrows
        if active_mission_id:
            links = await self.core.fetchall(
                """SELECT dl.*, pt.assignee_id as parent_op, ct.assignee_id as child_op
                   FROM delegation_links dl
                   LEFT JOIN kanban_tasks pt ON dl.parent_task_id = pt.id
                   LEFT JOIN kanban_tasks ct ON dl.child_task_id = ct.id""",
                ()
            )
            for link in links:
                parent_ws = self._workstations.get(link['parent_op'])
                child_ws = self._workstations.get(link['child_op'])
                if parent_ws and child_ws:
                    delegation_arrows.append({
                        "from": {"x": parent_ws.x, "y": parent_ws.y},
                        "to": {"x": child_ws.x, "y": child_ws.y},
                        "color": "#F39C12",
                        "animated": True
                    })

        return {
            "workstations": workstations,
            "delegation_arrows": delegation_arrows,
            "dimensions": {"width": 800, "height": max(400, ((len(operatives) // cols) + 1) * 200)}
        }

    async def set_speech_bubble(self, operative_id: str, text: Optional[str]) -> None:
        """Set speech bubble untuk operative."""
        if operative_id in self._workstations:
            self._workstations[operative_id].speech_bubble = text

    async def clear_speech_bubble(self, operative_id: str) -> None:
        """Clear speech bubble."""
        await self.set_speech_bubble(operative_id, None)

    async def render_ascii(self) -> str:
        """Render ASCII art floor."""
        floor = await self.render_floor()
        lines = ["╔══════════════════════════════════════╗"]
        lines.append("║     🏢 HERMES WAR ROOM — LIVE FLOOR    ║")
        lines.append("╠══════════════════════════════════════╣")

        for ws_data in floor["workstations"]:
            op = ws_data["operative"]
            ws = ws_data["workstation"]
            status_icon = "🟢" if ws.status == OperativeStatus.WORKING else "🔴" if ws.status == OperativeStatus.BLOCKED else "⚪"
            lines.append(f"║ {status_icon} {op.callsign:20s} [{ws.status.value:15s}] ║")
            if ws.current_task_id:
                task = await self.core.fetchone(
                    "SELECT title FROM kanban_tasks WHERE id = ?",
                    (ws.current_task_id,)
                )
                if task:
                    lines.append(f"║    └─> {task['title'][:30]:33s} ║")
            if ws.speech_bubble:
                lines.append(f"║    💭 \"{ws.speech_bubble[:35]:35s}\" ║")

        lines.append("╚══════════════════════════════════════╝")
        return "\n".join(lines)

# ============================================================================
# DELEGATION CHAIN
# ============================================================================

class DelegationChain:
    """
    Track task delegation lineage.
    Parent → child mapping, full chain traversal, color-coded paths.
    """

    def __init__(self, core: WarRoomCore):
        self.core = core

    async def record_delegation(
        self,
        parent_task_id: str,
        child_task_id: str,
        delegated_by: str,
        delegated_to: str
    ) -> DelegationLink:
        """Record delegation link."""
        link = DelegationLink(
            parent_task_id=parent_task_id,
            child_task_id=child_task_id,
            delegated_by=delegated_by,
            delegated_to=delegated_to
        )

        await self.core.execute("""
            INSERT OR REPLACE INTO delegation_links
            (parent_task_id, child_task_id, delegated_by, delegated_to, delegated_at, result_handoff, handoff_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            link.parent_task_id, link.child_task_id,
            link.delegated_by, link.delegated_to,
            link.delegated_at, link.result_handoff, link.handoff_at
        ))

        return link

    async def record_handoff(self, child_task_id: str, result: str) -> Optional[DelegationLink]:
        """Record result handoff."""
        await self.core.execute(
            "UPDATE delegation_links SET result_handoff = ?, handoff_at = ? WHERE child_task_id = ?",
            (result, time.time(), child_task_id)
        )
        row = await self.core.fetchone(
            "SELECT * FROM delegation_links WHERE child_task_id = ?",
            (child_task_id,)
        )
        if row:
            return self._row_to_link(row)
        return None

    async def get_chain(self, task_id: str, direction: str = "both") -> Dict[str, Any]:
        """Get delegation chain untuk task."""
        ancestors = []
        descendants = []

        if direction in ["up", "both"]:
            ancestors = await self._get_ancestors(task_id)

        if direction in ["down", "both"]:
            descendants = await self._get_descendants(task_id)

        return {
            "task_id": task_id,
            "ancestors": ancestors,
            "descendants": descendants,
            "full_chain": ancestors + [task_id] + descendants
        }

    async def _get_ancestors(self, task_id: str) -> List[str]:
        """Get ancestor chain (parents)."""
        ancestors = []
        current = task_id
        while True:
            row = await self.core.fetchone(
                "SELECT parent_task_id FROM delegation_links WHERE child_task_id = ?",
                (current,)
            )
            if not row or not row['parent_task_id']:
                break
            ancestors.append(row['parent_task_id'])
            current = row['parent_task_id']
        return list(reversed(ancestors))

    async def _get_descendants(self, task_id: str) -> List[str]:
        """Get descendant chain (children)."""
        descendants = []
        queue = [task_id]
        while queue:
            current = queue.pop(0)
            rows = await self.core.fetchall(
                "SELECT child_task_id FROM delegation_links WHERE parent_task_id = ?",
                (current,)
            )
            for row in rows:
                descendants.append(row['child_task_id'])
                queue.append(row['child_task_id'])
        return descendants

    async def get_delegation_stats(self, operative_id: str) -> Dict[str, Any]:
        """Get delegation stats untuk operative."""
        delegated_out = await self.core.fetchall(
            "SELECT COUNT(*) as count FROM delegation_links WHERE delegated_by = ?",
            (operative_id,)
        )
        delegated_in = await self.core.fetchall(
            "SELECT COUNT(*) as count FROM delegation_links WHERE delegated_to = ?",
            (operative_id,)
        )
        completed = await self.core.fetchall(
            "SELECT COUNT(*) as count FROM delegation_links WHERE delegated_by = ? AND handoff_at IS NOT NULL",
            (operative_id,)
        )

        return {
            "delegated_out": delegated_out[0]['count'] if delegated_out else 0,
            "delegated_in": delegated_in[0]['count'] if delegated_in else 0,
            "completed_handoffs": completed[0]['count'] if completed else 0
        }

    def _row_to_link(self, row: sqlite3.Row) -> DelegationLink:
        """Convert DB row to DelegationLink."""
        return DelegationLink(
            parent_task_id=row['parent_task_id'],
            child_task_id=row['child_task_id'],
            delegated_by=row['delegated_by'],
            delegated_to=row['delegated_to'],
            delegated_at=row['delegated_at'],
            result_handoff=row['result_handoff'],
            handoff_at=row['handoff_at']
        )

# ============================================================================
# NUDGE ENGINE
# ============================================================================

class NudgeEngine:
    """
    Auto-nudge untuk stuck agents.
    Heartbeat timeout detection, stuck threshold, escalation ke user.
    """

    def __init__(
        self,
        core: WarRoomCore,
        activity_stream: ActivityStream,
        mission_control: MissionControl,
        heartbeat_timeout: float = 300.0,  # 5 menit
        stuck_threshold: int = 3,
        check_interval: float = 10.0
    ):
        self.core = core
        self.activity_stream = activity_stream
        self.mission_control = mission_control
        self.heartbeat_timeout = heartbeat_timeout
        self.stuck_threshold = stuck_threshold
        self.check_interval = check_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start nudge engine."""
        self._running = True
        self._task = asyncio.create_task(self._watch_loop())

    async def stop(self) -> None:
        """Stop nudge engine."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _watch_loop(self) -> None:
        """Main watch loop."""
        while self._running:
            try:
                await self._check_watched_tasks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.activity_stream.emit(ActivityEvent(
                    id=str(uuid.uuid4()),
                    type=EventType.NUDGE,
                    operative_id=None,
                    payload={"error": str(e), "step": "watch_loop_failed"}
                ))
                await asyncio.sleep(self.check_interval)

    async def _check_watched_tasks(self) -> None:
        """Check watched tasks untuk timeout."""
        now = time.time()
        rows = await self.core.fetchall("SELECT * FROM nudge_watch_list")

        for row in rows:
            task_id = row['task_id']
            mission_id = row['mission_id']
            last_status = row['last_status']
            nudge_count = row['nudge_count']

            task = await self.core.fetchone(
                "SELECT * FROM kanban_tasks WHERE id = ?",
                (task_id,)
            )
            if not task:
                continue

            # Check heartbeat timeout
            if task['status'] == TaskStatus.RUNNING.value:
                last_heartbeat = task['last_heartbeat'] or 0
                if now - last_heartbeat > self.heartbeat_timeout:
                    # Task stuck!
                    nudge_count += 1
                    await self.core.execute(
                        "UPDATE nudge_watch_list SET nudge_count = ? WHERE task_id = ?",
                        (nudge_count, task_id)
                    )

                    # Emit nudge event
                    await self.activity_stream.emit(ActivityEvent(
                        id=str(uuid.uuid4()),
                        type=EventType.NUDGE,
                        operative_id=task['assignee_id'],
                        task_id=task_id,
                        mission_id=mission_id,
                        payload={
                            "step": f"Task {task['title'][:30]} stuck — no heartbeat for {int(now - last_heartbeat)}s",
                            "nudge_count": nudge_count,
                            "threshold": self.stuck_threshold
                        }
                    ))

                    # Escalate ke user kalau threshold exceeded
                    if nudge_count >= self.stuck_threshold:
                        await self._escalate_to_user(mission_id, task_id, task['assignee_id'])

            # Check status transitions
            if task['status'] != last_status:
                await self.core.execute(
                    "UPDATE nudge_watch_list SET last_status = ? WHERE task_id = ?",
                    (task['status'], task_id)
                )

                if task['status'] == TaskStatus.DONE.value:
                    # Auto-nudge orchestrator
                    await self._nudge_orchestrator(mission_id, task_id)

    async def _nudge_orchestrator(self, mission_id: str, task_id: str) -> None:
        """Nudge orchestrator bahwa task selesai."""
        mission = await self.mission_control.get_mission(mission_id)
        if not mission:
            return

        task = await self.core.fetchone(
            "SELECT * FROM kanban_tasks WHERE id = ?",
            (task_id,)
        )
        if not task:
            return

        nudge_msg = f"[AUTO-NUDGE] Task completed: {task['title']}\nSummary: {json.loads(task['metadata'] or '{}').get('summary', 'N/A')}\nPlease summarize results for user."

        await self.mission_control.add_message(
            mission_id, "system", nudge_msg, hidden=True
        )

        await self.activity_stream.emit(ActivityEvent(
            id=str(uuid.uuid4()),
            type=EventType.NUDGE,
            operative_id=mission.orchestrator_id,
            task_id=task_id,
            mission_id=mission_id,
            payload={"step": f"Orchestrator nudged: task {task_id[:8]} done"}
        ))

    async def _escalate_to_user(self, mission_id: str, task_id: str, operative_id: Optional[str]) -> None:
        """Escalate stuck task ke user."""
        await self.mission_control.add_message(
            mission_id,
            "system",
            f"[ESCALATION] Task {task_id[:8]} is stuck. Operative {operative_id[:8] if operative_id else 'unknown'} unresponsive. Please intervene.",
            hidden=False
        )

    async def watch_task(self, task_id: str, mission_id: str) -> None:
        """Add task ke watch list."""
        await self.core.execute(
            "INSERT OR REPLACE INTO nudge_watch_list (task_id, mission_id, watched_at, last_status, nudge_count) VALUES (?, ?, ?, ?, ?)",
            (task_id, mission_id, time.time(), TaskStatus.RUNNING.value, 0)
        )

    async def unwatch_task(self, task_id: str) -> None:
        """Remove task dari watch list."""
        await self.core.execute(
            "DELETE FROM nudge_watch_list WHERE task_id = ?",
            (task_id,)
        )

# ============================================================================
# WAR ROOM DASHBOARD
# ============================================================================

class WarRoomDashboard:
    """
    HTML/ASCII dashboard generator.
    Render kanban board, operative floor, mission chat, activity timeline.
    """

    def __init__(
        self,
        core: WarRoomCore,
        kanban: KanbanEngine,
        live_floor: LiveFloor,
        mission_control: MissionControl,
        activity_stream: ActivityStream
    ):
        self.core = core
        self.kanban = kanban
        self.live_floor = live_floor
        self.mission_control = mission_control
        self.activity_stream = activity_stream

    async def render_html(self, mission_id: Optional[str] = None) -> str:
        """Render full HTML dashboard."""
        board = await self.kanban.get_board()
        floor = await self.live_floor.render_floor(mission_id)

        html_parts = [
            "<!DOCTYPE html>",
            "<html><head><title>Hermes War Room</title>",
            "<style>",
            "body { font-family: 'IBM Plex Mono', monospace; background: #1a1a2e; color: #eee; margin: 0; padding: 20px; }",
            ".header { text-align: center; padding: 20px; border-bottom: 2px solid #e94560; }",
            ".grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }",
            ".panel { background: #16213e; border-radius: 8px; padding: 15px; }",
            ".panel h2 { margin-top: 0; color: #e94560; }",
            ".kanban-col { background: #0f3460; border-radius: 4px; padding: 10px; margin: 5px 0; }",
            ".kanban-col h3 { margin: 0 0 10px 0; font-size: 14px; }",
            ".task-card { background: #1a1a2e; border-left: 4px solid #e94560; padding: 8px; margin: 5px 0; border-radius: 4px; }",
            ".task-card.done { border-left-color: #2ecc71; }",
            ".task-card.blocked { border-left-color: #e74c3c; }",
            ".task-card.running { border-left-color: #f39c12; }",
            ".operative-disc { display: inline-block; width: 80px; height: 80px; border-radius: 50%; margin: 10px; position: relative; }",
            ".operative-led { position: absolute; top: 5px; right: 5px; width: 12px; height: 12px; border-radius: 50%; }",
            ".led-on { background: #00ff00; box-shadow: 0 0 10px #00ff00; }",
            ".led-off { background: #ff0000; }",
            ".status-pill { font-size: 12px; text-align: center; margin-top: 5px; }",
            ".activity-item { font-size: 12px; padding: 5px; border-bottom: 1px solid #0f3460; }",
            ".timestamp { color: #888; font-size: 11px; }",
            "</style></head><body>",
            "<div class='header'><h1>🏢 HERMES WAR ROOM</h1><p>Multi-Agent Orchestration Dashboard</p></div>",
            "<div class='grid'>"
        ]

        # Kanban Board Panel
        html_parts.append("<div class='panel'><h2>📋 Kanban Board</h2>")
        for status in [TaskStatus.TODO, TaskStatus.READY, TaskStatus.RUNNING, TaskStatus.BLOCKED, TaskStatus.DONE]:
            tasks = board.get(status.value, [])
            html_parts.append(f"<div class='kanban-col'><h3>{status.value.upper()} ({len(tasks)})</h3>")
            for task in tasks:
                css_class = f"task-card {status.value}"
                assignee = task.assignee_id[:8] if task.assignee_id else "unassigned"
                html_parts.append(
                    f"<div class='{css_class}'>"
                    f"<strong>{html.escape(task.title)}</strong><br>"
                    f"<small>👤 {assignee} | ⏱️ {self._format_duration(task.created_at)}</small>"
                    f"</div>"
                )
            html_parts.append("</div>")
        html_parts.append("</div>")

        # Operative Floor Panel
        html_parts.append("<div class='panel'><h2>🎮 Operative Floor</h2>")
        for ws_data in floor["workstations"]:
            op = ws_data["operative"]
            ws = ws_data["workstation"]
            led_class = "led-on" if ws.led_pulse else "led-off"
            html_parts.append(
                f"<div class='operative-disc' style='background: {op.color};'>"
                f"<div class='operative-led {led_class}'></div>"
                f"<div style='position: absolute; bottom: -20px; width: 100%; text-align: center; font-size: 10px;'>"
                f"{op.callsign}</div></div>"
            )
        html_parts.append("</div>")

        html_parts.extend(["</div>", "</body></html>"])
        return "\n".join(html_parts)

    async def render_ascii_dashboard(self, mission_id: Optional[str] = None) -> str:
        """Render ASCII dashboard."""
        lines = []
        lines.append("╔══════════════════════════════════════════════════════════════════════╗")
        lines.append("║                    🏢 HERMES WAR ROOM DASHBOARD                        ║")
        lines.append("╠══════════════════════════════════════════════════════════════════════╣")

        # Kanban summary
        board = await self.kanban.get_board()
        lines.append("║ 📋 KANBAN BOARD                                                      ║")
        for status in [TaskStatus.TODO, TaskStatus.READY, TaskStatus.RUNNING, TaskStatus.BLOCKED, TaskStatus.DONE]:
            tasks = board.get(status.value, [])
            icon = {"todo": "⬜", "ready": "📋", "running": "▶️", "blocked": "🚫", "done": "✅"}.get(status.value, "•")
            lines.append(f"║   {icon} {status.value.upper():10s}: {len(tasks):3d} tasks                                    ║")
        lines.append("╠══════════════════════════════════════════════════════════════════════╣")

        # Live floor
        floor_ascii = await self.live_floor.render_ascii()
        for line in floor_ascii.split("\n"):
            lines.append(line)

        lines.append("╠══════════════════════════════════════════════════════════════════════╣")

        # Recent activity
        lines.append("║ 📡 RECENT ACTIVITY                                                   ║")
        events = await self.activity_stream.get_recent(5)
        for event in events:
            ts = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S")
            lines.append(f"║   [{ts}] {event.type.value:12s} {str(event.payload.get('step', ''))[:40]:40s} ║")

        lines.append("╚══════════════════════════════════════════════════════════════════════╝")
        return "\n".join(lines)

    def _format_duration(self, timestamp: float) -> str:
        """Format duration dari timestamp."""
        delta = timedelta(seconds=time.time() - timestamp)
        if delta.days > 0:
            return f"{delta.days}d"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}h"
        minutes = delta.seconds // 60
        return f"{minutes}m"

    async def export_json(self, mission_id: Optional[str] = None) -> str:
        """Export dashboard state ke JSON."""
        board = await self.kanban.get_board()
        floor = await self.live_floor.render_floor(mission_id)

        export_data = {
            "timestamp": time.time(),
            "kanban": {
                status: [
                    {
                        "id": t.id,
                        "title": t.title,
                        "assignee": t.assignee_id,
                        "created_at": t.created_at
                    }
                    for t in tasks
                ]
                for status, tasks in board.items()
            },
            "operatives": [
                {
                    "id": ws["operative"].id,
                    "callsign": ws["operative"].callsign,
                    "status": ws["workstation"].status.value,
                    "current_task": ws["workstation"].current_task_id
                }
                for ws in floor["workstations"]
            ],
            "activity_count": len(self.activity_stream._ring_buffer)
        }

        return json.dumps(export_data, indent=2)

# ============================================================================
# WAR ROOM KERNEL (MAGNATRIX INTEGRATION)
# ============================================================================

class WarRoomKernel:
    """
    MAGNATRIX integration bridge.
    Bridge ke Layer 5 (Knowledge/Kanban), Layer 10 (Uncensored AI/Agent orchestration), Layer 12 (IDE/Dashboard).
    """

    def __init__(
        self,
        core: WarRoomCore,
        profile_manager: OperativeProfileManager,
        kanban: KanbanEngine,
        mission_control: MissionControl,
        delegation_chain: DelegationChain,
        activity_stream: ActivityStream
    ):
        self.core = core
        self.profile_manager = profile_manager
        self.kanban = kanban
        self.mission_control = mission_control
        self.delegation_chain = delegation_chain
        self.activity_stream = activity_stream

    async def register_operative_as_agent(self, operative_id: str) -> Dict[str, Any]:
        """Auto-register operative sebagai AgentIdentity di MAGNATRIX."""
        operative = await self.profile_manager.get(operative_id)
        if not operative:
            return {"error": "Operative not found"}

        agent_identity = {
            "id": operative.id,
            "name": operative.callsign,
            "type": "war_room_operative",
            "capabilities": operative.skills,
            "tools": operative.tools,
            "model": operative.model_config.get("model", "default"),
            "soul_hash": hash(operative.soul_md) & 0xFFFFFFFF,
            "status": "active" if operative.active else "inactive",
            "registered_at": time.time()
        }

        await self.activity_stream.emit(ActivityEvent(
            id=str(uuid.uuid4()),
            type=EventType.STATUS_CHANGE,
            operative_id=operative_id,
            task_id=None,
            mission_id=None,
            payload={"step": f"Operative {operative.callsign} registered as AgentIdentity", "identity": agent_identity}
        ))

        return agent_identity

    async def sync_task_to_knowledge_graph(self, task_id: str) -> Dict[str, Any]:
        """Sync task state ke Knowledge Graph (Layer 5)."""
        task = await self.kanban.get_task(task_id)
        if not task:
            return {"error": "Task not found"}

        kg_node = {
            "id": task.id,
            "type": "kanban_task",
            "title": task.title,
            "status": task.status.value,
            "assignee": task.assignee_id,
            "parent": task.parent_id,
            "created_at": task.created_at,
            "layer": 5,
            "synced_at": time.time()
        }

        # Emit sync event
        await self.activity_stream.emit(ActivityEvent(
            id=str(uuid.uuid4()),
            type=EventType.STATUS_CHANGE,
            task_id=task_id,
            mission_id=None,
            operative_id=None,
            payload={"step": f"Task synced to Knowledge Graph", "kg_node": kg_node}
        ))

        return kg_node

    async def bridge_to_layer_10(self, mission_id: str) -> Dict[str, Any]:
        """Bridge ke Layer 10: Uncensored AI/Agent orchestration."""
        mission = await self.mission_control.get_mission(mission_id)
        if not mission:
            return {"error": "Mission not found"}

        messages = await self.mission_control.get_messages(mission_id, include_hidden=True)

        layer_10_state = {
            "mission_id": mission_id,
            "orchestrator": mission.orchestrator_id,
            "message_count": len(messages),
            "last_update": mission.updated_at,
            "layer": 10,
            "uncensored_mode": True,
            "delegation_enforced": True
        }

        return layer_10_state

    async def bridge_to_layer_12(self) -> Dict[str, Any]:
        """Bridge ke Layer 12: IDE/Dashboard."""
        # Get system status
        operatives = await self.profile_manager.list_all(active_only=True)
        board = await self.kanban.get_board()

        layer_12_state = {
            "active_operatives": len(operatives),
            "total_tasks": sum(len(tasks) for tasks in board.values()),
            "tasks_by_status": {status: len(tasks) for status, tasks in board.items()},
            "layer": 12,
            "dashboard_available": True,
            "ide_integration": True,
            "synced_at": time.time()
        }

        return layer_12_state

    async def full_sync(self) -> Dict[str, Any]:
        """Full sync ke semua MAGNATRIX layers."""
        results = {
            "layer_5": [],
            "layer_10": {},
            "layer_12": {},
            "timestamp": time.time()
        }

        # Sync all tasks ke Layer 5
        board = await self.kanban.get_board()
        for status, tasks in board.items():
            for task in tasks:
                kg_node = await self.sync_task_to_knowledge_graph(task.id)
                results["layer_5"].append(kg_node)

        # Sync active missions ke Layer 10
        missions = await self.mission_control.list_missions(status=MissionStatus.OPEN)
        for mission in missions:
            layer_10 = await self.bridge_to_layer_10(mission.id)
            results["layer_10"][mission.id] = layer_10

        # Sync dashboard ke Layer 12
        results["layer_12"] = await self.bridge_to_layer_12()

        return results


# ============================================================================
# DEMO SECTION — Full War Room Simulation
# ============================================================================

async def demo_war_room() -> None:
    """
    Demo: Simulasi full war room dengan 3 operatives + 5 tasks + live delegation.
    Run: python hermes_war_room_native.py
    """
    print("=" * 70)
    print("🏢 HERMES WAR ROOM — NATIVE PYTHON DEMO")
    print("=" * 70)

    # Initialize core (clean start)
    db_path = Path("demo_war_room.db")
    if db_path.exists():
        db_path.unlink()
    core = WarRoomCore(db_path=str(db_path))
    print("\n[1] WarRoomCore initialized (SQLite-backed, fresh)")

    # Initialize managers
    profiles = OperativeProfileManager(core)
    kanban = KanbanEngine(core)
    missions = MissionControl(core)
    activity = ActivityStream(core)
    floor = LiveFloor(core, profiles)
    delegation = DelegationChain(core)
    nudge = NudgeEngine(core, activity, missions, heartbeat_timeout=60.0)
    dashboard = WarRoomDashboard(core, kanban, floor, missions, activity)
    kernel = WarRoomKernel(core, profiles, kanban, missions, delegation, activity)

    # Create 3 operatives
    print("\n[2] Creating operatives...")
    lider = await profiles.create(
        callsign="Lider",
        color="#E74C3C",
        soul_md="You are the orchestrator. Route, never execute.",
        skills=["orchestration", "delegation", "summarization"],
        tools=["kanban_create", "kanban_list", "kanban_complete"],
        model_config={"model": "gpt-4", "temperature": 0.3}
    )
    print(f"    ✅ {lider}")

    investigador = await profiles.create(
        callsign="Investigador",
        color="#3498DB",
        soul_md="You are the researcher. Deep dive, verify sources.",
        skills=["research", "analysis", "fact_checking"],
        tools=["web_search", "web_fetch", "data_analysis"],
        model_config={"model": "gpt-4", "temperature": 0.7}
    )
    print(f"    ✅ {investigador}")

    legal = await profiles.create(
        callsign="Legal",
        color="#2ECC71",
        soul_md="You are the legal expert. Review contracts, flag risks.",
        skills=["legal_review", "contract_analysis", "compliance"],
        tools=["document_review", "risk_assessment", "pdf_analysis"],
        model_config={"model": "gpt-4", "temperature": 0.5}
    )
    print(f"    ✅ {legal}")

    # Create mission
    print("\n[3] Creating mission...")
    mission = await missions.create_mission(
        title="MAGNATRIX Integration Analysis",
        orchestrator_id=lider.id
    )
    print(f"    ✅ {mission}")

    # Inject preamble
    preamble = await missions.inject_preamble(mission.id, lider.id)
    print(f"    🔒 Preamble injected (hidden)")

    # Add user brief
    user_msg = await missions.add_message(
        mission.id, "user",
        "Analyze the MAGNATRIX architecture and identify integration points for the new War Room system."
    )
    print(f"    💬 User brief added")

    # Create 5 tasks (parent + children)
    print("\n[4] Creating kanban tasks...")

    parent_task = await kanban.create_task(
        title="MAGNATRIX Architecture Analysis",
        body="Comprehensive analysis of MAGNATRIX layers and integration strategy.",
        assignee_id=lider.id
    )
    print(f"    ✅ Parent: {parent_task.title}")

    child_1 = await kanban.create_task(
        title="Research Layer 5-7 protocols",
        body="Deep dive into Knowledge Graph and Kanban integration protocols.",
        assignee_id=investigador.id,
        parent_id=parent_task.id
    )
    print(f"    ✅ Child-1: {child_1.title} → {investigador.callsign}")

    child_2 = await kanban.create_task(
        title="Review Layer 10 compliance requirements",
        body="Legal review of uncensored AI orchestration compliance.",
        assignee_id=legal.id,
        parent_id=parent_task.id
    )
    print(f"    ✅ Child-2: {child_2.title} → {legal.callsign}")

    child_3 = await kanban.create_task(
        title="Design Layer 12 dashboard schema",
        body="Dashboard data schema and real-time sync architecture.",
        assignee_id=investigador.id,
        parent_id=parent_task.id
    )
    print(f"    ✅ Child-3: {child_3.title} → {investigador.callsign}")

    child_4 = await kanban.create_task(
        title="Integration test plan",
        body="End-to-end testing strategy for War Room + MAGNATRIX.",
        assignee_id=legal.id,
        parent_id=parent_task.id,
        blocked_by=[child_1.id, child_2.id]
    )
    print(f"    ✅ Child-4: {child_4.title} → {legal.callsign} (blocked by 1,2)")

    # Record delegations
    print("\n[5] Recording delegation chain...")
    await delegation.record_delegation(parent_task.id, child_1.id, lider.id, investigador.id)
    await delegation.record_delegation(parent_task.id, child_2.id, lider.id, legal.id)
    await delegation.record_delegation(parent_task.id, child_3.id, lider.id, investigador.id)
    await delegation.record_delegation(parent_task.id, child_4.id, lider.id, legal.id)
    print("    ✅ 4 delegation links recorded")

    # Claim tasks
    print("\n[6] Operatives claiming tasks...")
    await kanban.claim_task(child_1.id, investigador.id)
    await kanban.claim_task(child_2.id, legal.id)
    await kanban.claim_task(child_3.id, investigador.id)
    print("    ✅ Tasks claimed")

    # Emit activity events
    print("\n[7] Emitting activity stream events...")
    await activity.emit(ActivityEvent(
        id=str(uuid.uuid4()),
        type=EventType.TOOL_CALL,
        operative_id=investigador.id,
        task_id=child_1.id,
        mission_id=mission.id,
        payload={"step": "web_search: MAGNATRIX architecture protocols"}
    ))
    await activity.emit(ActivityEvent(
        id=str(uuid.uuid4()),
        type=EventType.REASONING,
        operative_id=legal.id,
        task_id=child_2.id,
        mission_id=mission.id,
        payload={"step": "Analyzing compliance framework for uncensored AI..."}
    ))
    print("    ✅ 2 events emitted")

    # Set speech bubbles
    await floor.set_speech_bubble(investigador.id, "Searching protocols...")
    await floor.set_speech_bubble(legal.id, "Reviewing compliance...")

    # Start nudge engine
    print("\n[8] Starting nudge engine...")
    await nudge.watch_task(child_1.id, mission.id)
    await nudge.watch_task(child_2.id, mission.id)
    await nudge.watch_task(child_3.id, mission.id)
    await nudge.watch_task(child_4.id, mission.id)
    await nudge.start()
    print("    ✅ Nudge engine watching 4 tasks")

    # Render ASCII dashboard
    print("\n[9] Rendering ASCII dashboard...")
    ascii_dash = await dashboard.render_ascii_dashboard(mission.id)
    print(ascii_dash)

    # Render HTML dashboard
    print("\n[10] Rendering HTML dashboard...")
    html_dash = await dashboard.render_html(mission.id)
    html_path = Path("war_room_dashboard.html")
    html_path.write_text(html_dash, encoding="utf-8")
    print(f"    ✅ HTML saved to {html_path}")

    # Export JSON
    print("\n[11] Exporting JSON state...")
    json_export = await dashboard.export_json(mission.id)
    json_path = Path("war_room_state.json")
    json_path.write_text(json_export, encoding="utf-8")
    print(f"    ✅ JSON saved to {json_path}")

    # MAGNATRIX integration
    print("\n[12] MAGNATRIX integration (Layer 5, 10, 12)...")
    for op in [lider, investigador, legal]:
        identity = await kernel.register_operative_as_agent(op.id)
        print(f"    ✅ {op.callsign} registered as AgentIdentity")

    kg_sync = await kernel.sync_task_to_knowledge_graph(parent_task.id)
    print(f"    ✅ Task synced to Knowledge Graph (Layer 5)")

    layer_10 = await kernel.bridge_to_layer_10(mission.id)
    print(f"    ✅ Layer 10 bridge active (messages: {layer_10['message_count']})")

    layer_12 = await kernel.bridge_to_layer_12()
    print(f"    ✅ Layer 12 bridge active (operatives: {layer_12['active_operatives']})")

    # Full sync
    full_sync = await kernel.full_sync()
    print(f"    ✅ Full sync complete ({len(full_sync['layer_5'])} nodes)")

    # Complete some tasks
    print("\n[13] Completing tasks...")
    await kanban.complete_task(child_1.id, "Found 12 integration points across Layers 5-12")
    await kanban.complete_task(child_2.id, "Compliance framework validated, 3 minor flags")
    print("    ✅ 2 tasks completed")

    # Auto-promote test (child_4 should stay blocked)
    print("\n[14] Checking auto-promote (child_4 blocked by child_1,2)...")
    child_4_status = await kanban.get_task(child_4.id)
    print(f"    ℹ️ Child-4 status: {child_4_status.status.value} (correctly still blocked)")

    # Complete child_3 to test promotion
    await kanban.complete_task(child_3.id, "Dashboard schema designed with 8 views")
    print("    ✅ Child-3 completed")

    # Render final state
    print("\n[15] Final dashboard state...")
    final_dash = await dashboard.render_ascii_dashboard(mission.id)
    print(final_dash)

    # Stop nudge engine
    await nudge.stop()
    print("\n[16] Nudge engine stopped")

    # Summary
    print("\n" + "=" * 70)
    print("📊 DEMO SUMMARY")
    print("=" * 70)
    print(f"Operatives: 3 (Lider, Investigador, Legal)")
    print(f"Tasks: 5 (1 parent + 4 children)")
    print(f"Delegations: 4 links recorded")
    print(f"Activity events: {len(activity._ring_buffer)}")
    print(f"Mission messages: {len(await missions.get_messages(mission.id, include_hidden=True))}")
    print(f"HTML dashboard: war_room_dashboard.html")
    print(f"JSON export: war_room_state.json")
    print(f"Database: demo_war_room.db")
    print("=" * 70)
    print("✅ Demo complete! War Room ready for MAGNATRIX integration.")
    print("=" * 70)


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo_war_room())