"""
graph_visualizer_native.py
MAGNATRIX-OS — Graph Visualizer

Generate interactive HTML knowledge graph visualization. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any


class GraphVisualizer:
    """Generate interactive HTML knowledge graph visualization."""

    def __init__(self, output_dir: str = "./graph_viz"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def to_html(self, graph_data: Dict[str, Any], title: str = "Knowledge Graph") -> str:
        """Generate interactive HTML from graph data."""
        nodes = graph_data.get("nodes", {})
        edges = graph_data.get("edges", {})

        nodes_json = json.dumps([{"id": k, "label": v.get("label", k), "type": v.get("entity_type", "unknown")} for k, v in nodes.items()])
        edges_json = json.dumps([{"source": e["source"], "target": e["target"], "label": e["label"]} for e in edges.values()])

        html = '<!DOCTYPE html>\n<html>\n<head>\n'
        html += '    <title>' + title + '</title>\n'
        html += '    <style>\n'
        html += '        body { margin: 0; font-family: sans-serif; background: #1a1a2e; }\n'
        html += '        #graph { width: 100vw; height: 100vh; }\n'
        html += '        .node { fill: #e94560; stroke: #fff; stroke-width: 2px; }\n'
        html += '        .edge { stroke: #4a4a6a; stroke-width: 1.5px; }\n'
        html += '        .label { fill: #fff; font-size: 12px; text-anchor: middle; }\n'
        html += '    </style>\n'
        html += '</head>\n<body>\n'
        html += '    <svg id="graph"></svg>\n'
        html += '    <script>\n'
        html += '        const nodes = ' + nodes_json + ';\n'
        html += '        const edges = ' + edges_json + ';\n'
        html += '        \n'
        html += '        const svg = document.getElementById("graph");\n'
        html += '        const width = window.innerWidth;\n'
        html += '        const height = window.innerHeight;\n'
        html += '        svg.setAttribute("width", width);\n'
        html += '        svg.setAttribute("height", height);\n'
        html += '        \n'
        html += '        const nodePositions = {};\n'
        html += '        const centerX = width / 2;\n'
        html += '        const centerY = height / 2;\n'
        html += '        const radius = Math.min(width, height) * 0.35;\n'
        html += '        \n'
        html += '        nodes.forEach((n, i) => {\n'
        html += '            const angle = (2 * Math.PI * i) / nodes.length;\n'
        html += '            nodePositions[n.id] = {\n'
        html += '                x: centerX + radius * Math.cos(angle),\n'
        html += '                y: centerY + radius * Math.sin(angle)\n'
        html += '            };\n'
        html += '        });\n'
        html += '        \n'
        html += '        edges.forEach(e => {\n'
        html += '            const s = nodePositions[e.source];\n'
        html += '            const t = nodePositions[e.target];\n'
        html += '            if (s && t) {\n'
        html += '                const line = document.createElementNS("http://www.w3.org/2000/svg", "line");\n'
        html += '                line.setAttribute("x1", s.x);\n'
        html += '                line.setAttribute("y1", s.y);\n'
        html += '                line.setAttribute("x2", t.x);\n'
        html += '                line.setAttribute("y2", t.y);\n'
        html += '                line.setAttribute("class", "edge");\n'
        html += '                svg.appendChild(line);\n'
        html += '            }\n'
        html += '        });\n'
        html += '        \n'
        html += '        nodes.forEach(n => {\n'
        html += '            const pos = nodePositions[n.id];\n'
        html += '            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");\n'
        html += '            circle.setAttribute("cx", pos.x);\n'
        html += '            circle.setAttribute("cy", pos.y);\n'
        html += '            circle.setAttribute("r", 20);\n'
        html += '            circle.setAttribute("class", "node");\n'
        html += '            svg.appendChild(circle);\n'
        html += '            \n'
        html += '            const text = document.createElementNS("http://www.w3.org/2000/svg", "text");\n'
        html += '            text.setAttribute("x", pos.x);\n'
        html += '            text.setAttribute("y", pos.y + 35);\n'
        html += '            text.setAttribute("class", "label");\n'
        html += '            text.textContent = n.label;\n'
        html += '            svg.appendChild(text);\n'
        html += '        });\n'
        html += '    </script>\n'
        html += '</body>\n</html>'
        return html

    def save_html(self, graph_data: Dict[str, Any], filename: str = "knowledge_graph.html", title: str = "Knowledge Graph") -> str:
        """Save graph visualization to HTML file."""
        html = self.to_html(graph_data, title)
        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return str(output_path)

    def to_json(self, graph_data: Dict[str, Any]) -> str:
        """Export graph as JSON for external tools."""
        return json.dumps(graph_data, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        return {"output_dir": str(self.output_dir)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["GraphVisualizer"]