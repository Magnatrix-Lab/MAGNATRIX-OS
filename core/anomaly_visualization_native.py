#!/usr/bin/env python3
"""
Anomaly Visualization Engine — MAGNATRIX-OS ASCII/SVG Charts
=============================================================
Generate ASCII and SVG charts from time-series anomaly data.
Pure stdlib: textwrap, string templates for SVG. No matplotlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass
class DataPoint:
    """A single time-series data point."""
    timestamp: float
    value: float
    label: str = ""
    is_anomaly: bool = False


@dataclass
class ChartSeries:
    """A series of data points for charting."""
    name: str
    points: List[DataPoint] = field(default_factory=list)
    color: str = "#4CAF50"


class ASCIIChartRenderer:
    """
    Render time-series data as ASCII art charts.
    
    Supports: line charts, bar charts, heat maps.
    """

    def __init__(self, width: int = 80, height: int = 20):
        self.width = width
        self.height = height

    def line_chart(self, series: ChartSeries) -> str:
        """Render a line chart as ASCII art."""
        if not series.points:
            return "No data"

        values = [p.value for p in series.points]
        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val if max_val != min_val else 1

        # Build grid
        grid = [[" " for _ in range(self.width)] for _ in range(self.height)]
        
        # Plot points
        for i, point in enumerate(series.points):
            if len(series.points) > 1:
                x = int(i * (self.width - 1) / (len(series.points) - 1))
            else:
                x = self.width // 2
            y = self.height - 1 - int((point.value - min_val) / range_val * (self.height - 1))
            y = max(0, min(self.height - 1, y))
            
            char = "X" if point.is_anomaly else "*"
            grid[y][x] = char

        # Connect points with lines
        for i in range(len(series.points) - 1):
            x1 = int(i * (self.width - 1) / (len(series.points) - 1))
            x2 = int((i + 1) * (self.width - 1) / (len(series.points) - 1))
            y1 = self.height - 1 - int((values[i] - min_val) / range_val * (self.height - 1))
            y2 = self.height - 1 - int((values[i + 1] - min_val) / range_val * (self.height - 1))
            y1 = max(0, min(self.height - 1, y1))
            y2 = max(0, min(self.height - 1, y2))
            
            # Draw line between points
            if x1 != x2:
                slope = (y2 - y1) / (x2 - x1)
                for x in range(x1, x2 + 1):
                    y = int(y1 + slope * (x - x1))
                    y = max(0, min(self.height - 1, y))
                    if grid[y][x] == " ":
                        grid[y][x] = "-"

        # Add axes
        lines = []
        lines.append(f"  {max_val:.2f} +" + "-" * self.width)
        for row in grid:
            lines.append("       |" + "".join(row))
        lines.append(f"  {min_val:.2f} +" + "-" * self.width)
        lines.append("       " + "^" * self.width)
        lines.append(f"  {series.name} (min={min_val:.2f}, max={max_val:.2f})")
        
        return "\n".join(lines)

    def bar_chart(self, series: ChartSeries) -> str:
        """Render a bar chart as ASCII art."""
        if not series.points:
            return "No data"

        values = [p.value for p in series.points]
        max_val = max(values)
        max_val = max_val if max_val != 0 else 1
        labels = [p.label[:8] for p in series.points]
        max_label = max(len(l) for l in labels) if labels else 8

        lines = []
        lines.append(f"  {series.name}")
        lines.append("")
        
        for i, (point, label) in enumerate(zip(series.points, labels)):
            bar_len = int((point.value / max_val) * (self.width - max_label - 10))
            bar_char = "#" if point.is_anomaly else "="
            bar = bar_char * bar_len
            marker = " [!]" if point.is_anomaly else ""
            lines.append(f"  {label:>{max_label}s} | {bar:<{self.width}} {point.value:.2f}{marker}")
        
        return "\n".join(lines)

    def heatmap(self, matrix: List[List[float]], labels: Optional[List[str]] = None) -> str:
        """Render a heatmap as ASCII art."""
        if not matrix or not matrix[0]:
            return "No data"

        flat = [v for row in matrix for v in row]
        min_val = min(flat)
        max_val = max(flat)
        range_val = max_val - min_val if max_val != min_val else 1

        chars = " .:-=+*#%@"
        lines = []
        for row in matrix:
            line = ""
            for val in row:
                idx = int((val - min_val) / range_val * (len(chars) - 1))
                idx = max(0, min(len(chars) - 1, idx))
                line += chars[idx]
            lines.append(f"  {line}")
        
        lines.append(f"  scale: {min_val:.2f} (.) to {max_val:.2f} (@)")
        return "\n".join(lines)


class SVGChartRenderer:
    """
    Render charts as SVG using string templates.
    No external dependencies.
    """

    SVG_HEADER = '''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#1a1a2e"/>
'''
    SVG_FOOTER = '</svg>'

    def __init__(self, width: int = 800, height: int = 400):
        self.width = width
        self.height = height

    def line_chart(self, series: ChartSeries) -> str:
        """Render a line chart as SVG."""
        if not series.points:
            return self._empty_svg("No data")

        values = [p.value for p in series.points]
        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val if max_val != min_val else 1

        margin = 50
        chart_w = self.width - 2 * margin
        chart_h = self.height - 2 * margin

        svg = [self.SVG_HEADER.format(width=self.width, height=self.height)]
        
        # Grid lines
        for i in range(5):
            y = margin + i * chart_h // 4
            svg.append(f'  <line x1="{margin}" y1="{y}" x2="{self.width - margin}" y2="{y}" stroke="#333" stroke-width="1"/>')

        # Build path
        points_svg = []
        for i, point in enumerate(series.points):
            x = margin + (i * chart_w // max(1, len(series.points) - 1))
            y = margin + chart_h - int((point.value - min_val) / range_val * chart_h)
            points_svg.append(f"{x},{y}")
            
            # Anomaly markers
            if point.is_anomaly:
                svg.append(f'  <circle cx="{x}" cy="{y}" r="6" fill="#ff4444" opacity="0.8"/>')

        path_data = "M" + " L".join(points_svg)
        svg.append(f'  <polyline points="{path_data}" fill="none" stroke="{series.color}" stroke-width="2"/>')
        
        # Axis labels
        svg.append(f'  <text x="{margin - 10}" y="{margin}" fill="#888" font-size="12" text-anchor="end">{max_val:.2f}</text>')
        svg.append(f'  <text x="{margin - 10}" y="{self.height - margin}" fill="#888" font-size="12" text-anchor="end">{min_val:.2f}</text>')
        svg.append(f'  <text x="{self.width // 2}" y="{self.height - 10}" fill="#888" font-size="14" text-anchor="middle">{series.name}</text>')

        svg.append(self.SVG_FOOTER)
        return "\n".join(svg)

    def bar_chart(self, series: ChartSeries) -> str:
        """Render a bar chart as SVG."""
        if not series.points:
            return self._empty_svg("No data")

        values = [p.value for p in series.points]
        max_val = max(values)
        max_val = max_val if max_val != 0 else 1

        margin = 50
        chart_w = self.width - 2 * margin
        chart_h = self.height - 2 * margin
        bar_w = chart_w // max(1, len(series.points)) - 5

        svg = [self.SVG_HEADER.format(width=self.width, height=self.height)]

        for i, point in enumerate(series.points):
            x = margin + i * (chart_w // max(1, len(series.points)))
            bar_h = int((point.value / max_val) * chart_h)
            y = margin + chart_h - bar_h
            color = "#ff4444" if point.is_anomaly else series.color
            svg.append(f'  <rect x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" fill="{color}" opacity="0.8"/>')

        svg.append(f'  <text x="{self.width // 2}" y="{self.height - 10}" fill="#888" font-size="14" text-anchor="middle">{series.name}</text>')
        svg.append(self.SVG_FOOTER)
        return "\n".join(svg)

    def multi_series_chart(self, series_list: List[ChartSeries]) -> str:
        """Render multiple series on one chart."""
        if not series_list or not any(s.points for s in series_list):
            return self._empty_svg("No data")

        all_values = [p.value for s in series_list for p in s.points]
        min_val = min(all_values)
        max_val = max(all_values)
        range_val = max_val - min_val if max_val != min_val else 1

        margin = 50
        chart_w = self.width - 2 * margin
        chart_h = self.height - 2 * margin

        svg = [self.SVG_HEADER.format(width=self.width, height=self.height)]

        # Grid lines
        for i in range(5):
            y = margin + i * chart_h // 4
            svg.append(f'  <line x1="{margin}" y1="{y}" x2="{self.width - margin}" y2="{y}" stroke="#333" stroke-width="1"/>')

        for series in series_list:
            if not series.points:
                continue
            points_svg = []
            for i, point in enumerate(series.points):
                x = margin + (i * chart_w // max(1, len(series.points) - 1))
                y = margin + chart_h - int((point.value - min_val) / range_val * chart_h)
                points_svg.append(f"{x},{y}")
                if point.is_anomaly:
                    svg.append(f'  <circle cx="{x}" cy="{y}" r="4" fill="#ff4444" opacity="0.8"/>')
            
            path_data = "M" + " L".join(points_svg)
            svg.append(f'  <polyline points="{path_data}" fill="none" stroke="{series.color}" stroke-width="2"/>')

        svg.append(f'  <text x="{self.width // 2}" y="{self.height - 10}" fill="#888" font-size="14" text-anchor="middle">{series_list[0].name if series_list else ""}</text>')
        svg.append(self.SVG_FOOTER)
        return "\n".join(svg)

    def _empty_svg(self, message: str) -> str:
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}">
  <rect width="100%" height="100%" fill="#1a1a2e"/>
  <text x="{self.width//2}" y="{self.height//2}" fill="#888" font-size="18" text-anchor="middle">{message}</text>
</svg>'''


class AnomalyVizEngine:
    """
    Top-level anomaly visualization engine for MAGNATRIX-OS.
    
    Generates ASCII and SVG charts from time-series anomaly data.
    """

    CAPABILITIES = ["visualization", "charting", "ascii_art", "svg"]

    def __init__(self, repo_root: str = "."):
        self.repo_root = repo_root
        self._ascii = ASCIIChartRenderer(width=80, height=20)
        self._svg = SVGChartRenderer(width=800, height=400)
        self._lock = threading.Lock()
        self._stats = {"charts_rendered": 0, "ascii": 0, "svg": 0}

    def render_ascii_line(self, data: List[Tuple[float, float]],
                          name: str = "Series") -> str:
        """Render ASCII line chart."""
        series = ChartSeries(name=name, points=[
            DataPoint(timestamp=t, value=v) for t, v in data
        ])
        result = self._ascii.line_chart(series)
        with self._lock:
            self._stats["charts_rendered"] += 1
            self._stats["ascii"] += 1
        return result

    def render_ascii_bar(self, data: List[Tuple[str, float]],
                         name: str = "Series") -> str:
        """Render ASCII bar chart."""
        series = ChartSeries(name=name, points=[
            DataPoint(timestamp=i, value=v, label=l) for i, (l, v) in enumerate(data)
        ])
        result = self._ascii.bar_chart(series)
        with self._lock:
            self._stats["charts_rendered"] += 1
            self._stats["ascii"] += 1
        return result

    def render_svg_line(self, data: List[Tuple[float, float]],
                        name: str = "Series", color: str = "#4CAF50") -> str:
        """Render SVG line chart."""
        series = ChartSeries(name=name, color=color, points=[
            DataPoint(timestamp=t, value=v) for t, v in data
        ])
        result = self._svg.line_chart(series)
        with self._lock:
            self._stats["charts_rendered"] += 1
            self._stats["svg"] += 1
        return result

    def render_svg_bar(self, data: List[Tuple[str, float]],
                       name: str = "Series", color: str = "#4CAF50") -> str:
        """Render SVG bar chart."""
        series = ChartSeries(name=name, color=color, points=[
            DataPoint(timestamp=i, value=v, label=l) for i, (l, v) in enumerate(data)
        ])
        result = self._svg.bar_chart(series)
        with self._lock:
            self._stats["charts_rendered"] += 1
            self._stats["svg"] += 1
        return result

    def render_svg_multi(self, data_list: List[Dict[str, Any]]) -> str:
        """Render SVG multi-series chart."""
        series_list = []
        for item in data_list:
            series = ChartSeries(
                name=item.get("name", "Series"),
                color=item.get("color", "#4CAF50"),
                points=[
                    DataPoint(timestamp=t, value=v) for t, v in item.get("data", [])
                ]
            )
            series_list.append(series)
        result = self._svg.multi_series_chart(series_list)
        with self._lock:
            self._stats["charts_rendered"] += 1
            self._stats["svg"] += 1
        return result

    def render_ascii_heatmap(self, matrix: List[List[float]],
                             labels: Optional[List[str]] = None) -> str:
        """Render ASCII heatmap."""
        result = self._ascii.heatmap(matrix, labels)
        with self._lock:
            self._stats["charts_rendered"] += 1
            self._stats["ascii"] += 1
        return result

    def mark_anomalies(self, data: List[Tuple[float, float]],
                       threshold_std: float = 2.0) -> List[Tuple[float, float, bool]]:
        """Mark anomalies in data based on standard deviation."""
        if len(data) < 2:
            return [(t, v, False) for t, v in data]

        values = [v for _, v in data]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance) if variance > 0 else 1

        return [(t, v, abs(v - mean) > threshold_std * std) for t, v in data]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._stats)

    def handle_message(self, message: Dict[str, Any]) -> Any:
        action = message.get("action", "")
        fmt = message.get("format", "ascii")
        if action == "line" and fmt == "ascii":
            return self.render_ascii_line(message.get("data", []), message.get("name", "Series"))
        elif action == "bar" and fmt == "ascii":
            return self.render_ascii_bar(message.get("data", []), message.get("name", "Series"))
        elif action == "line" and fmt == "svg":
            return self.render_svg_line(message.get("data", []), message.get("name", "Series"), message.get("color", "#4CAF50"))
        elif action == "bar" and fmt == "svg":
            return self.render_svg_bar(message.get("data", []), message.get("name", "Series"), message.get("color", "#4CAF50"))
        elif action == "multi" and fmt == "svg":
            return self.render_svg_multi(message.get("data", []))
        elif action == "heatmap":
            return self.render_ascii_heatmap(message.get("matrix", []))
        elif action == "anomalies":
            return self.mark_anomalies(message.get("data", []), message.get("threshold", 2.0))
        elif action == "stats":
            return self.get_stats()
        return None

    def on_event(self, event) -> None:
        pass
