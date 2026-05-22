#!/usr/bin/env python3
"""
skill_registry.py — MAGNATRIX Markdown Skill System
Adaptasi dari konsep STOA: skills adalah markdown prompts, bukan code.
Setiap skill adalah direktori dengan SKILL.md yang berisi:
  - Objective, Steps, Output, Exit Codes
  - Frontmatter YAML dengan name, agent, description, schedule

Skill bisa di-extend tanpa restart — cukup drop SKILL.md baru ke skills/
dan registry akan auto-load pada tick berikutnya.
"""

import os
import re
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Skill:
    """Satu skill yang di-parse dari SKILL.md."""
    name: str
    agent: str
    description: str
    schedule: str
    objective: str
    steps: List[str]
    output_spec: str
    exit_codes: Dict[str, str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_path: Optional[str] = None
    last_loaded: float = 0.0


class SkillRegistry:
    """Registry yang auto-scan dan parse SKILL.md dari direktori skills/."""

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, Skill] = {}
        self._agent_index: Dict[str, List[str]] = {}
        self._last_scan = 0.0
        self._scan_interval = 60.0

    def _parse_skill_md(self, path: Path) -> Optional[Skill]:
        """Parse satu file SKILL.md jadi Skill object."""
        text = path.read_text(encoding="utf-8")

        # Extract YAML frontmatter
        frontmatter = {}
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    text = parts[2]
                except Exception:
                    pass

        # Parse sections
        sections = self._extract_sections(text)

        name = frontmatter.get("name", path.parent.name)
        agent = frontmatter.get("agent", "generic")
        description = frontmatter.get("description", "")
        schedule = frontmatter.get("schedule", "*/15 * * * *")

        objective = sections.get("Objective", "").strip()
        steps = [s.strip() for s in sections.get("Steps", "").split("\n") if s.strip() and s.strip()[0].isdigit()]
        output_spec = sections.get("Output", "").strip()

        # Parse exit codes
        exit_codes: Dict[str, str] = {}
        exit_block = sections.get("Exit Codes", "")
        for line in exit_block.split("\n"):
            match = re.match(r"-\s+(\w+):\s*(.+)", line.strip())
            if match:
                exit_codes[match.group(1)] = match.group(2)

        return Skill(
            name=name,
            agent=agent,
            description=description,
            schedule=schedule,
            objective=objective,
            steps=steps,
            output_spec=output_spec,
            exit_codes=exit_codes or {"SKILL_OK": "success", "SKILL_FAIL": "failure"},
            metadata=frontmatter,
            source_path=str(path),
            last_loaded=time.time(),
        )

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract markdown H2 sections."""
        sections: Dict[str, str] = {}
        pattern = re.compile(r"##\s+(.+)\n(.*?)(?=\n##\s+|\Z)", re.S)
        for match in pattern.finditer(text):
            sections[match.group(1).strip()] = match.group(2).strip()
        return sections

    def scan(self, force: bool = False) -> int:
        """Scan direktori skills/ dan load semua SKILL.md."""
        now = time.time()
        if not force and (now - self._last_scan) < self._scan_interval:
            return len(self.skills)

        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            return 0

        self.skills.clear()
        self._agent_index.clear()

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                skill = self._parse_skill_md(skill_md)
                if skill:
                    self.skills[skill.name] = skill
                    self._agent_index.setdefault(skill.agent, []).append(skill.name)

        self._last_scan = now
        return len(self.skills)

    def get_by_agent(self, agent: str) -> List[Skill]:
        """Ambil semua skill milik satu agent."""
        names = self._agent_index.get(agent, [])
        return [self.skills[n] for n in names if n in self.skills]

    def get(self, name: str) -> Optional[Skill]:
        """Ambil satu skill by name."""
        return self.skills.get(name)

    def list_all(self) -> List[str]:
        """List semua skill names."""
        return list(self.skills.keys())

    def to_prompt(self, skill_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Render skill jadi LLM prompt lengkap."""
        skill = self.skills.get(skill_name)
        if not skill:
            return ""
        lines = [
            f"# Skill: {skill.name}",
            f"## Agent: {skill.agent}",
            f"## Objective\n{skill.objective}",
            "## Steps",
        ]
        for step in skill.steps:
            lines.append(f"1. {step}")
        lines.append(f"## Output\n{skill.output_spec}")
        lines.append("## Exit Codes")
        for code, desc in skill.exit_codes.items():
            lines.append(f"- {code}: {desc}")
        if context:
            lines.append("## Context")
            lines.append(f"```json\n{json.dumps(context, indent=2, default=str)}\n```")
        return "\n\n".join(lines)

    def get_status(self) -> Dict[str, Any]:
        return {
            "skills_dir": str(self.skills_dir),
            "total_skills": len(self.skills),
            "last_scan": self._last_scan,
            "by_agent": {k: len(v) for k, v in self._agent_index.items()},
        }


# ------------------------------------------------------------------
# Demo
# ------------------------------------------------------------------
if __name__ == "__main__":
    import json
    import tempfile

    print("=" * 60)
    print("MAGNATRIX Skill Registry — STOA Adaptation")
    print("=" * 60)

    # Buat direktori skills temp untuk demo
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "skills"
        skills_dir.mkdir()

        # Buat sample skill: analyze-signal
        analyze_dir = skills_dir / "analyze-signal"
        analyze_dir.mkdir()
        analyze_dir.joinpath("SKILL.md").write_text("""---
name: analyze-signal
agent: analyst
description: Evaluasi sinyal trading dari scout
schedule: "*/10 * * * *"
---

# analyze-signal

## Objective
Evaluasi sinyal trading yang diterima dari scout. Berikan confidence score 0-1 dan rekomendasi tindakan.

## Steps
1. Terima payload sinyal (symbol, price, change_24h, volume_spike).
2. Cross-check dengan knowledge graph untuk historical pattern.
3. Hitung confidence score berdasarkan: trend alignment, volume confirmation, support/resistance level.
4. Jika confidence > 0.75, generate trade thesis dan kirim ke executor.
5. Jika confidence < 0.5, discard dan log alasan.

## Output
- JSON dengan fields: symbol, confidence, thesis, recommended_action, risk_level
- Kirim ke mesh target=executor jika confidence > 0.75

## Exit Codes
- SKILL_OK: Analisis selesai, output valid
- SKILL_FAIL: Data tidak valid atau error internal
""")

        # Buat sample skill: check-risk
        risk_dir = skills_dir / "check-risk"
        risk_dir.mkdir()
        risk_dir.joinpath("SKILL.md").write_text("""---
name: check-risk
agent: guardian
description: Monitor risk exposure dan drawdown
description: "*/3 * * * *"
---

# check-risk

## Objective
Monitor seluruh posisi terbuka, hitung total exposure, drawdown, dan flag anomaly.

## Steps
1. Ambil snapshot semua posisi dari trading layer.
2. Hitung total NAV, unrealized PnL, drawdown % dari peak.
3. Cek apakah ada posisi melebihi max_position_size (default 10% NAV).
4. Jika drawdown > 15% atau ada posisi > 10%, trigger HALT ke swarm.
5. Log risk metrics ke knowledge graph.

## Output
- Risk report JSON: nav, drawdown_pct, max_position_pct, anomaly_flag, halt_triggered
- Broadcast HALT ke mesh jika threshold breached

## Exit Codes
- SKILL_OK: Risk dalam batas normal
- SKILL_HALT: Risk threshold breached, HALT triggered
- SKILL_FAIL: Error mengambil data posisi
""")

        registry = SkillRegistry(str(skills_dir))
        count = registry.scan(force=True)
        print(f"\n[1] Scanned {count} skill(s)")

        print("\n[2] Skills by agent:")
        for agent, names in registry._agent_index.items():
            print(f"  • {agent}: {', '.join(names)}")

        print("\n[3] Sample prompt render (analyze-signal):")
        prompt = registry.to_prompt("analyze-signal", context={"symbol": "SOL", "price": 145.2})
        print(prompt[:500] + "...")

        print("\n[4] Registry status:")
        print(json.dumps(registry.get_status(), indent=2, default=str))

    print("\n" + "=" * 60)
    print("Skill Registry ready.")
    print("=" * 60)
