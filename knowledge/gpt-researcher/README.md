# gpt-researcher Integration — MAGNATRIX Agentic OS

> **Repo**: https://github.com/assafelovic/gpt-researcher | 15.6k+ stars | Deep Research Engine

## Status: ADOPTED

---

## Integration Strategy: Embed

gpt-researcher menjadi **deep research engine** untuk GQRIS brain di MAGNATRIX. Autonomous web research dengan report generation.

## Directory

```
knowledge/gpt-researcher/
├── README.md              # This file
├── config.yaml            # Research config
├── reports/               # Generated reports storage
└── adapter.py             # MAGNATRIX adapter
```

## Adapter (adapter.py)

```python
#!/usr/bin/env python3
"""MAGNATRIX adapter untuk gpt-researcher."""

import json
import subprocess

class GPTResearcherAdapter:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
    
    def deep_research(self, topic: str, report_type: str = "research_report") -> dict:
        """Jalankan deep research dan return report."""
        result = subprocess.run(
            ["python", "-m", "gpt_researcher",
             "--query", topic,
             "--report_type", report_type],
            capture_output=True,
            text=True
        )
        return {
            "topic": topic,
            "report": result.stdout,
            "status": "success" if result.returncode == 0 else "error"
        }
    
    def quick_summary(self, topic: str) -> str:
        """Quick summary (faster, less depth)."""
        return self.deep_research(topic, report_type="summary")

# MCP Tool exposed
def tool_deep_research(params: dict) -> dict:
    adapter = GPTResearcherAdapter()
    return adapter.deep_research(params["topic"], params.get("report_type", "research_report"))
```

## Commands

```bash
# Install
cd knowledge/gpt-researcher
pip install -r requirements.txt

# Research (CLI)
python -m gpt_researcher --query "Quantum computing impact on cryptography" --report_type research_report

# Research (via adapter)
python adapter.py --topic "Solana DeFi ecosystem 2026"

# Generate PDF report
python -m gpt_researcher --query $TOPIC --output_format pdf
```

## Integration dengan Horizon

```
Horizon (news radar) ──▶ gpt-researcher (deep dive)
     ↓                        ↓
   Score > 7 ──────────────▶ Auto-trigger research
     ↓                        ↓
   Alert user ◀─────────── Report generated
```

## Notes

- Multi-agent architecture built-in.
- Supports: Azure, OpenAI, Anthropic, Gemini, DeepSeek, Perplexity, Ollama.
- License: MIT — aman embed.
