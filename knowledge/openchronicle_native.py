#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAGNATRIX-OS — OpenChronicle Native Integration
═══════════════════════════════════════════════════════════════════════════════
AMATI-PELAJARI-TIRU dari Einsia/OpenChronicle

Pola yang ditiru:
• Local-first memory — Markdown + SQLite on machine, tidak ada data ke cloud
• AX-first capture — Accessibility tree events sebagai primary signal,
  screenshot sebagai secondary
• Event-driven pipeline — watcher → dispatcher (dedup/debounce/gap)
  → S1 parser → capture buffer → timeline normalizer → session manager
  → reducer → classifier → memory files
• Timeline normalizer — wall-clock aligned 1-minute blocks,
  verbatim-preserving (tidak paraphrase user typed text), UI chrome stripping
• Session management — hard cut (idle 5min), soft cut (unrelated app 3min),
  timeout (2h max), flush tick (5min)
• Memory format — structured Markdown: user-, project-, tool-, topic-,
  person-, org-, event-YYYY-MM-DD.md
• Supersede-not-delete — history entries superseded oleh newer version,
  replacement chain tracked
• MCP endpoint — tool-calling agents query memory via read_memory()
• Buffer hygiene — tiered retention: 7 days delete, 24h strip screenshot,
  2GB size cap eviction
• Content dedup — hash fingerprint (bundle + title + focused.value + text + url)
• Classifier — auto-route entries ke correct memory file
• SQLite FTS5 — full-text search indexing

Layer: Knowledge (5) — Persistent Local-First Memory System
Versi: Phase 5 — OpenChronicle Native Memory Layer
"""

from __future__ import annotations
from storage.file_ops_native import open as _secure_open

import hashlib
import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ═════════════════════════════════════════════════════════════════════════════
# 0. UTILITAS DASAR
# ═════════════════════════════════════════════════════════════════════════════

def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def _now_minute_aligned() -> datetime:
    """Wall-clock aligned ke minute boundary (:00, :01, ...)."""
    now = datetime.utcnow()
    return now.replace(second=0, microsecond=0)

def _hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()[:16]

def _iso_to_filename(ts: str) -> str:
    """Convert ISO timestamp ke safe filename: : → -, + → p, - → m."""
    return ts.replace(":", "-").replace("+", "p").replace("-", "m", 1)


# ═════════════════════════════════════════════════════════════════════════════
# 1. CAPTURE DISPATCHER — Debounce, Dedup, Gap Control
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class CaptureEvent:
    """Satu raw capture event dari AX watcher atau heartbeat."""
    timestamp: float
    event_type: str  # AXValueChanged, AXFocusChanged, heartbeat, etc.
    app_bundle: str
    window_title: str
    raw_ax_tree: Optional[Dict[str, Any]] = None
    screenshot_b64: Optional[str] = None
    triggered_by: str = "watcher"

@dataclass
class S1Capture:
    """S1 enriched capture: parsed dari raw AX tree."""
    timestamp: float
    app_bundle: str
    window_title: str
    focused_element: Dict[str, Any]  # role, title, value, is_editable
    visible_text: str  # pre-rendered markdown view of AX tree, capped 10KB
    url: Optional[str]  # regex extracted dari visible text
    screenshot_b64: Optional[str]
    content_fingerprint: str  # hash(bundle + title + focused.value + text + url)

class CaptureDispatcher:
    """
    Dispatcher untuk capture events dengan 4 time-based knobs:
    • debounce_seconds: collapse AXValueChanged dalam window
    • dedup_interval_seconds: drop same (event_type, app) pair
    • min_capture_gap_seconds: hard floor antara consecutive captures
    • same_window_dedup_seconds: collapse non-focus-change events
    Plus content dedup: hash fingerprint comparison.
    """

    def __init__(self,
                 debounce_seconds: float = 3.0,
                 dedup_interval_seconds: float = 1.0,
                 min_capture_gap_seconds: float = 2.0,
                 same_window_dedup_seconds: float = 5.0,
                 heartbeat_minutes: float = 10.0) -> None:
        self.debounce = debounce_seconds
        self.dedup_interval = dedup_interval_seconds
        self.min_gap = min_capture_gap_seconds
        self.same_window_dedup = same_window_dedup_seconds
        self.heartbeat = heartbeat_minutes * 60

        self.last_capture_time: float = 0.0
        self.last_event_signature: Optional[str] = None
        self.last_fingerprint: Optional[str] = None
        self.last_window_key: Optional[str] = None
        self.last_window_time: float = 0.0
        self.pending_debounce: Optional[CaptureEvent] = None
        self.debounce_timer: Optional[float] = None

    def dispatch(self, event: CaptureEvent) -> Optional[S1Capture]:
        """
        Process incoming event. Return S1Capture kalau should capture,
        None kalau dropped.
        """
        now = time.time()
        sig = f"{event.event_type}:{event.app_bundle}"
        window_key = f"{event.app_bundle}:{event.window_title}"

        # Rule 1: min capture gap
        if now - self.last_capture_time < self.min_gap:
            return None

        # Rule 2: dedup interval for same (event_type, app)
        if sig == self.last_event_signature and now - self.last_capture_time < self.dedup_interval:
            return None

        # Rule 3: debounce AXValueChanged
        if event.event_type == "AXValueChanged":
            self.pending_debounce = event
            self.debounce_timer = now
            # Don't capture yet — wait for debounce window to settle
            return None

        # Flush any pending debounce bila focus change atau debounce expired
        if self.pending_debounce and (event.event_type == "AXFocusChanged"
                                       or now - self.debounce_timer > self.debounce):
            debounced_event = self.pending_debounce
            self.pending_debounce = None
            self.debounce_timer = None
            # Process debounced event
            return self._process_event(debounced_event, now)

        # Rule 4: same window dedup untuk non-focus-change
        if event.event_type != "AXFocusChanged" and window_key == self.last_window_key:
            if now - self.last_window_time < self.same_window_dedup:
                return None

        self.last_window_key = window_key
        self.last_window_time = now
        return self._process_event(event, now)

    def _process_event(self, event: CaptureEvent, now: float) -> Optional[S1Capture]:
        # S1 parsing
        s1 = self._s1_parse(event)
        if not s1:
            return None

        # Content dedup
        if s1.content_fingerprint == self.last_fingerprint:
            return None
        self.last_fingerprint = s1.content_fingerprint
        self.last_capture_time = now
        self.last_event_signature = f"{event.event_type}:{event.app_bundle}"

        return s1

    def _s1_parse(self, event: CaptureEvent) -> Optional[S1Capture]:
        """Parse raw AX tree ke S1 fields."""
        ax = event.raw_ax_tree or {}

        # Extract focused element
        focused = ax.get("focused_element", {})
        focused_val = focused.get("value", "")
        is_editable = focused.get("is_editable", False)

        # Extract visible text — pre-rendered markdown view
        visible = self._render_visible_text(ax)
        visible = visible[:10000]  # cap at 10KB

        # Extract URL dari visible text
        url = self._extract_url(visible)

        # Content fingerprint (exclude timestamp, trigger, screenshot)
        fp_data = f"{event.app_bundle}:{event.window_title}:{focused_val}:{visible}:{url}"
        fingerprint = _hash(fp_data)

        return S1Capture(
            timestamp=event.timestamp,
            app_bundle=event.app_bundle,
            window_title=event.window_title,
            focused_element=focused,
            visible_text=visible,
            url=url,
            screenshot_b64=event.screenshot_b64,
            content_fingerprint=fingerprint,
        )

    @staticmethod
    def _render_visible_text(ax: Dict[str, Any]) -> str:
        """Render AX tree ke markdown-like visible text."""
        elements = ax.get("elements", [])
        lines = []
        for el in elements:
            role = el.get("role", "")
            title = el.get("title", "")
            value = el.get("value", "")
            if role in ("button", "link", "heading", "text"):
                if title:
                    lines.append(f"[{role}] {title}")
                if value and len(value) < 500:
                    lines.append(f"  → {value[:200]}")
        return "\n".join(lines)

    @staticmethod
    def _extract_url(text: str) -> Optional[str]:
        """Extract URL dari text via regex."""
        pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+'
        match = re.search(pattern, text)
        return match.group(0) if match else None

    def heartbeat_tick(self) -> Optional[S1Capture]:
        """Generate heartbeat capture kalau no recent activity."""
        now = time.time()
        if self.heartbeat > 0 and now - self.last_capture_time > self.heartbeat:
            event = CaptureEvent(
                timestamp=now,
                event_type="heartbeat",
                app_bundle="system",
                window_title="idle",
                triggered_by="heartbeat",
            )
            return self._process_event(event, now)
        return None


# ═════════════════════════════════════════════════════════════════════════════
# 2. TIMELINE NORMALIZER — Wall-Clock Aligned Verbatim Preserving
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class TimelineBlock:
    """Satu 1-minute timeline block, wall-clock aligned."""
    start_time: datetime
    end_time: datetime
    captures: List[S1Capture] = field(default_factory=list)
    normalized_text: str = ""
    block_id: str = ""

    def __post_init__(self):
        if not self.block_id:
            self.block_id = f"block-{_hash(str(self.start_time))}"

class TimelineNormalizer:
    """
    Timeline = verbatim-preserving normalizer antara raw captures dan reducer.
    • 1-minute wall-clock aligned blocks (:00/:01/:02...)
    • Strip UI chrome, keep authored text verbatim
    • Deduplicate snapshots, preserve proper nouns
    • Max 30 events per window
    """

    def __init__(self, window_minutes: int = 1,
                 max_events_per_window: int = 30) -> None:
        self.window = timedelta(minutes=window_minutes)
        self.max_events = max_events_per_window
        self.blocks: Dict[str, TimelineBlock] = {}  # key = start_time iso

    def ingest_captures(self, captures: List[S1Capture]) -> List[TimelineBlock]:
        """Assign captures ke timeline blocks."""
        for cap in captures:
            dt = datetime.utcfromtimestamp(cap.timestamp)
            block_start = dt.replace(second=0, microsecond=0)
            # Align ke window boundary
            if self.window.seconds >= 60:
                minute = (dt.minute // self.window.seconds * 60) * (self.window.seconds // 60)
                block_start = block_start.replace(minute=minute)

            key = block_start.isoformat()
            if key not in self.blocks:
                self.blocks[key] = TimelineBlock(
                    start_time=block_start,
                    end_time=block_start + self.window,
                )
            block = self.blocks[key]
            if len(block.captures) < self.max_events:
                block.captures.append(cap)

        return list(self.blocks.values())

    def normalize_block(self, block: TimelineBlock) -> str:
        """
        Normalize satu block: strip UI chrome, deduplicate, preserve verbatim.
        Return normalized text string.
        """
        records: List[str] = []
        seen_contexts: Set[str] = set()

        for cap in sorted(block.captures, key=lambda c: c.timestamp):
            # Build context key
            context = f"[{cap.app_bundle}] {cap.window_title}"
            if context in seen_contexts:
                # Same context: merge, keep latest
                continue
            seen_contexts.add(context)

            # Extract authored text dari focused element
            authored = ""
            focused = cap.focused_element
            if focused.get("is_editable") and focused.get("value_length", 0) > 0:
                authored = f'"{focused["value"][:500]}"'

            # Build normalized record
            url_str = f" ({cap.url})" if cap.url else ""
            record = f"[{cap.app_bundle}] {cap.window_title}{url_str}: {cap.visible_text[:200]}"
            if authored:
                record += f". Latest version {authored}"

            # Extract people/topics
            people = self._extract_proper_nouns(cap.visible_text)
            if people:
                record += f". Involving: {', '.join(people[:5])}"

            records.append(record)

        block.normalized_text = "\n".join(records)
        return block.normalized_text

    @staticmethod
    def _extract_proper_nouns(text: str) -> List[str]:
        """Extract proper nouns / named entities dari text."""
        # Simplified: capitalize words yang mungkin nama
        words = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', text)
        return list(set(words))[:10]

    def close_old_blocks(self, before: datetime) -> List[TimelineBlock]:
        """Return and remove blocks yang sudah closed."""
        closed = []
        keys_to_remove = []
        for key, block in self.blocks.items():
            if block.end_time <= before:
                self.normalize_block(block)
                closed.append(block)
                keys_to_remove.append(key)
        for k in keys_to_remove:
            del self.blocks[k]
        return closed


# ═════════════════════════════════════════════════════════════════════════════
# 3. SESSION MANAGER — Hard Cut, Soft Cut, Timeout
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class Session:
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    app_history: List[str] = field(default_factory=list)
    blocks: List[TimelineBlock] = field(default_factory=list)
    status: str = "active"  # active, flushing, closed
    flush_end: Optional[datetime] = None
    classified_end: Optional[datetime] = None

class SessionManager:
    """
    Session manager dengan 3 cut rules:
    1. Hard cut: idle > gap_minutes → session ends at last event
    2. Soft cut: unrelated app > soft_cut_minutes + no frequent-switching
    3. Timeout: session > max_session_hours → force cut
    Plus flush tick: incremental reducer every flush_minutes.
    """

    def __init__(self,
                 gap_minutes: float = 5.0,
                 soft_cut_minutes: float = 3.0,
                 max_session_hours: float = 2.0,
                 flush_minutes: float = 5.0,
                 tick_seconds: float = 30.0) -> None:
        self.gap = gap_minutes * 60
        self.soft_cut = soft_cut_minutes * 60
        self.max_hours = max_session_hours * 3600
        self.flush = flush_minutes * 60
        self.tick = tick_seconds

        self.sessions: List[Session] = []
        self.current_session: Optional[Session] = None
        self.last_event_time: float = 0.0
        self.last_app_switch_time: float = 0.0
        self.recent_apps: List[Tuple[float, str]] = []  # (time, app)

    def on_event(self, capture: S1Capture) -> Optional[Session]:
        """Process capture event, manage session lifecycle."""
        now = capture.timestamp
        app = capture.app_bundle

        self.recent_apps.append((now, app))
        # Keep only last 2 minutes
        self.recent_apps = [(t, a) for t, a in self.recent_apps if now - t < 120]

        # Check cuts
        ended_session = self._check_cuts(now, app)

        # Start new session if needed
        if not self.current_session or self.current_session.status == "closed":
            self.current_session = Session(
                session_id=f"sess-{_hash(str(now))}",
                start_time=now,
                app_history=[app],
            )
            self.sessions.append(self.current_session)

        self.current_session.app_history.append(app)
        self.last_event_time = now

        return ended_session

    def _check_cuts(self, now: float, app: str) -> Optional[Session]:
        if not self.current_session:
            return None

        session = self.current_session
        elapsed = now - session.start_time

        # Cut 1: Hard cut (idle gap)
        if now - self.last_event_time > self.gap and self.last_event_time > 0:
            session.end_time = self.last_event_time
            session.status = "closed"
            return session

        # Cut 2: Soft cut (unrelated app)
        if self.recent_apps:
            recent_unique = set(a for t, a in self.recent_apps if now - t < 120)
            frequent_switching = len(recent_unique) >= 2
            if not frequent_switching and now - self.last_app_switch_time > self.soft_cut:
                if len(set(session.app_history[-5:])) == 1 and app != session.app_history[-1]:
                    session.end_time = now
                    session.status = "closed"
                    return session

        # Cut 3: Timeout
        if elapsed > self.max_hours:
            session.end_time = now
            session.status = "closed"
            return session

        # Track app switch
        if session.app_history and app != session.app_history[-1]:
            self.last_app_switch_time = now

        return None

    def add_timeline_block(self, block: TimelineBlock) -> None:
        if self.current_session and self.current_session.status == "active":
            self.current_session.blocks.append(block)

    def should_flush(self, now: float) -> bool:
        """Check whether incremental reducer flush should run."""
        if not self.current_session or self.current_session.status != "active":
            return False
        last_flush = self.current_session.flush_end
        if not last_flush:
            return True
        return (now - last_flush.timestamp()) > self.flush

    def mark_flush(self, now: datetime) -> None:
        if self.current_session:
            self.current_session.flush_end = now

    def get_active_session(self) -> Optional[Session]:
        return self.current_session if self.current_session and self.current_session.status == "active" else None

    def get_all_sessions(self) -> List[Session]:
        return self.sessions


# ═════════════════════════════════════════════════════════════════════════════
# 4. REDUCER — Compress Timeline Blocks → Event Entries
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class EventEntry:
    entry_id: str
    session_id: str
    timestamp: datetime
    duration_minutes: float
    app: str
    context: str  # title/URL/file
    summary: str
    verbatim_snippets: List[str]  # user typed text preserved
    people: List[str]
    topics: List[str]
    tools: List[str]
    tags: List[str] = field(default_factory=list)
    superseded_by: Optional[str] = None

class SessionReducer:
    """
    Reducer: compress timeline blocks per session menjadi event entries.
    Incremental flush setiap 5 menit, final reducer pas session close.
    """

    def __init__(self, model_callback: Optional[Callable[[str], str]] = None) -> None:
        self.model = model_callback  # LLM callback untuk summarization
        self.entries: List[EventEntry] = []

    def reduce_session(self, session: Session, is_final: bool = False) -> List[EventEntry]:
        """Reduce satu session's blocks menjadi event entries."""
        if not session.blocks:
            return []

        # Group blocks by contiguous activity
        groups = self._group_blocks(session.blocks)
        new_entries = []

        for group in groups:
            entry = self._reduce_group(session.session_id, group)
            new_entries.append(entry)
            self.entries.append(entry)

        if is_final:
            session.status = "closed"

        return new_entries

    def _group_blocks(self, blocks: List[TimelineBlock]) -> List[List[TimelineBlock]]:
        """Group contiguous blocks dengan same app/context."""
        if not blocks:
            return []
        groups: List[List[TimelineBlock]] = [[blocks[0]]]
        for block in blocks[1:]:
            last_group = groups[-1]
            # Check continuity (max 2 min gap)
            gap = (block.start_time - last_group[-1].end_time).total_seconds()
            if gap <= 120:
                last_group.append(block)
            else:
                groups.append([block])
        return groups

    def _reduce_group(self, session_id: str, blocks: List[TimelineBlock]) -> EventEntry:
        """Reduce satu group of blocks jadi satu event entry."""
        apps = set()
        contexts: Set[str] = set()
        verbatim: List[str] = []
        people: Set[str] = set()
        topics: Set[str] = set()
        tools: Set[str] = set()
        all_text = []

        start = blocks[0].start_time
        end = blocks[-1].end_time
        duration = (end - start).total_seconds() / 60.0

        for block in blocks:
            for cap in block.captures:
                apps.add(cap.app_bundle)
                contexts.add(cap.window_title)
                all_text.append(block.normalized_text)

                # Extract verbatim
                focused = cap.focused_element
                if focused.get("is_editable") and focused.get("value"):
                    verbatim.append(focused["value"][:500])

                # Extract entities
                people.update(TimelineNormalizer._extract_proper_nouns(cap.visible_text))
                if cap.url:
                    topics.add(cap.url)
                tools.add(cap.app_bundle)

        # Generate summary (simplified — production uses LLM)
        summary = self._generate_summary(all_text, list(apps), duration)

        return EventEntry(
            entry_id=f"ent-{_hash(session_id + str(start))}",
            session_id=session_id,
            timestamp=start,
            duration_minutes=duration,
            app=" → ".join(sorted(apps)) if len(apps) > 1 else list(apps)[0],
            context=" / ".join(sorted(contexts))[:200],
            summary=summary,
            verbatim_snippets=verbatim[:5],
            people=list(people)[:10],
            topics=list(topics)[:10],
            tools=list(tools)[:5],
            tags=list(apps),
        )

    def _generate_summary(self, texts: List[str], apps: List[str],
                          duration: float) -> str:
        """Generate human-readable summary."""
        if self.model:
            prompt = f"Summarize this activity ({', '.join(apps)}, {duration:.0f}min):\n" + "\n".join(texts[:5])
            return self.model(prompt)

        # Simplified heuristic summary
        app_str = ", ".join(apps[:3])
        return f"Worked in {app_str} for {duration:.0f} minutes. {len(texts)} activity snapshots recorded."

    def flush(self, session: Session) -> List[EventEntry]:
        """Incremental flush untuk active session."""
        # Only reduce blocks yang belum diflush
        unflushed = [b for b in session.blocks
                     if not session.flush_end or b.end_time > session.flush_end]
        if unflushed:
            return self.reduce_session(session, is_final=False)
        return []


# ═════════════════════════════════════════════════════════════════════════════
# 5. CLASSIFIER — Auto-Route Entries ke Memory Files
# ═════════════════════════════════════════════════════════════════════════════

class MemoryFileType(Enum):
    USER = "user"
    PROJECT = "project"
    TOOL = "tool"
    TOPIC = "topic"
    PERSON = "person"
    ORG = "org"
    EVENT = "event"

class MemoryClassifier:
    """
    Classifier: route event entries ke structured memory files.
    Meniru OpenChronicle classifier yang auto-assign entries ke:
    user-profile.md, project-*.md, tool-*.md, topic-*.md, person-*.md,
    org-*.md, event-YYYY-MM-DD.md
    """

    # App → likely file type mapping
    APP_PATTERNS: Dict[str, MemoryFileType] = {
        "safari": MemoryFileType.TOPIC,
        "chrome": MemoryFileType.TOPIC,
        "firefox": MemoryFileType.TOPIC,
        "cursor": MemoryFileType.PROJECT,
        "vscode": MemoryFileType.PROJECT,
        "xcode": MemoryFileType.PROJECT,
        "terminal": MemoryFileType.TOOL,
        "iterm": MemoryFileType.TOOL,
        "slack": MemoryFileType.ORG,
        "discord": MemoryFileType.ORG,
        "teams": MemoryFileType.ORG,
        "notion": MemoryFileType.PROJECT,
        "linear": MemoryFileType.PROJECT,
        "figma": MemoryFileType.PROJECT,
        "calendar": MemoryFileType.EVENT,
        "mail": MemoryFileType.PERSON,
        "messages": MemoryFileType.PERSON,
    }

    def classify(self, entry: EventEntry) -> List[Tuple[MemoryFileType, str]]:
        """
        Classify entry dan return list of (file_type, file_name).
        Satu entry bisa masuk multiple files.
        """
        assignments: List[Tuple[MemoryFileType, str]] = []

        # Primary: based on app
        primary_type = self.APP_PATTERNS.get(entry.app.lower().split(".")[-1], MemoryFileType.EVENT)

        # Build file name
        if primary_type == MemoryFileType.EVENT:
            fname = f"event-{entry.timestamp.strftime('%Y-%m-%d')}.md"
        elif primary_type == MemoryFileType.USER:
            fname = "user-profile.md"
        elif primary_type == MemoryFileType.PROJECT:
            # Derive project name dari context
            proj_name = self._slugify(entry.context.split("/")[-1].split(".")[0][:30])
            fname = f"project-{proj_name}.md"
        elif primary_type == MemoryFileType.TOOL:
            tool_name = self._slugify(entry.app.split(".")[-1][:30])
            fname = f"tool-{tool_name}.md"
        elif primary_type == MemoryFileType.PERSON:
            # Use first person name
            person = entry.people[0] if entry.people else "unknown"
            fname = f"person-{self._slugify(person[:30])}.md"
        elif primary_type == MemoryFileType.ORG:
            org = entry.context.split("/")[-1][:30] if entry.context else "unknown"
            fname = f"org-{self._slugify(org)}.md"
        else:
            topic = entry.topics[0] if entry.topics else "general"
            fname = f"topic-{self._slugify(topic[:40])}.md"

        assignments.append((primary_type, fname))

        # Secondary: people always go to person files too
        for person in entry.people[:3]:
            assignments.append((MemoryFileType.PERSON, f"person-{self._slugify(person[:30])}.md"))

        # Tools used
        for tool in entry.tools[:2]:
            assignments.append((MemoryFileType.TOOL, f"tool-{self._slugify(tool[:30])}.md"))

        return assignments

    @staticmethod
    def _slugify(text: str) -> str:
        return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


# ═════════════════════════════════════════════════════════════════════════════
# 6. MEMORY STORE — Markdown Files + SQLite FTS5
# ═════════════════════════════════════════════════════════════════════════════

class MemoryStore:
    """
    Persistent memory store:
    • Markdown files on disk (human-readable, inspectable)
    • SQLite FTS5 untuk full-text search indexing
    • Supersede-not-delete semantics
    """

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root = (root_dir or Path.home() / ".magnatrix" / "memory").resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "memory.db"
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_index USING fts5(
                entry_id, session_id, summary, context, verbatim,
                people, topics, tools, tags, timestamp, content='',
                tokenize='porter'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                entry_id TEXT PRIMARY KEY,
                session_id TEXT,
                file_path TEXT,
                timestamp TEXT,
                summary TEXT,
                superseded_by TEXT,
                json_data TEXT
            )
        """)
        conn.commit()
        conn.close()

    def write_entry(self, entry: EventEntry, file_type: MemoryFileType,
                    file_name: str) -> Path:
        """Write entry ke Markdown file dan index in SQLite."""
        file_path = self.root / file_name

        # Check for existing entry with same context → supersede
        existing_id = self._find_existing_entry(entry.context, file_name)
        if existing_id:
            entry.superseded_by = entry.entry_id
            self._mark_superseded(existing_id, entry.entry_id)

        # Append ke Markdown file
        md_content = self._entry_to_markdown(entry)
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(md_content + "\n\n")

        # Index in SQLite
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO memory_index
            (entry_id, session_id, summary, context, verbatim, people, topics, tools, tags, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.entry_id, entry.session_id, entry.summary, entry.context,
            "\n".join(entry.verbatim_snippets), " ".join(entry.people),
            " ".join(entry.topics), " ".join(entry.tools), " ".join(entry.tags),
            entry.timestamp.isoformat(),
        ))
        conn.execute("""
            INSERT OR REPLACE INTO entries (entry_id, session_id, file_path,
                timestamp, summary, superseded_by, json_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.entry_id, entry.session_id, str(file_path),
            entry.timestamp.isoformat(), entry.summary,
            entry.superseded_by, json.dumps(entry.__dict__, default=str),
        ))
        conn.commit()
        conn.close()

        return file_path

    def _entry_to_markdown(self, entry: EventEntry) -> str:
        """Convert event entry ke Markdown format."""
        lines = [
            f"## {entry.timestamp.strftime('%H:%M')} — {entry.app}",
            "",
            f"**Context:** {entry.context}",
            f"**Duration:** {entry.duration_minutes:.0f} minutes",
            "",
            f"{entry.summary}",
            "",
        ]
        if entry.verbatim_snippets:
            lines.append("**Verbatim:**")
            for v in entry.verbatim_snippets:
                lines.append(f'> "{v[:200]}"')
            lines.append("")
        if entry.people:
            lines.append(f"**People:** {', '.join(entry.people)}")
        if entry.topics:
            lines.append(f"**Topics:** {', '.join(entry.topics)}")
        if entry.tools:
            lines.append(f"**Tools:** {', '.join(entry.tools)}")
        lines.append(f"**Entry ID:** `{entry.entry_id}`")
        if entry.superseded_by:
            lines.append(f"**Superseded by:** `{entry.superseded_by}`")
        lines.append("")
        return "\n".join(lines)

    def _find_existing_entry(self, context: str, file_name: str) -> Optional[str]:
        """Find most recent entry dengan similar context di file yang sama."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT entry_id FROM entries WHERE file_path = ? AND summary LIKE ? ORDER BY timestamp DESC LIMIT 1",
            (str(self.root / file_name), f"%{context[:50]}%")
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def _mark_superseded(self, old_id: str, new_id: str) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE entries SET superseded_by = ? WHERE entry_id = ?",
            (new_id, old_id)
        )
        conn.commit()
        conn.close()

    def read_memory(self, path: str, since: Optional[str] = None,
                    until: Optional[str] = None, tags: Optional[List[str]] = None,
                    tail_n: Optional[int] = None) -> Dict[str, Any]:
        """
        MCP-style read_memory tool:
        Read contents of ONE memory file dengan filtering.
        """
        file_path = self.root / path
        if not file_path.exists():
            return {"error": f"File not found: {path}"}

        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Parse entries dari markdown
        entries = self._parse_markdown_entries(content)

        # Apply filters
        if since:
            entries = [e for e in entries if e.get("timestamp", "") >= since]
        if until:
            entries = [e for e in entries if e.get("timestamp", "") <= until]
        if tags:
            entries = [e for e in entries if any(t in e.get("tags", []) for t in tags)]
        if tail_n:
            entries = entries[-tail_n:]

        return {
            "path": path,
            "entry_count": len(entries),
            "entries": entries,
        }

    def _parse_markdown_entries(self, content: str) -> List[Dict[str, Any]]:
        """Parse markdown content jadi structured entries."""
        entries = []
        current: Dict[str, Any] = {}
        for line in content.splitlines():
            if line.startswith("## "):
                if current:
                    entries.append(current)
                current = {"header": line[3:], "body": [], "tags": []}
            elif line.startswith("**Entry ID:**"):
                current["entry_id"] = line.split("`")[1] if "`" in line else ""
            elif line.startswith("**") and line.endswith("**"):
                pass  # skip formatting lines
            elif line.startswith("> "):
                current.setdefault("verbatim", []).append(line[2:].strip('"'))
            elif line.strip():
                current.setdefault("body", []).append(line)
        if current:
            entries.append(current)
        return entries

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Full-text search via SQLite FTS5."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT entry_id, summary, context, timestamp FROM memory_index WHERE memory_index MATCH ? LIMIT ?",
            (query, limit)
        )
        results = []
        for row in cursor.fetchall():
            results.append({
                "entry_id": row[0],
                "summary": row[1],
                "context": row[2],
                "timestamp": row[3],
            })
        conn.close()
        return results

    def list_memories(self) -> List[Dict[str, Any]]:
        """List semua memory files dengan metadata."""
        files = []
        for f in sorted(self.root.glob("*.md")):
            stat = f.stat()
            files.append({
                "path": f.name,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        return files


# ═════════════════════════════════════════════════════════════════════════════
# 7. BUFFER MANAGER — Tiered Retention
# ═════════════════════════════════════════════════════════════════════════════

class BufferManager:
    """
    Capture buffer hygiene dengan 3-tiered retention:
    1. Delete: mtime > buffer_retention_hours (default 7 days)
    2. Strip screenshot: mtime > screenshot_retention_hours (default 24h)
    3. Evict by size: total > buffer_max_mb (default 2GB)
    """

    def __init__(self, buffer_dir: Path,
                 retention_hours: float = 168.0,
                 screenshot_hours: float = 24.0,
                 max_mb: float = 2048.0) -> None:
        self.buffer_dir = buffer_dir
        self.retention = retention_hours * 3600
        self.screenshot_retention = screenshot_hours * 3600
        self.max_bytes = max_mb * 1024 * 1024

    def cleanup(self, absorbed_files: Set[str]) -> Dict[str, int]:
        """Run 3-pass cleanup. Return counts per pass."""
        if not self.buffer_dir.exists():
            return {"deleted": 0, "stripped": 0, "evicted": 0}

        now = time.time()
        files = [(f, f.stat()) for f in self.buffer_dir.glob("*.json")]
        deleted = 0
        stripped = 0
        evicted = 0

        # Pass 1: Delete old files
        for f, stat in files:
            if now - stat.st_mtime > self.retention and str(f) in absorbed_files:
                f.unlink()
                deleted += 1

        # Re-read remaining
        remaining = [(f, f.stat()) for f in self.buffer_dir.glob("*.json")]

        # Pass 2: Strip screenshots
        for f, stat in remaining:
            if now - stat.st_mtime > self.screenshot_retention:
                try:
                    data = json.loads(f.read_text())
                    if "screenshot_b64" in data:
                        del data["screenshot_b64"]
                        data["screenshot_stripped"] = True
                        f.write_text(json.dumps(data))
                        stripped += 1
                except Exception:
                    pass

        # Pass 3: Evict by size
        total_size = sum(f.stat().st_size for f in self.buffer_dir.glob("*.json"))
        if total_size > self.max_bytes:
            sorted_files = sorted(
                self.buffer_dir.glob("*.json"),
                key=lambda f: f.stat().st_mtime
            )
            for f in sorted_files:
                if total_size <= self.max_bytes:
                    break
                if str(f) in absorbed_files:
                    size = f.stat().st_size
                    f.unlink()
                    total_size -= size
                    evicted += 1

        return {"deleted": deleted, "stripped": stripped, "evicted": evicted}


# ═════════════════════════════════════════════════════════════════════════════
# 8. MCP ENDPOINT — Agent Query Interface
# ═════════════════════════════════════════════════════════════════════════════

class MCPEndpoint:
    """
    MCP endpoint untuk tool-calling agents.
    Exposes: read_memory, list_memories, search, get_recent_events.
    """

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def handle_tool_call(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP tool call."""
        if tool_name == "read_memory":
            return self.store.read_memory(
                params.get("path", ""),
                params.get("since"),
                params.get("until"),
                params.get("tags"),
                params.get("tail_n"),
            )
        elif tool_name == "list_memories":
            return {"memories": self.store.list_memories()}
        elif tool_name == "search":
            return {"results": self.store.search(params.get("query", ""), params.get("limit", 20))}
        elif tool_name == "get_recent_events":
            hours = params.get("hours", 24)
            since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
            # Search all event files
            event_files = [f.name for f in self.store.root.glob("event-*.md")]
            all_entries = []
            for ef in event_files:
                mem = self.store.read_memory(ef, since=since)
                all_entries.extend(mem.get("entries", []))
            return {
                "hours": hours,
                "entries": sorted(all_entries, key=lambda e: e.get("timestamp", ""), reverse=True)[:params.get("limit", 10)],
            }
        return {"error": f"Unknown tool: {tool_name}"}


# ═════════════════════════════════════════════════════════════════════════════
# 9. UNIFIED OPENCHRONICLE ENGINE — Entry Point
# ═════════════════════════════════════════════════════════════════════════════

class OpenChronicleEngine:
    """
    Unified OpenChronicle engine untuk MAGNATRIX.
    Entry point: capture → normalize → session → reduce → classify → store.
    """

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.dispatcher = CaptureDispatcher()
        self.timeline = TimelineNormalizer()
        self.sessions = SessionManager()
        self.reducer = SessionReducer()
        self.classifier = MemoryClassifier()
        self.store = MemoryStore(root_dir)
        self.buffer_mgr = BufferManager(
            (root_dir or Path.home() / ".magnatrix" / "memory") / "capture-buffer"
        )
        self.mcp = MCPEndpoint(self.store)
        self.capture_buffer: List[S1Capture] = []

    # ── Capture Pipeline ──────────────────────────────────────────────────

    def capture(self, event: CaptureEvent) -> Optional[S1Capture]:
        """Process single capture event."""
        s1 = self.dispatcher.dispatch(event)
        if s1:
            self.capture_buffer.append(s1)
            # Notify session manager
            self.sessions.on_event(s1)
        return s1

    def heartbeat(self) -> Optional[S1Capture]:
        """Trigger heartbeat capture."""
        s1 = self.dispatcher.heartbeat_tick()
        if s1:
            self.capture_buffer.append(s1)
        return s1

    # ── Timeline Tick ─────────────────────────────────────────────────────

    def timeline_tick(self) -> List[TimelineBlock]:
        """Run timeline normalizer, close old blocks."""
        if not self.capture_buffer:
            return []

        # Ingest captures ke timeline
        self.timeline.ingest_captures(self.capture_buffer)
        self.capture_buffer = []

        # Close blocks yang sudah lewat
        now = datetime.utcnow()
        closed = self.timeline.close_old_blocks(now)

        # Add closed blocks ke active session
        for block in closed:
            self.sessions.add_timeline_block(block)

        return closed

    # ── Session Flush ───────────────────────────────────────────────────────

    def session_tick(self) -> List[EventEntry]:
        """Check session cuts dan run reducer flush."""
        now = time.time()
        entries: List[EventEntry] = []

        # Check active session cuts
        active = self.sessions.get_active_session()
        if active:
            # Check if should flush
            if self.sessions.should_flush(now):
                flush_time = datetime.utcnow()
                new_entries = self.reducer.flush(active)
                entries.extend(new_entries)
                self.sessions.mark_flush(flush_time)

                # Classify dan store entries
                for entry in new_entries:
                    assignments = self.classifier.classify(entry)
                    for ftype, fname in assignments:
                        self.store.write_entry(entry, ftype, fname)

        return entries

    def close_session(self) -> List[EventEntry]:
        """Force close current session dan reduce final."""
        active = self.sessions.get_active_session()
        if not active:
            return []

        active.status = "closed"
        active.end_time = time.time()
        entries = self.reducer.reduce_session(active, is_final=True)

        for entry in entries:
            assignments = self.classifier.classify(entry)
            for ftype, fname in assignments:
                self.store.write_entry(entry, ftype, fname)

        return entries

    # ── Buffer Cleanup ──────────────────────────────────────────────────────

    def cleanup_buffer(self) -> Dict[str, int]:
        """Run tiered buffer retention cleanup."""
        absorbed = set()
        for sess in self.sessions.get_all_sessions():
            for block in sess.blocks:
                for cap in block.captures:
                    # Mark captures yang sudah masuk timeline
                    pass
        return self.buffer_mgr.cleanup(absorbed)

    # ── MCP Tools ─────────────────────────────────────────────────────────

    def read_memory(self, **kwargs) -> Dict[str, Any]:
        return self.mcp.handle_tool_call("read_memory", kwargs)

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        return self.mcp.handle_tool_call("search", {"query": query, "limit": limit})["results"]

    def list_memories(self) -> List[Dict[str, Any]]:
        return self.mcp.handle_tool_call("list_memories", {})["memories"]

    def get_recent_events(self, hours: int = 24) -> Dict[str, Any]:
        return self.mcp.handle_tool_call("get_recent_events", {"hours": hours})

    # ── Full Pipeline ─────────────────────────────────────────────────────

    def process_captures(self, events: List[CaptureEvent]) -> Dict[str, Any]:
        """Run full pipeline untuk batch of capture events."""
        captured = []
        for evt in events:
            s1 = self.capture(evt)
            if s1:
                captured.append(s1)

        # Timeline
        blocks = self.timeline_tick()

        # Session
        entries = self.session_tick()

        # Cleanup
        cleanup = self.cleanup_buffer()

        return {
            "captured": len(captured),
            "timeline_blocks": len(blocks),
            "entries_written": len(entries),
            "cleanup": cleanup,
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "active_session": self.sessions.get_active_session().session_id if self.sessions.get_active_session() else None,
            "total_sessions": len(self.sessions.get_all_sessions()),
            "open_timeline_blocks": len(self.timeline.blocks),
            "pending_captures": len(self.capture_buffer),
            "memory_files": len(self.store.list_memories()),
        }


def main():
    print("═══════════════════════════════════════════════════════════════")
    print("  MAGNATRIX-OS — OpenChronicle Native Memory Layer")
    print("  AMATI-PELAJARI-TIRU dari Einsia/OpenChronicle")
    print("═══════════════════════════════════════════════════════════════")
    print()

    engine = OpenChronicleEngine()

    # Simulate capture events
    print("[1] Simulating capture events...")
    events = [
        CaptureEvent(time.time(), "AXFocusChanged", "com.apple.Safari", "GitHub - Einsia/OpenChronicle",
                     {"focused_element": {"role": "link", "title": "OpenChronicle", "value": "", "is_editable": False},
                      "elements": [{"role": "heading", "title": "OpenChronicle", "value": ""},
                                   {"role": "text", "title": "", "value": "Open-source local-first memory"}]}),
        CaptureEvent(time.time() + 2, "AXValueChanged", "com.apple.Safari", "GitHub - Einsia/OpenChronicle",
                     {"focused_element": {"role": "textfield", "title": "Search", "value": "local-first agent memory", "is_editable": True, "value_length": 24},
                      "elements": []}),
        CaptureEvent(time.time() + 5, "AXFocusChanged", "com.microsoft.VSCode", "openchronicle_native.py",
                     {"focused_element": {"role": "text", "title": "openchronicle_native.py", "value": "class OpenChronicleEngine", "is_editable": True, "value_length": 25},
                      "elements": [{"role": "heading", "title": "openchronicle_native.py", "value": ""}]}),
        CaptureEvent(time.time() + 8, "AXValueChanged", "com.microsoft.VSCode", "openchronicle_native.py",
                     {"focused_element": {"role": "text", "title": "", "value": "def capture(self, event):", "is_editable": True, "value_length": 24},
                      "elements": []}),
        CaptureEvent(time.time() + 360, "AXFocusChanged", "com.apple.Safari", "Hacker News",
                     {"focused_element": {"role": "link", "title": "OpenChronicle on HN", "value": "", "is_editable": False},
                      "elements": [{"role": "text", "title": "", "value": "This isn't just open-source..."}]}),
    ]

    result = engine.process_captures(events)
    print(f"  Captured: {result['captured']}")
    print(f"  Timeline blocks: {result['timeline_blocks']}")
    print(f"  Entries written: {result['entries_written']}")
    print()

    # Session status
    print("[2] Session Status:")
    status = engine.get_status()
    print(f"  Sessions: {status['total_sessions']}")
    print(f"  Memory files: {status['memory_files']}")
    print()

    # List memories
    print("[3] Memory Files:")
    memories = engine.list_memories()
    for m in memories:
        print(f"  • {m['path']} ({m['size_bytes']} bytes)")
    print()

    # Search
    print("[4] Search 'memory':")
    results = engine.search("memory", limit=5)
    for r in results:
        print(f"  • [{r['timestamp'][:16]}] {r['summary'][:60]}...")
    print()

    # Read memory
    if memories:
        print("[5] Read memory file:")
        mem = engine.read_memory(path=memories[0]['path'], tail_n=2)
        print(f"  File: {mem['path']} ({mem['entry_count']} entries)")
        for e in mem.get("entries", [])[:2]:
            print(f"    {e.get('header', 'No header')}")
    print()

    # Cleanup
    print("[6] Buffer Cleanup:")
    cleanup = engine.cleanup_buffer()
    print(f"  Deleted: {cleanup['deleted']}, Stripped: {cleanup['stripped']}, Evicted: {cleanup['evicted']}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
