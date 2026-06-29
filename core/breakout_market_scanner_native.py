"""Breakout Market Scanner - Market-wide scanner and scheduler."""
from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class ScanSession:
    session_id: str
    start_time: float
    end_time: float = 0.0
    stocks_scanned: int = 0
    breakouts_found: int = 0
    status: str = "running"  # running, completed, failed

    def to_dict(self) -> Dict:
        return {"session_id": self.session_id, "start_time": self.start_time,
                "end_time": self.end_time, "stocks_scanned": self.stocks_scanned,
                "breakouts_found": self.breakouts_found, "status": self.status}

class BreakoutMarketScanner:
    """Market-wide scanner: schedule scans, track sessions, aggregate results."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "breakout_scanner"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: List[ScanSession] = []
        self.schedule: List[Dict] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for s in data.get("sessions",[]): self.sessions.append(ScanSession(**s))
                self.schedule = data.get("schedule", [])
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"sessions": [s.to_dict() for s in self.sessions[-100:]],
                        "schedule": self.schedule}, indent=2))

    def start_session(self, session_id: str = "") -> ScanSession:
        if not session_id: session_id = "scan_" + str(int(time.time()))
        session = ScanSession(session_id=session_id, start_time=time.time())
        self.sessions.append(session)
        self._save_state()
        return session

    def end_session(self, session_id: str, stocks_scanned: int, breakouts_found: int) -> ScanSession:
        for s in self.sessions:
            if s.session_id == session_id:
                s.end_time = time.time()
                s.stocks_scanned = stocks_scanned
                s.breakouts_found = breakouts_found
                s.status = "completed"
                self._save_state()
                return s
        raise ValueError("Session not found")

    def add_schedule(self, interval_minutes: int, symbols: List[str]) -> None:
        self.schedule.append({"interval_minutes": interval_minutes, "symbols": symbols,
                              "next_run": time.time() + interval_minutes * 60})
        self._save_state()

    def get_due_schedules(self) -> List[Dict]:
        now = time.time()
        due = [s for s in self.schedule if s.get("next_run",0) <= now]
        for s in due: s["next_run"] = now + s["interval_minutes"] * 60
        self._save_state()
        return due

    def get_stats(self) -> Dict:
        total_scanned = sum(s.stocks_scanned for s in self.sessions)
        total_breakouts = sum(s.breakouts_found for s in self.sessions)
        return {"sessions_total": len(self.sessions), "total_scanned": total_scanned,
                "total_breakouts": total_breakouts, "schedules": len(self.schedule)}

    def to_dict(self) -> Dict:
        return {"sessions": [s.to_dict() for s in self.sessions[-20:]],
                "schedule": self.schedule, "stats": self.get_stats()}

__all__ = ["BreakoutMarketScanner", "ScanSession"]
