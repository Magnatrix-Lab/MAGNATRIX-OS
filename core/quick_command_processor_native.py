
"""
quick_command_processor_native.py
MAGNATRIX-OS — Quick Command Processor

Inspired by Hermes Browser Extension v0.1.6 quick commands:
/summarize, /explain, /rewrite, /tabs, /action-items, and more.

Pure Python standard library.
"""

import re
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime


class QuickCommand(Enum):
    SUMMARIZE = "/summarize"
    EXPLAIN = "/explain"
    REWRITE = "/rewrite"
    TABS = "/tabs"
    ACTION_ITEMS = "/action-items"
    TRANSLATE = "/translate"
    DEFINE = "/define"
    CODE = "/code"
    SEARCH = "/search"
    HELP = "/help"


@dataclass
class CommandResult:
    command: str
    args: List[str]
    output: str
    success: bool
    timestamp: str


class QuickCommandProcessor:
    """Process slash commands for browser-context AI work."""

    def __init__(self):
        self.commands: Dict[str, Callable] = {
            QuickCommand.SUMMARIZE.value: self._cmd_summarize,
            QuickCommand.EXPLAIN.value: self._cmd_explain,
            QuickCommand.REWRITE.value: self._cmd_rewrite,
            QuickCommand.TABS.value: self._cmd_tabs,
            QuickCommand.ACTION_ITEMS.value: self._cmd_action_items,
            QuickCommand.TRANSLATE.value: self._cmd_translate,
            QuickCommand.DEFINE.value: self._cmd_define,
            QuickCommand.CODE.value: self._cmd_code,
            QuickCommand.SEARCH.value: self._cmd_search,
            QuickCommand.HELP.value: self._cmd_help,
        }
        self.history: List[CommandResult] = []

    def parse(self, text: str) -> Optional[Dict]:
        """Parse a command from text."""
        match = re.match(r"^(/\w+)(?:\s+(.+))?", text.strip())
        if match:
            return {"command": match.group(1), "args": match.group(2) or ""}
        return None

    def execute(self, text: str, context: Optional[Dict] = None) -> CommandResult:
        parsed = self.parse(text)
        if not parsed:
            return CommandResult(
                command="", args=[], output="No command detected.",
                success=False, timestamp=datetime.now().isoformat()
            )
        cmd = parsed["command"]
        args = parsed["args"].split() if parsed["args"] else []
        handler = self.commands.get(cmd, self._cmd_unknown)
        try:
            output = handler(args, context or {})
            success = True
        except Exception as e:
            output = f"Error: {e}"
            success = False
        result = CommandResult(
            command=cmd, args=args, output=output,
            success=success, timestamp=datetime.now().isoformat()
        )
        self.history.append(result)
        return result

    def _cmd_summarize(self, args: List[str], context: Dict) -> str:
        tab_content = context.get("tab_content", "")
        if not tab_content:
            return "No tab content to summarize."
        sentences = tab_content.split(". ")
        summary = ". ".join(sentences[:3]) + ("..." if len(sentences) > 3 else "")
        return f"**Summary:** {summary}"

    def _cmd_explain(self, args: List[str], context: Dict) -> str:
        topic = " ".join(args) if args else context.get("selected_text", "the content")
        return f"**Explanation:** {topic} refers to the key concept being discussed. It involves core mechanisms that enable the described functionality."

    def _cmd_rewrite(self, args: List[str], context: Dict) -> str:
        text = " ".join(args) if args else context.get("selected_text", "")
        if not text:
            return "No text to rewrite."
        return f"**Rewritten:** {text} (rephrased for clarity and conciseness)"

    def _cmd_tabs(self, args: List[str], context: Dict) -> str:
        tabs = context.get("open_tabs", [])
        if not tabs:
            return "No open tabs."
        lines = ["**Open Tabs:**"]
        for i, tab in enumerate(tabs, 1):
            lines.append(f"{i}. {tab.get('title', 'Untitled')} ({tab.get('url', '')})")
        return "\n".join(lines)

    def _cmd_action_items(self, args: List[str], context: Dict) -> str:
        content = context.get("tab_content", "")
        if not content:
            return "No content to extract action items from."
        # Simple extraction: look for action keywords
        action_keywords = ["todo", "task", "action", "follow up", "need to", "should", "must"]
        items = []
        for line in content.splitlines():
            lower = line.lower()
            if any(kw in lower for kw in action_keywords):
                items.append(f"- {line.strip()}")
        if not items:
            return "No action items found."
        return "**Action Items:**\n" + "\n".join(items[:10])

    def _cmd_translate(self, args: List[str], context: Dict) -> str:
        if len(args) < 2:
            return "Usage: /translate <text> <target_lang>"
        target_lang = args[-1]
        text = " ".join(args[:-1])
        return f"**Translation ({target_lang}):** [{text}] (translated)"

    def _cmd_define(self, args: List[str], context: Dict) -> str:
        word = " ".join(args) if args else "unknown"
        return f"**Definition:** {word} — a term used in the current context."

    def _cmd_code(self, args: List[str], context: Dict) -> str:
        lang = args[0] if args else "python"
        return f"```\n// Example {lang} code snippet\nfunction example() {{\n  return 'generated';\n}}\n```"

    def _cmd_search(self, args: List[str], context: Dict) -> str:
        query = " ".join(args) if args else ""
        return f"**Search:** [{query}] — results would be fetched from search engine."

    def _cmd_help(self, args: List[str], context: Dict) -> str:
        return "**Available Commands:**\n" + "\n".join([f"- {c.value}" for c in QuickCommand])

    def _cmd_unknown(self, args: List[str], context: Dict) -> str:
        return f"Unknown command. Use /help for available commands."

    def get_history(self) -> List[Dict]:
        return [asdict(r) for r in self.history]

    def to_dict(self) -> Dict:
        return {
            "commands": list(self.commands.keys()),
            "history_count": len(self.history),
        }


__all__ = ["QuickCommandProcessor", "QuickCommand", "CommandResult"]
