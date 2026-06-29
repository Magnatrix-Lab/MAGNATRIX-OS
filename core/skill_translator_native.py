
"""
skill_translator_native.py
MAGNATRIX-OS — Skill Translator

Inspired by SkillKit: translate skills between 40+ agent formats.
Claude Code <> Cursor <> Codex <> Copilot <> Windsurf <> Hermes <> Aider <> OpenCode

Pure Python standard library.
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum, auto


class AgentFormat(Enum):
    CLAUDE = "claude"
    CURSOR = "cursor"
    CODEX = "codex"
    COPILOT = "copilot"
    WINDSURF = "windsurf"
    HERMES = "hermes"
    AIDER = "aider"
    OPENCODE = "opencode"
    MARKDOWN = "markdown"


class SkillTranslator:
    """Translate skills between different AI agent formats."""

    # Format-specific templates
    TEMPLATES = {
        AgentFormat.CLAUDE: """# Skill: {name}

## Description
{description}

## Instructions
{content}

## Rules
- Always follow the instructions above
- Use this skill when: {tags}
""",
        AgentFormat.CURSOR: """# {name}

{description}

{content}

# Apply this skill for: {tags}
""",
        AgentFormat.CODEX: """<skill name="{name}">
<description>{description}</description>
<instructions>
{content}
</instructions>
<tags>{tags}</tags>
</skill>
""",
        AgentFormat.COPILOT: """## Skill: {name}

{description}

```
{content}
```

Tags: {tags}
""",
        AgentFormat.WINDSURF: """# Skill: {name}

{description}

## Context
{content}

## When to use
{tags}
""",
        AgentFormat.HERMES: """---
name: {name}
description: {description}
---

{content}

tags: {tags}
""",
        AgentFormat.AIDER: """# aider skill: {name}

{description}

{content}

# tags: {tags}
""",
        AgentFormat.OPENCODE: """<skill>
  <name>{name}</name>
  <description>{description}</description>
  <content><![CDATA[
{content}
  ]]></content>
  <tags>{tags}</tags>
</skill>
""",
        AgentFormat.MARKDOWN: """# {name}

{description}

{content}

---
Tags: {tags}
""",
    }

    def translate(self, content: str, from_format: AgentFormat, to_format: AgentFormat,
                  name: str = "", description: str = "", tags: str = "") -> str:
        """Translate skill content from one format to another."""
        if from_format == to_format:
            return content
        # Extract content if in a structured format
        plain_content = self._extract_content(content, from_format)
        # Apply target template
        template = self.TEMPLATES.get(to_format, self.TEMPLATES[AgentFormat.MARKDOWN])
        return template.format(
            name=name or "Untitled",
            description=description or "",
            content=plain_content,
            tags=tags,
        )

    def _extract_content(self, content: str, fmt: AgentFormat) -> str:
        """Extract plain content from structured format."""
        if fmt == AgentFormat.CODEX:
            m = re.search(r"<instructions>(.*?)</instructions>", content, re.DOTALL)
            if m:
                return m.group(1).strip()
        elif fmt == AgentFormat.OPENCODE:
            m = re.search(r"<\!\[CDATA\[(.*?)\]\]>", content, re.DOTALL)
            if m:
                return m.group(1).strip()
        elif fmt == AgentFormat.COPILOT:
            m = re.search(r"```\n(.*?)\n```", content, re.DOTALL)
            if m:
                return m.group(1).strip()
        # Default: strip headers and return
        lines = content.splitlines()
        filtered = []
        in_header = True
        for line in lines:
            if in_header and line.startswith("#"):
                continue
            if in_header and line.strip() and not line.startswith("#"):
                in_header = False
            if not in_header:
                filtered.append(line)
        return "\n".join(filtered).strip()

    def translate_all(self, content: str, from_format: AgentFormat, name: str = "",
                      description: str = "", tags: str = "") -> Dict[str, str]:
        """Translate to all supported formats."""
        return {
            fmt.value: self.translate(content, from_format, fmt, name, description, tags)
            for fmt in AgentFormat
        }

    def detect_format(self, content: str) -> Optional[AgentFormat]:
        """Detect the format of a skill file."""
        if "<skill name=" in content:
            return AgentFormat.CODEX
        if "<name>" in content and "<description>" in content:
            return AgentFormat.OPENCODE
        if "---" in content and "name:" in content:
            return AgentFormat.HERMES
        if "aider skill:" in content.lower():
            return AgentFormat.AIDER
        if "# Skill:" in content:
            return AgentFormat.CLAUDE
        if "```" in content and "## Skill:" in content:
            return AgentFormat.COPILOT
        if "# aider skill:" in content:
            return AgentFormat.AIDER
        return AgentFormat.MARKDOWN

    def to_dict(self) -> Dict:
        return {
            "supported_formats": [f.value for f in AgentFormat],
            "total_formats": len(AgentFormat),
        }


__all__ = ["SkillTranslator", "AgentFormat"]
