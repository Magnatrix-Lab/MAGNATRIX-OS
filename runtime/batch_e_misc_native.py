#!/usr/bin/env python3
"""
batch_e_misc_native.py
Educational simulation of 3 diverse systems in pure Python:
1. alda — music programming language interpreter (AST + evaluator)
2. flash-card — spaced repetition engine (SM-2 + Leitner)
3. aicoe-ci — CI/CD pipeline (build/test/deploy stages)
Zero external dependencies. ~800 lines.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import deque
import time
import math

# ============================================================================
# 1. BASE — Alda Interpreter Engine (AST + Evaluator)
# ============================================================================

class NoteName(Enum):
    C = 0; D = 2; E = 4; F = 5; G = 7; A = 9; B = 11

@dataclass
class NoteEvent:
    """A single musical note event."""
    pitch: int          # MIDI note number (0-127)
    duration: float     # in seconds
    volume: float = 0.8

class ASTNode:
    """Base class for Alda AST nodes."""
    pass

@dataclass
class NoteNode(ASTNode):
    note: str           # e.g., "c", "e", "g"
    octave: int = 4
    duration: float = 1.0
    accidental: Optional[str] = None   # "+" or "-"

@dataclass
class RestNode(ASTNode):
    duration: float = 1.0

@dataclass
class ChordNode(ASTNode):
    notes: List[NoteNode]
    duration: float = 1.0

@dataclass
class SequenceNode(ASTNode):
    children: List[ASTNode] = field(default_factory=list)

@dataclass
class RepeatNode(ASTNode):
    count: int
    body: ASTNode

class AldaParser:
    """Minimal Alda parser — tokenizes simple phrases into AST."""
    def __init__(self):
        self.note_map = {n.name.lower(): n.value for n in NoteName}
    def tokenize(self, src: str) -> List[str]:
        # split on whitespace, keep note+duration combos like "c4" or "e2"
        return src.strip().split()
    def parse(self, src: str) -> SequenceNode:
        tokens = self.tokenize(src)
        seq = SequenceNode()
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            # chord: notes separated by / like "c/e/g"
            if "/" in tok:
                parts = tok.split("/")
                notes = [self._parse_note(p) for p in parts]
                dur = notes[0].duration
                seq.children.append(ChordNode(notes, dur))
            # repeat marker: *N [ ... ]
            elif tok.startswith("*"):
                count = int(tok[1:])
                # naive: repeat applies to next token only (no bracket parsing)
                if i + 1 < len(tokens):
                    body = self._parse_note(tokens[i + 1]) if "/" not in tokens[i + 1] else self.parse(tokens[i + 1])
                    seq.children.append(RepeatNode(count, body))
                    i += 1
            else:
                seq.children.append(self._parse_note(tok))
            i += 1
        return seq
    def _parse_note(self, tok: str) -> NoteNode:
        note_part = ""
        octave = 4
        dur = 1.0
        acc = None
        idx = 0
        # extract note letter + accidental
        while idx < len(tok) and tok[idx].lower() in self.note_map:
            note_part += tok[idx].lower()
            idx += 1
        if idx < len(tok) and tok[idx] in "+-":
            acc = tok[idx]
            idx += 1
        # extract octave number
        oct_str = ""
        while idx < len(tok) and tok[idx].isdigit():
            oct_str += tok[idx]
            idx += 1
        if oct_str:
            octave = int(oct_str)
        # extract duration fraction
        if idx < len(tok) and tok[idx] == "/":
            num_str = ""
            idx += 1
            while idx < len(tok) and tok[idx].isdigit():
                num_str += tok[idx]
                idx += 1
            dur = 1.0 / int(num_str) if num_str else 0.5
        elif idx < len(tok) and tok[idx] == "*":
            mult_str = ""
            idx += 1
            while idx < len(tok) and tok[idx].isdigit():
                mult_str += tok[idx]
                idx += 1
            dur = int(mult_str) if mult_str else 2.0
        return NoteNode(note_part, octave, dur, acc)

class AldaEvaluator:
    """Evaluates AST into a list of NoteEvents with absolute timing."""
    def __init__(self, tempo: int = 120):
        self.tempo = tempo
        self.beat_sec = 60.0 / tempo
        self.note_map = {n.name.lower(): n.value for n in NoteName}
    def eval(self, node: ASTNode) -> List[NoteEvent]:
        return self._eval(node, 0.0)[0]
    def _eval(self, node: ASTNode, t: float) -> Tuple[List[NoteEvent], float]:
        events: List[NoteEvent] = []
        if isinstance(node, NoteNode):
            pitch = self._note_to_midi(node)
            dur = node.duration * self.beat_sec
            events.append(NoteEvent(pitch, dur))
            return events, t + dur
        if isinstance(node, RestNode):
            dur = node.duration * self.beat_sec
            return events, t + dur
        if isinstance(node, ChordNode):
            dur = node.duration * self.beat_sec
            for n in node.notes:
                events.append(NoteEvent(self._note_to_midi(n), dur))
            return events, t + dur
        if isinstance(node, SequenceNode):
            for child in node.children:
                child_events, t = self._eval(child, t)
                events.extend(child_events)
            return events, t
        if isinstance(node, RepeatNode):
            for _ in range(node.count):
                child_events, t = self._eval(node.body, t)
                events.extend(child_events)
            return events, t
        return events, t
    def _note_to_midi(self, n: NoteNode) -> int:
        base = self.note_map.get(n.note, 0)
        if n.accidental == "+":
            base += 1
        elif n.accidental == "-":
            base -= 1
        # MIDI octave mapping: C4 = 60
        return (n.octave + 1) * 12 + base

class ScoreBuilder:
    """Builds a score sheet from evaluated events."""
    def __init__(self):
        self.tracks: Dict[int, List[NoteEvent]] = {}
    def add_track(self, track_id: int, events: List[NoteEvent]):
        self.tracks[track_id] = events
    def summary(self) -> str:
        lines = []
        for tid, evs in self.tracks.items():
            total = sum(e.duration for e in evs)
            lines.append(f"Track {tid}: {len(evs)} events, total {total:.2f}s")
        return "\n".join(lines)


# ============================================================================
# 2. CORE — Flash Card Engine (SM-2 + Leitner)
# ============================================================================

@dataclass
class FlashCard:
    """A single flash card with SM-2 scheduling fields."""
    id: int
    front: str
    back: str
    # SM-2 fields
    interval: float = 0.0       # days
    repetition: int = 0
    ef: float = 2.5           # easiness factor
    next_due: float = 0.0     # timestamp
    # Leitner box (1=review daily, 2=2days, 3=4days, 4=7days, 5=14days)
    box: int = 1
    # history
    history: List[Tuple[float, int]] = field(default_factory=list)

class Rating(Enum):
    AGAIN = 1   # total blackout
    HARD = 3    # incorrect but familiar
    GOOD = 4    # correct with effort
    EASY = 5    # perfect

class SM2Engine:
    """SuperMemo-2 algorithm implementation."""
    def review(self, card: FlashCard, rating: Rating) -> FlashCard:
        q = rating.value
        # update easiness factor
        card.ef = card.ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        if card.ef < 1.3:
            card.ef = 1.3
        # update interval and repetition
        if q < 3:
            card.repetition = 0
            card.interval = 1.0
        else:
            if card.repetition == 0:
                card.interval = 1.0
            elif card.repetition == 1:
                card.interval = 6.0
            else:
                card.interval = card.interval * card.ef
            card.repetition += 1
        card.next_due = time.time() + card.interval * 86400
        card.history.append((time.time(), q))
        return card

class LeitnerEngine:
    """Leitner box system with scheduled promotions/demotions."""
    BOX_SCHEDULE = {1: 1, 2: 2, 3: 4, 4: 7, 5: 14}  # days per box
    def review(self, card: FlashCard, correct: bool) -> FlashCard:
        if correct:
            if card.box < 5:
                card.box += 1
        else:
            card.box = 1
        days = self.BOX_SCHEDULE.get(card.box, 1)
        card.next_due = time.time() + days * 86400
        card.history.append((time.time(), 1 if correct else 0))
        return card

class FlashCardSession:
    """Manages a review session combining SM-2 and Leitner."""
    def __init__(self, cards: List[FlashCard], mode: str = "sm2"):
        self.cards = cards
        self.mode = mode
        self.sm2 = SM2Engine()
        self.leitner = LeitnerEngine()
        self.current: Optional[FlashCard] = None
        self.stats = {"seen": 0, "correct": 0, "again": 0}
    def due_cards(self) -> List[FlashCard]:
        now = time.time()
        return [c for c in self.cards if c.next_due <= now]
    def pick_card(self) -> Optional[FlashCard]:
        due = self.due_cards()
        if due:
            self.current = due[0]
            return self.current
        return None
    def submit_rating(self, rating: Rating) -> FlashCard:
        if not self.current:
            raise ValueError("No card in play")
        self.stats["seen"] += 1
        if rating == Rating.AGAIN:
            self.stats["again"] += 1
        else:
            self.stats["correct"] += 1
        if self.mode == "sm2":
            self.sm2.review(self.current, rating)
        else:
            correct = rating.value >= 4
            self.leitner.review(self.current, correct)
        return self.current
    def quiz_loop(self):
        """Simulated quiz: auto-rates cards for demo purposes."""
        while True:
            c = self.pick_card()
            if not c:
                break
            # simulated rating: GOOD for even ids, AGAIN for odd
            r = Rating.GOOD if c.id % 2 == 0 else Rating.HARD
            self.submit_rating(r)
            print(f"Card {c.id}: rated {r.name} (next due in {c.interval:.1f} days)")


# ============================================================================
# 3. FEATURES — CI/CD Pipeline (Build/Test/Deploy)
# ============================================================================

class StageState(Enum):
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    SKIPPED = auto()

@dataclass
class Stage:
    name: str
    commands: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    state: StageState = StageState.PENDING
    logs: List[str] = field(default_factory=list)
    duration_sec: float = 0.0

@dataclass
class Pipeline:
    name: str
    stages: List[Stage] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    state: StageState = StageState.PENDING
    start_time: float = 0.0
    end_time: float = 0.0

class StageRunner:
    """Executes a single stage with simulated commands."""
    def __init__(self):
        self.cmd_handlers: Dict[str, Callable[..., Any]] = {
            "echo": self._cmd_echo,
            "make": self._cmd_make,
            "pytest": self._cmd_pytest,
            "docker": self._cmd_docker,
            "deploy": self._cmd_deploy,
        }
    def run(self, stage: Stage, pipeline: Pipeline) -> StageState:
        stage.state = StageState.RUNNING
        t0 = time.time()
        for cmd in stage.commands:
            result = self._exec(cmd, pipeline)
            stage.logs.append(f"$ {cmd}\n{result}")
            if "FAILED" in result:
                stage.state = StageState.FAILED
                stage.duration_sec = time.time() - t0
                return stage.state
        stage.state = StageState.SUCCESS
        stage.duration_sec = time.time() - t0
        return stage.state
    def _exec(self, cmd: str, pipeline: Pipeline) -> str:
        parts = cmd.split()
        handler = self.cmd_handlers.get(parts[0], self._cmd_unknown)
        return handler(parts, pipeline)
    def _cmd_echo(self, parts, pipeline) -> str:
        return " ".join(parts[1:])
    def _cmd_make(self, parts, pipeline) -> str:
        pipeline.artifacts["build"] = {"binary": "app", "size": 2048}
        return "make: build success"
    def _cmd_pytest(self, parts, pipeline) -> str:
        return "pytest: 42 passed, 0 failed"
    def _cmd_docker(self, parts, pipeline) -> str:
        pipeline.artifacts["image"] = {"tag": "app:latest", "layers": 5}
        return "docker: built app:latest"
    def _cmd_deploy(self, parts, pipeline) -> str:
        if "build" not in pipeline.artifacts or "image" not in pipeline.artifacts:
            return "FAILED: missing artifacts"
        pipeline.artifacts["deploy"] = {"host": "prod-01", "status": "ok"}
        return "deploy: deployed to prod-01"
    def _cmd_unknown(self, parts, pipeline) -> str:
        return f"unknown command: {parts[0]}"

class CIPipeline:
    """Pipeline state machine: build -> test -> deploy."""
    def __init__(self):
        self.runner = StageRunner()
        self.pipelines: List[Pipeline] = []
    def create_pipeline(self, name: str) -> Pipeline:
        p = Pipeline(name=name)
        p.stages.append(Stage("build", commands=["echo Building...", "make"], artifacts=["build"]))
        p.stages.append(Stage("test", commands=["echo Testing...", "pytest"], artifacts=["test-results"]))
        p.stages.append(Stage("deploy", commands=["echo Deploying...", "docker", "deploy"], artifacts=["deploy"]))
        self.pipelines.append(p)
        return p
    def run_pipeline(self, p: Pipeline) -> StageState:
        p.state = StageState.RUNNING
        p.start_time = time.time()
        for stage in p.stages:
            if stage.state == StageState.SKIPPED:
                continue
            result = self.runner.run(stage, p)
            if result == StageState.FAILED:
                p.state = StageState.FAILED
                p.end_time = time.time()
                return p.state
            # pass artifacts forward implicitly via pipeline.artifacts dict
        p.state = StageState.SUCCESS
        p.end_time = time.time()
        return p.state
    def webhook_notify(self, p: Pipeline, url: str = "") -> str:
        status = "✅ PASSED" if p.state == StageState.SUCCESS else "❌ FAILED"
        msg = f"Pipeline [{p.name}] {status} in {p.end_time - p.start_time:.2f}s"
        return msg


# ============================================================================
# 4. DEMOS
# ============================================================================

def demo_alda():
    print("\n=== DEMO: Alda Music Interpreter ===")
    src = "c4 e4 g4 c5/2 rest/4 e4*2"
    parser = AldaParser()
    ast = parser.parse(src)
    evalr = AldaEvaluator(tempo=120)
    events = evalr.eval(ast)
    print(f"Parsed '{src}' into {len(events)} events")
    for ev in events:
        print(f"  pitch={ev.pitch} dur={ev.duration:.3f}s")
    score = ScoreBuilder()
    score.add_track(0, events)
    print(score.summary())

def demo_flashcards():
    print("\n=== DEMO: FlashCard SM-2 + Leitner ===")
    cards = [
        FlashCard(1, "capital of France", "Paris"),
        FlashCard(2, "2+2", "4"),
        FlashCard(3, "linux init system", "systemd"),
        FlashCard(4, "HTTP 200 meaning", "OK"),
    ]
    # SM-2 demo
    sm2 = SM2Engine()
    for c in cards:
        sm2.review(c, Rating.GOOD)
        print(f"SM2 Card {c.id}: interval={c.interval:.1f}d ef={c.ef:.2f} rep={c.repetition}")
    # Leitner demo
    leitner = LeitnerEngine()
    for c in cards:
        leitner.review(c, correct=(c.id % 2 == 0))
        print(f"Leitner Card {c.id}: box={c.box} next_due={c.next_due - time.time():.0f}s")
    # Session quiz
    session = FlashCardSession(cards, mode="sm2")
    session.quiz_loop()
    print(f"Session stats: {session.stats}")

def demo_ci_pipeline():
    print("\n=== DEMO: CI/CD Pipeline ===")
    ci = CIPipeline()
    p = ci.create_pipeline("app-release")
    result = ci.run_pipeline(p)
    print(f"Pipeline result: {result.name}")
    for s in p.stages:
        print(f"  [{s.name}] {s.state.name} ({s.duration_sec:.3f}s)")
        for log in s.logs:
            print(f"    {log.strip()}")
    print(ci.webhook_notify(p))
    # Artifact tree
    print(f"Artifacts: {list(p.artifacts.keys())}")


if __name__ == "__main__":
    print("=" * 70)
    print(" Batch E Misc Native — Alda + FlashCard + CI Pipeline ")
    print("=" * 70)
    demo_alda()
    demo_flashcards()
    demo_ci_pipeline()
    print("\n" + "=" * 70)
    print(" All demos completed successfully.")
    print("=" * 70)
