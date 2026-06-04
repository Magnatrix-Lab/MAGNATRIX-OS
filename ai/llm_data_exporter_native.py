"""Data Exporter - Export data to various formats for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import json
import csv
import io

class ExportFormat(Enum):
    JSON = auto(); CSV = auto(); MARKDOWN = auto()

@dataclass
class DataExporter:
    format: ExportFormat = ExportFormat.JSON
    
    def export(self, data: List[Dict], headers: List[str] = None) -> str:
        if self.format == ExportFormat.JSON:
            return json.dumps(data, indent=2)
        elif self.format == ExportFormat.CSV:
            output = io.StringIO()
            if data and headers:
                writer = csv.DictWriter(output, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data)
            return output.getvalue()
        elif self.format == ExportFormat.MARKDOWN:
            lines = []
            if headers:
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for row in data:
                values = [str(row.get(h, "")) for h in headers] if headers else []
                lines.append("| " + " | ".join(values) + " |")
            return "\n".join(lines)
        return ""
    
    def stats(self, data: List[Dict]) -> dict:
        return {"format": self.format.name, "records": len(data)}

def run():
    de = DataExporter(ExportFormat.MARKDOWN)
    data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    print(de.export(data, ["name", "age"]))
    print("Stats:", de.stats(data))

if __name__ == "__main__": run()
