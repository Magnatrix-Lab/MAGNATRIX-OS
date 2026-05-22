#!/usr/bin/env python3
"""
external_skill_importer.py — MAGNATRIX Curated Skill Importer
Import dan adaptasi skill dari repo eksternal seperti:
  - ComposioHQ/awesome-codex-skills (Codex CLI skills)
  - stoaaadev/stoa (STOA skills)
  - Lainnya di masa depan

Setiap skill di-parse, difilter berdasarkan relevansi agent MAGNATRIX,
dan di-convert ke MAGNATRIX SKILL.md format.
"""

import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Any


class ExternalSkillImporter:
    """Importer untuk curated skills dari repo eksternal."""

    # Mapping skill ke agent MAGNATRIX
    AGENT_MAP = {
        "ops": ["gh-address-comments", "gh-fix-ci", "codebase-migrate", "deploy-pipeline",
                "datadog-logs", "issue-triage", "repo-health", "dependency-audit", "ci-monitor"],
        "writer": ["changelog-generator", "content-research-writer", "meeting-notes-and-actions",
                   "daily-digest", "write-newsletter", "tweet-compose"],
        "analyst": ["competitive-ads-extractor", "analyze-signal", "trend-analysis",
                    "market-structure", "forecast-model"],
        "researcher": ["lead-research-assistant", "arxiv-scan", "paper-summarize",
                         "competitor-watch", "protocol-deep-dive", "security-audit"],
        "architect": ["mcp-builder", "webapp-testing", "code-mutate", "capability-rank",
                      "constitution-evolve", "emergent-predict"],
        "scout": ["scan-tokens", "web-monitor", "repo-hunt", "news-scrape", "social-listen"],
        "executor": ["execute-trade", "dca-execute", "deploy-node", "api-call"],
        "guardian": ["check-risk", "drawdown-monitor", "anomaly-flag", "veto-trigger",
                     "self-repair", "constitution-check"],
    }

    # Skill sources
    SOURCES = {
        "codex-skills": {
            "repo": "ComposioHQ/awesome-codex-skills",
            "url_pattern": "https://raw.githubusercontent.com/{repo}/master/{skill}/SKILL.md",
            "skills": [
                "agent-deep-links", "brand-guidelines", "canvas-design", "changelog-generator",
                "codebase-migrate", "competitive-ads-extractor", "composio-skills", "connect",
                "connect-apps", "content-research-writer", "create-plan", "datadog-logs",
                "deploy-pipeline", "developer-growth-analysis", "domain-name-brainstormer",
                "email-draft-polish", "file-organizer", "gh-address-comments", "gh-fix-ci",
                "helium-mcp", "image-enhancer", "internal-comms", "invoice-organizer",
                "issue-triage", "langsmith-fetch", "lead-research-assistant", "linear",
                "mcp-builder", "meeting-insights-analyzer", "meeting-notes-and-actions",
                "notion-knowledge-capture", "notion-meeting-intelligence",
                "notion-research-documentation", "notion-spec-to-implementation",
                "support-ticket-triage", "spreadsheet-formula-helper", "tailored-resume-generator",
                "video-downloader", "webapp-testing",
            ],
        },
    }

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.imported = 0
        self.skipped = 0

    def _download_skill(self, source: str, skill_name: str) -> Optional[str]:
        """Download SKILL.md dari repo eksternal."""
        cfg = self.SOURCES[source]
        url = cfg["url_pattern"].format(repo=cfg["repo"], skill=skill_name)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MAGNATRIX-Skill-Importer/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8")
        except Exception:
            return None

    def _detect_agent(self, skill_name: str) -> str:
        """Deteksi agent yang paling cocok untuk skill."""
        for agent, skills in self.AGENT_MAP.items():
            if skill_name in skills:
                return agent
        # Heuristic: keyword matching
        keywords = {
            "ops": ["deploy", "ci", "pipeline", "log", "monitor", "health", "audit", "triage", "fix"],
            "writer": ["content", "write", "draft", "changelog", "meeting", "notes", "email"],
            "analyst": ["analyze", "competitive", "forecast", "trend", "market", "signal"],
            "researcher": ["research", "lead", "arxiv", "paper", "protocol", "security"],
            "architect": ["mcp", "test", "mutate", "evolve", "predict", "capability"],
            "scout": ["scan", "hunt", "scrape", "listen", "monitor"],
            "executor": ["execute", "trade", "deploy", "call"],
            "guardian": ["risk", "check", "guard", "anomaly", "veto"],
        }
        for agent, kws in keywords.items():
            if any(kw in skill_name.lower() for kw in kws):
                return agent
        return "generic"

    def _convert_to_magnatrix_format(self, skill_name: str, raw_md: str) -> str:
        """Convert raw Codex SKILL.md ke MAGNATRIX format."""
        agent = self._detect_agent(skill_name)

        # Extract sections dari markdown
        sections = self._extract_sections(raw_md)
        objective = sections.get("Objective", sections.get("Context", "")).strip()
        steps = sections.get("Steps", "").strip()
        output = sections.get("Output", "").strip()
        exit_codes = sections.get("Exit Codes", "").strip()

        # Build MAGNATRIX format
        lines = [
            "---",
            f'name: {skill_name}',
            f'agent: {agent}',
            f'description: {objective[:80] if objective else skill_name.replace("-", " ")}',
            'schedule: "*/15 * * * *"',
            "---",
            "",
            f"# {skill_name}",
            "",
            "## Objective",
            objective if objective else f"Execute {skill_name} workflow.",
            "",
            "## Steps",
            steps if steps else "1. Analyze context.\n2. Execute task.\n3. Validate output.\n4. Report result.",
            "",
            "## Output",
            output if output else f"Result dari {skill_name} execution.",
            "",
            "## Exit Codes",
            exit_codes if exit_codes else "- SKILL_OK: Success\n- SKILL_FAIL: Error",
        ]
        return "\n".join(lines)

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract markdown H2 sections."""
        sections: Dict[str, str] = {}
        pattern = re.compile(r"##\s+(.+)\n(.*?)(?=\n##\s+|\Z)", re.S)
        for match in pattern.finditer(text):
            sections[match.group(1).strip()] = match.group(2).strip()
        return sections

    def import_skill(self, source: str, skill_name: str, force: bool = False) -> Optional[Path]:
        """Import satu skill dari repo eksternal."""
        target_dir = self.skills_dir / skill_name
        target_file = target_dir / "SKILL.md"

        if target_file.exists() and not force:
            self.skipped += 1
            return None

        raw = self._download_skill(source, skill_name)
        if not raw:
            return None

        target_dir.mkdir(parents=True, exist_ok=True)
        converted = self._convert_to_magnatrix_format(skill_name, raw)
        target_file.write_text(converted, encoding="utf-8")
        self.imported += 1
        return target_file

    def import_all(self, source: str, force: bool = False) -> Dict[str, Any]:
        """Import semua skills dari satu source."""
        self.imported = 0
        self.skipped = 0
        results = {}

        for skill in self.SOURCES[source]["skills"]:
            path = self.import_skill(source, skill, force)
            results[skill] = {
                "imported": path is not None,
                "path": str(path) if path else None,
                "agent": self._detect_agent(skill),
            }

        return {
            "source": source,
            "total": len(self.SOURCES[source]["skills"]),
            "imported": self.imported,
            "skipped": self.skipped,
            "results": results,
        }

    def list_available(self, source: str) -> List[str]:
        """List skills yang tersedia dari source."""
        return list(self.SOURCES[source]["skills"])


# ===================================================================
# Demo
# ===================================================================
if __name__ == "__main__":
    import json

    print("=" * 60)
    print("MAGNATRIX External Skill Importer")
    print("=" * 60)

    importer = ExternalSkillImporter("/mnt/agents/MAGNATRIX-OS/skills")

    print("\n[1] Available sources:")
    for name, cfg in importer.SOURCES.items():
        print(f"  • {name}: {len(cfg['skills'])} skills from {cfg['repo']}")

    print("\n[2] Sample skill detection:")
    samples = ["gh-fix-ci", "changelog-generator", "competitive-ads-extractor", "mcp-builder"]
    for s in samples:
        print(f"  • {s:30s} → agent: {importer._detect_agent(s)}")

    print("\n[3] Try importing one skill (demo):")
    result = importer.import_skill("codex-skills", "changelog-generator")
    if result:
        print(f"  ✅ Imported: {result}")
    else:
        print(f"  ⚠️  Skill not found or already exists")

    print(f"\n[4] Import summary: {importer.imported} imported, {importer.skipped} skipped")

    print("\n" + "=" * 60)
    print("External Skill Importer ready.")
    print("=" * 60)
