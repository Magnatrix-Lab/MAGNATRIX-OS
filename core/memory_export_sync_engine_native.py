
"""
memory_export_sync_engine_native.py
MAGNATRIX-OS — Memory Export Sync Engine

Inspired by Memanto memory file pipelines:
Export structured memory markdown, sync MEMORY.md into projects.

Pure Python standard library.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class MemoryExport:
    export_id: str
    format: str
    content: str
    exported_at: str
    memory_count: int
    file_path: str = ""


class MemoryExportSyncEngine:
    """Export and sync memory to external files and formats."""

    def __init__(self, export_dir: str = "./memory_exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)
        self.exports: List[MemoryExport] = []

    def export_to_markdown(self, memories: List[Dict[str, Any]], filename: str = "MEMORY.md") -> MemoryExport:
        """Export memories to structured markdown."""
        lines = ["# MEMORY.md", "", f"Generated: {datetime.now().isoformat()}", "", "---", ""]
        # Group by type
        by_type = {}
        for m in memories:
            mtype = m.get("memory_type", "unknown")
            by_type.setdefault(mtype, []).append(m)
        for mtype, items in sorted(by_type.items()):
            lines.append(f"## {mtype.title()}")
            lines.append("")
            for item in items:
                lines.append(f"- **{item.get('memory_id', 'unknown')}** ({item.get('confidence', 1.0)} confidence)")
                lines.append(f"  {item.get('content', '')}")
                if item.get('tags'):
                    lines.append(f"  Tags: {', '.join(item['tags'])}")
                lines.append("")
            lines.append("---")
            lines.append("")
        content = "\n".join(lines)
        file_path = self.export_dir / filename
        file_path.write_text(content, encoding="utf-8")
        export = MemoryExport(
            export_id=f"export_md_{int(datetime.now().timestamp())}",
            format="markdown", content=content[:1000],
            exported_at=datetime.now().isoformat(),
            memory_count=len(memories), file_path=str(file_path),
        )
        self.exports.append(export)
        return export

    def export_to_json(self, memories: List[Dict[str, Any]], filename: str = "memory.json") -> MemoryExport:
        """Export memories to JSON."""
        file_path = self.export_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(memories, f, indent=2)
        export = MemoryExport(
            export_id=f"export_json_{int(datetime.now().timestamp())}",
            format="json", content=f"{len(memories)} memories exported",
            exported_at=datetime.now().isoformat(),
            memory_count=len(memories), file_path=str(file_path),
        )
        self.exports.append(export)
        return export

    def sync_to_project(self, project_dir: str, memories: List[Dict[str, Any]]) -> str:
        """Sync MEMORY.md into a project directory."""
        project_path = Path(project_dir)
        project_path.mkdir(parents=True, exist_ok=True)
        memory_file = project_path / "MEMORY.md"
        export = self.export_to_markdown(memories, str(memory_file))
        return str(memory_file)

    def import_from_json(self, filepath: str) -> List[Dict[str, Any]]:
        """Import memories from a JSON file."""
        path = Path(filepath)
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def import_from_conversation(self, conversation: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Extract memories from a conversation log."""
        memories = []
        for msg in conversation:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user" and len(content) > 10:
                # Extract what seems like a fact or instruction
                if any(content.lower().startswith(p) for p in ["i prefer", "i want", "use ", "always ", "never "]):
                    memories.append({
                        "memory_id": f"conv_{len(memories)}",
                        "content": content,
                        "memory_type": "preference" if "prefer" in content.lower() else "instruction",
                        "confidence": 0.8,
                        "provenance": "conversation",
                    })
                elif "?" not in content and len(content) < 200:
                    memories.append({
                        "memory_id": f"conv_{len(memories)}",
                        "content": content,
                        "memory_type": "fact",
                        "confidence": 0.7,
                        "provenance": "conversation",
                    })
        return memories

    def get_export_history(self) -> List[Dict[str, Any]]:
        return [asdict(e) for e in self.exports]

    def get_stats(self) -> Dict[str, Any]:
        format_counts = {}
        for e in self.exports:
            format_counts[e.format] = format_counts.get(e.format, 0) + 1
        return {
            "total_exports": len(self.exports),
            "format_breakdown": format_counts,
            "total_memories_exported": sum(e.memory_count for e in self.exports),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MemoryExportSyncEngine", "MemoryExport"]
