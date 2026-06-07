#!/usr/bin/env python3
"""
Dashboard Frontend Engine for MAGNATRIX-OS
Generates, customizes, and manages the web dashboard.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class DashboardTheme:
    """Theme configuration with CSS variable generation."""

    DARK = {
        "bg_primary": "#0a0a0f",
        "bg_secondary": "#12121a",
        "bg_surface": "rgba(255,255,255,0.03)",
        "border_subtle": "rgba(255,255,255,0.06)",
        "border_hover": "rgba(255,255,255,0.12)",
        "text_primary": "#e2e8f0",
        "text_secondary": "#94a3b8",
        "text_muted": "#64748b",
        "accent_indigo": "#6366f1",
        "accent_purple": "#a855f7",
        "accent_cyan": "#06b6d4",
        "accent_green": "#10b981",
        "accent_amber": "#f59e0b",
        "accent_red": "#ef4444",
    }

    LIGHT = {
        "bg_primary": "#f8fafc",
        "bg_secondary": "#ffffff",
        "bg_surface": "rgba(0,0,0,0.02)",
        "border_subtle": "rgba(0,0,0,0.06)",
        "border_hover": "rgba(0,0,0,0.12)",
        "text_primary": "#1e293b",
        "text_secondary": "#475569",
        "text_muted": "#94a3b8",
        "accent_indigo": "#4f46e5",
        "accent_purple": "#7c3aed",
        "accent_cyan": "#0891b2",
        "accent_green": "#059669",
        "accent_amber": "#d97706",
        "accent_red": "#dc2626",
    }

    GENESIS = {
        "bg_primary": "#0c0c1a",
        "bg_secondary": "#141428",
        "bg_surface": "rgba(100,100,255,0.03)",
        "border_subtle": "rgba(100,100,255,0.08)",
        "border_hover": "rgba(100,100,255,0.15)",
        "text_primary": "#e0e0ff",
        "text_secondary": "#a0a0d0",
        "text_muted": "#606090",
        "accent_indigo": "#818cf8",
        "accent_purple": "#c084fc",
        "accent_cyan": "#22d3ee",
        "accent_green": "#34d399",
        "accent_amber": "#fbbf24",
        "accent_red": "#f87171",
    }

    @classmethod
    def css_variables(cls, theme_dict: Dict[str, str]) -> str:
        """Generate CSS :root block from theme dict."""
        lines = [":root {"]
        for key, val in theme_dict.items():
            css_key = "--" + key.replace("_", "-")
            lines.append(f"  {css_key}: {val};")
        lines.append("}")
        return "\n".join(lines)


class DashboardComponent:
    """Base class for dashboard UI components."""

    def __init__(self, name: str) -> None:
        self.name = name

    def render_html(self) -> str:
        return ""

    def render_js(self) -> str:
        return ""


class StatsPanel(DashboardComponent):
    """Real-time stats panel with canvas gauge charts."""

    def render_html(self) -> str:
        return """
    <div class="panel hidden" id="panel-stats">
      <div class="card-title">Live Statistics</div>
      <div class="stats-grid" id="stats-grid">
        <div class="gauge-card">
          <canvas class="gauge-canvas" id="gauge-cpu" width="120" height="120"></canvas>
          <div class="gauge-label">CPU</div>
        </div>
        <div class="gauge-card">
          <canvas class="gauge-canvas" id="gauge-mem" width="120" height="120"></canvas>
          <div class="gauge-label">Memory</div>
        </div>
        <div class="gauge-card">
          <canvas class="gauge-canvas" id="gauge-disk" width="120" height="120"></canvas>
          <div class="gauge-label">Disk</div>
        </div>
        <div class="gauge-card">
          <canvas class="gauge-canvas" id="gauge-req" width="120" height="120"></canvas>
          <div class="gauge-label">Requests</div>
        </div>
      </div>
      <div class="card-title" style="margin-top:16px">Request History</div>
      <div class="chart-container">
        <canvas id="req-chart" width="800" height="200"></canvas>
      </div>
    </div>"""

    def render_js(self) -> str:
        return """
  // Gauge drawing
  function drawGauge(id, value, max, color) {
    const c = document.getElementById(id);
    if (!c) return;
    const ctx = c.getContext('2d');
    const center = 60, radius = 50, width = 8;
    ctx.clearRect(0, 0, 120, 120);
    // Background arc
    ctx.beginPath();
    ctx.arc(center, center, radius, 0.7 * Math.PI, 2.3 * Math.PI);
    ctx.lineWidth = width;
    ctx.strokeStyle = 'var(--border-subtle)';
    ctx.stroke();
    // Value arc
    const pct = Math.min(value / max, 1);
    const endAngle = 0.7 * Math.PI + pct * 1.6 * Math.PI;
    ctx.beginPath();
    ctx.arc(center, center, radius, 0.7 * Math.PI, endAngle);
    ctx.lineWidth = width;
    ctx.strokeStyle = color;
    ctx.lineCap = 'round';
    ctx.stroke();
    // Text
    ctx.fillStyle = 'var(--text-primary)';
    ctx.font = 'bold 20px var(--font-mono)';
    ctx.textAlign = 'center';
    ctx.fillText(Math.round(value), center, center + 5);
  }

  // Request history chart
  let reqHistory = [];
  function updateReqChart() {
    const c = document.getElementById('req-chart');
    if (!c) return;
    const ctx = c.getContext('2d');
    ctx.clearRect(0, 0, 800, 200);
    if (reqHistory.length < 2) return;
    const maxVal = Math.max(...reqHistory, 1);
    const w = 800, h = 200, pad = 20;
    const step = (w - pad * 2) / (reqHistory.length - 1);
    ctx.beginPath();
    ctx.moveTo(pad, h - pad - (reqHistory[0] / maxVal) * (h - pad * 2));
    for (let i = 1; i < reqHistory.length; i++) {
      ctx.lineTo(pad + i * step, h - pad - (reqHistory[i] / maxVal) * (h - pad * 2));
    }
    ctx.strokeStyle = 'var(--accent-indigo)';
    ctx.lineWidth = 2;
    ctx.stroke();
    // Fill area
    ctx.lineTo(pad + (reqHistory.length - 1) * step, h - pad);
    ctx.lineTo(pad, h - pad);
    ctx.closePath();
    ctx.fillStyle = 'rgba(99,102,241,0.1)';
    ctx.fill();
  }"""


class TerminalPanel(DashboardComponent):
    """Terminal-style command panel."""

    def render_html(self) -> str:
        return """
    <div class="panel hidden" id="panel-terminal">
      <div class="card-title">Terminal</div>
      <div class="terminal" id="terminal-output">
        <div class="term-line"><span class="term-prompt">$</span> <span class="term-cmd">magnatrix status</span></div>
        <div class="term-line term-out">System: Online | Modules: <span id="term-mod-count">-</span></div>
      </div>
      <div class="terminal-input-line">
        <span class="term-prompt">$</span>
        <input type="text" class="terminal-input" id="terminal-input" placeholder="Enter command..." autocomplete="off">
      </div>
    </div>"""

    def render_js(self) -> str:
        return """
  // Terminal
  const termOutput = document.getElementById('terminal-output');
  const termInput = document.getElementById('terminal-input');
  if (termInput) {
    termInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        const cmd = termInput.value.trim();
        if (!cmd) return;
        termInput.value = '';
        addTermLine('$ ' + cmd, 'cmd');
        handleCommand(cmd);
      }
    });
  }
  function addTermLine(text, type) {
    if (!termOutput) return;
    const div = document.createElement('div');
    div.className = 'term-line' + (type === 'out' ? ' term-out' : '') + (type === 'err' ? ' term-err' : '');
    div.textContent = text;
    termOutput.appendChild(div);
    termOutput.scrollTop = termOutput.scrollHeight;
  }
  function handleCommand(cmd) {
    const cmds = {
      'help': 'Commands: help, status, modules, metrics, clear, echo <text>, reload',
      'status': () => 'System: Online | Uptime: ' + document.getElementById('uptime').textContent,
      'modules': () => 'Active modules: ' + document.getElementById('module-count').textContent,
      'metrics': () => 'CPU: ' + document.getElementById('cpu-val').textContent + ' | Mem: ' + document.getElementById('mem-val').textContent,
      'clear': () => { termOutput.innerHTML = ''; return ''; },
    };
    const parts = cmd.split(' ');
    const handler = cmds[parts[0]];
    if (handler) {
      const out = typeof handler === 'function' ? handler() : handler;
      if (out) addTermLine(out, 'out');
    } else if (parts[0] === 'echo') {
      addTermLine(parts.slice(1).join(' ') || '(empty)', 'out');
    } else {
      addTermLine('Unknown command: ' + parts[0], 'err');
      addTermLine('Type "help" for available commands', 'out');
    }
  }"""


class DashboardFrontend:
    """Main frontend engine — generates the complete dashboard HTML."""

    def __init__(self, theme: str = "dark", title: str = "MAGNATRIX-OS Dashboard") -> None:
        self.theme_name = theme
        self.title = title
        self.theme = self._resolve_theme(theme)
        self.components: List[DashboardComponent] = [StatsPanel("stats"), TerminalPanel("terminal")]
        self.custom_css = ""
        self.custom_js = ""

    def _resolve_theme(self, name: str) -> Dict[str, str]:
        themes = {
            "dark": DashboardTheme.DARK,
            "light": DashboardTheme.LIGHT,
            "genesis": DashboardTheme.GENESIS,
        }
        return themes.get(name, DashboardTheme.DARK)

    def set_theme(self, name: str) -> None:
        self.theme_name = name
        self.theme = self._resolve_theme(name)

    def add_component(self, component: DashboardComponent) -> None:
        self.components.append(component)

    def _generate_css(self) -> str:
        return """
<style>
""" + DashboardTheme.css_variables(self.theme) + """
  --font-main: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  --radius: 12px; --radius-sm: 8px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.4);
  --shadow-glow: 0 0 20px rgba(99,102,241,0.15);
  --transition: all 0.2s ease;

* { margin:0; padding:0; box-sizing:border-box; }

body {
  font-family: var(--font-main);
  background: var(--bg-primary);
  color: var(--text-primary);
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Animated background */
.bg-animated {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  pointer-events: none; z-index: 0; opacity: 0.3;
}
.bg-grid {
  background-image: 
    linear-gradient(rgba(99,102,241,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99,102,241,0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  position: absolute; inset: 0;
}
.bg-glow {
  position: absolute; width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(99,102,241,0.08), transparent 70%);
  border-radius: 50%; animation: float 8s ease-in-out infinite;
  top: 20%; left: 60%;
}
.bg-glow-2 {
  position: absolute; width: 300px; height: 300px;
  background: radial-gradient(circle, rgba(168,85,247,0.06), transparent 70%);
  border-radius: 50%; animation: float 10s ease-in-out infinite reverse;
  top: 60%; left: 20%;
}
@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-30px, -30px); }
}

/* Top Bar */
.topbar {
  height: 56px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-subtle);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px; flex-shrink: 0; z-index: 100; position: relative;
}
.brand { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 18px; letter-spacing: -0.5px; }
.brand-icon {
  width: 32px; height: 32px;
  background: linear-gradient(135deg, var(--accent-indigo), var(--accent-purple));
  border-radius: 8px; display: flex; align-items: center; justify-content: center;
  font-size: 14px; color: white; box-shadow: 0 0 12px rgba(99,102,241,0.3);
  animation: iconPulse 3s ease-in-out infinite;
}
@keyframes iconPulse { 0%, 100% { box-shadow: 0 0 12px rgba(99,102,241,0.3); } 50% { box-shadow: 0 0 20px rgba(99,102,241,0.5); } }

.status-pill {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 12px; background: rgba(16,185,129,0.1);
  border: 1px solid rgba(16,185,129,0.2); border-radius: 20px;
  font-size: 12px; color: var(--accent-green); font-weight: 500;
}
.status-pill::before {
  content: ''; width: 6px; height: 6px; background: var(--accent-green);
  border-radius: 50%; box-shadow: 0 0 6px var(--accent-green); animation: pulse 2s infinite;
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.version-tag { font-size: 12px; color: var(--text-muted); font-family: var(--font-mono); }

/* Main Layout */
.main-layout { display: flex; flex: 1; overflow: hidden; position: relative; z-index: 1; }

/* Sidebar */
.sidebar {
  width: 64px; background: var(--bg-secondary);
  border-right: 1px solid var(--border-subtle);
  display: flex; flex-direction: column; align-items: center;
  padding: 12px 0; gap: 8px; flex-shrink: 0; z-index: 90;
}
.nav-btn {
  width: 44px; height: 44px; border: none; border-radius: var(--radius-sm);
  background: transparent; color: var(--text-muted); cursor: pointer;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 2px; transition: var(--transition); font-size: 10px; font-family: var(--font-main);
}
.nav-btn:hover { color: var(--text-primary); background: var(--bg-surface); }
.nav-btn.active {
  color: var(--accent-indigo); background: rgba(99,102,241,0.1);
  box-shadow: 0 0 12px rgba(99,102,241,0.1);
}
.nav-btn .icon { font-size: 18px; line-height: 1; }

/* Content Area */
.content { flex: 1; display: flex; overflow: hidden; background: var(--bg-primary); }
.panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; padding: 20px; gap: 16px; }
.panel.hidden { display: none; }

/* Cards */
.card {
  background: var(--bg-surface); border: 1px solid var(--border-subtle);
  border-radius: var(--radius); padding: 16px; backdrop-filter: blur(10px);
  transition: var(--transition); position: relative; overflow: hidden;
}
.card:hover { border-color: var(--border-hover); transform: translateY(-1px); }
.card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, var(--accent-indigo), var(--accent-purple));
  opacity: 0; transition: var(--transition);
}
.card:hover::before { opacity: 1; }
.card-title {
  font-size: 14px; font-weight: 600; color: var(--text-secondary);
  margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px;
  display: flex; align-items: center; gap: 8px;
}

/* Chat Panel */
.chat-container { flex: 1; display: flex; flex-direction: column; gap: 12px; overflow: hidden; }
.chat-messages {
  flex: 1; overflow-y: auto; display: flex; flex-direction: column;
  gap: 12px; padding-right: 8px;
}
.chat-messages::-webkit-scrollbar { width: 4px; }
.chat-messages::-webkit-scrollbar-thumb { background: var(--border-subtle); border-radius: 4px; }
.message {
  max-width: 80%; padding: 12px 16px; border-radius: var(--radius);
  font-size: 14px; line-height: 1.6; animation: fadeInUp 0.3s ease;
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.message.user {
  align-self: flex-end;
  background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(168,85,247,0.1));
  border: 1px solid rgba(99,102,241,0.2); border-bottom-right-radius: 4px;
}
.message.assistant {
  align-self: flex-start;
  background: var(--bg-surface); border: 1px solid var(--border-subtle);
  border-bottom-left-radius: 4px;
}
.message-header { font-size: 11px; color: var(--text-muted); margin-bottom: 4px; font-weight: 600; }
.message.user .message-header { color: var(--accent-indigo); }
.message.assistant .message-header { color: var(--accent-cyan); }
.typing-indicator { display: flex; gap: 4px; padding: 8px 0; }
.typing-indicator span {
  width: 6px; height: 6px; background: var(--accent-indigo);
  border-radius: 50%; animation: typing 1.4s infinite;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing { 0%, 60%, 100% { transform: translateY(0); opacity: 0.4; } 30% { transform: translateY(-4px); opacity: 1; } }

.chat-input-area { display: flex; gap: 8px; align-items: flex-end; }
.chat-input {
  flex: 1; background: var(--bg-surface); border: 1px solid var(--border-subtle);
  border-radius: var(--radius); padding: 12px 16px; color: var(--text-primary);
  font-family: var(--font-main); font-size: 14px; outline: none; resize: none;
  min-height: 44px; max-height: 120px; transition: var(--transition);
}
.chat-input:focus { border-color: var(--accent-indigo); box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
.send-btn {
  width: 44px; height: 44px;
  background: linear-gradient(135deg, var(--accent-indigo), var(--accent-purple));
  border: none; border-radius: var(--radius-sm); color: white; cursor: pointer;
  display: flex; align-items: center; justify-content: center; font-size: 16px;
  transition: var(--transition); flex-shrink: 0;
}
.send-btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-glow); }
.send-btn:active { transform: scale(0.95); }

/* Metrics */
.metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.metric-card {
  background: var(--bg-surface); border: 1px solid var(--border-subtle);
  border-radius: var(--radius); padding: 16px; transition: var(--transition);
  position: relative; overflow: hidden;
}
.metric-card:hover { border-color: var(--border-hover); transform: translateY(-1px); }
.metric-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, var(--accent-indigo), var(--accent-purple));
  opacity: 0; transition: var(--transition);
}
.metric-card:hover::before { opacity: 1; }
.metric-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.metric-value { font-size: 24px; font-weight: 700; color: var(--text-primary); font-family: var(--font-mono); letter-spacing: -0.5px; }
.metric-value.small { font-size: 18px; }
.metric-bar { height: 4px; background: var(--bg-secondary); border-radius: 2px; margin-top: 8px; overflow: hidden; }
.metric-bar-fill { height: 100%; border-radius: 2px; transition: width 0.5s ease; background: linear-gradient(90deg, var(--accent-indigo), var(--accent-purple)); }
.metric-bar-fill.warning { background: linear-gradient(90deg, var(--accent-amber), #f97316); }
.metric-bar-fill.danger { background: linear-gradient(90deg, var(--accent-red), #dc2626); }

/* Module Grid */
.module-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; overflow-y: auto; padding-right: 4px; }
.module-card {
  background: var(--bg-surface); border: 1px solid var(--border-subtle);
  border-radius: var(--radius); padding: 14px; display: flex; flex-direction: column;
  gap: 8px; transition: var(--transition); cursor: pointer; position: relative; overflow: hidden;
}
.module-card:hover { border-color: var(--border-hover); }
.module-card.active::after { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: var(--accent-green); }
.module-card.inactive::after { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: var(--accent-red); }
.module-header { display: flex; align-items: center; justify-content: space-between; }
.module-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.module-status { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.module-status.online { background: var(--accent-green); box-shadow: 0 0 6px var(--accent-green); }
.module-status.offline { background: var(--accent-red); box-shadow: 0 0 6px var(--accent-red); }
.module-status.loading { background: var(--accent-amber); animation: pulse 1s infinite; }
.module-desc { font-size: 12px; color: var(--text-muted); line-height: 1.4; }
.module-meta { display: flex; gap: 8px; font-size: 11px; color: var(--text-muted); font-family: var(--font-mono); }

/* Toggle Switch */
.toggle-switch { position: relative; width: 36px; height: 20px; background: var(--bg-secondary); border-radius: 10px; cursor: pointer; transition: var(--transition); border: 1px solid var(--border-subtle); }
.toggle-switch.on { background: linear-gradient(135deg, var(--accent-indigo), var(--accent-purple)); border-color: transparent; }
.toggle-switch::after { content: ''; position: absolute; width: 14px; height: 14px; background: white; border-radius: 50%; top: 2px; left: 2px; transition: var(--transition); box-shadow: var(--shadow-sm); }
.toggle-switch.on::after { left: 18px; }

/* Config Panel */
.config-list { display: flex; flex-direction: column; gap: 8px; overflow-y: auto; padding-right: 4px; }
.config-row { display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); transition: var(--transition); }
.config-row:hover { border-color: var(--border-hover); }
.config-key { font-size: 13px; font-weight: 500; color: var(--text-primary); font-family: var(--font-mono); min-width: 180px; }
.config-value { flex: 1; background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 6px 10px; color: var(--text-primary); font-size: 13px; font-family: var(--font-mono); outline: none; transition: var(--transition); }
.config-value:focus { border-color: var(--accent-indigo); box-shadow: 0 0 0 2px rgba(99,102,241,0.1); }
.config-type { font-size: 11px; color: var(--text-muted); font-family: var(--font-mono); background: var(--bg-secondary); padding: 2px 8px; border-radius: 4px; }

/* Log Panel */
.log-stream { flex: 1; background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius); padding: 12px; overflow-y: auto; font-family: var(--font-mono); font-size: 12px; line-height: 1.6; }
.log-entry { display: flex; gap: 8px; padding: 2px 0; border-bottom: 1px solid rgba(255,255,255,0.02); }
.log-time { color: var(--text-muted); min-width: 80px; flex-shrink: 0; }
.log-level { min-width: 50px; font-weight: 600; flex-shrink: 0; }
.log-level.info { color: var(--accent-cyan); }
.log-level.warn { color: var(--accent-amber); }
.log-level.error { color: var(--accent-red); }
.log-level.debug { color: var(--text-muted); }
.log-msg { color: var(--text-secondary); word-break: break-word; }

/* Right Panel */
.right-panel {
  width: 280px; background: var(--bg-secondary); border-left: 1px solid var(--border-subtle);
  display: flex; flex-direction: column; gap: 16px; padding: 20px; overflow-y: auto; flex-shrink: 0;
}
.right-panel.collapsed { width: 0; padding: 0; overflow: hidden; border: none; }
.section-title { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
.quick-stat { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border-subtle); font-size: 13px; }
.quick-stat-label { color: var(--text-muted); }
.quick-stat-value { color: var(--text-primary); font-weight: 600; font-family: var(--font-mono); }

/* Stats Panel Gauges */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px; }
.gauge-card { background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius); padding: 16px; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.gauge-canvas { width: 120px; height: 120px; }
.gauge-label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.chart-container { background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius); padding: 16px; }

/* Terminal Panel */
.terminal {
  flex: 1; background: var(--bg-secondary); border: 1px solid var(--border-subtle);
  border-radius: var(--radius); padding: 12px; overflow-y: auto; font-family: var(--font-mono);
  font-size: 13px; line-height: 1.6;
}
.term-line { padding: 2px 0; }
.term-prompt { color: var(--accent-green); font-weight: 600; margin-right: 4px; }
.term-cmd { color: var(--text-primary); }
.term-out { color: var(--text-secondary); }
.term-err { color: var(--accent-red); }
.terminal-input-line { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); margin-top: 8px; }
.terminal-input { flex: 1; background: transparent; border: none; color: var(--text-primary); font-family: var(--font-mono); font-size: 13px; outline: none; }

/* Bottom Status Bar */
.statusbar {
  height: 32px; background: var(--bg-secondary); border-top: 1px solid var(--border-subtle);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px; font-size: 12px; color: var(--text-muted); flex-shrink: 0; z-index: 100; position: relative;
}
.statusbar-left, .statusbar-right { display: flex; gap: 16px; align-items: center; }
.statusbar-item { display: flex; align-items: center; gap: 6px; }
.statusbar-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent-green); box-shadow: 0 0 4px var(--accent-green); }
.statusbar-dot.warning { background: var(--accent-amber); box-shadow: 0 0 4px var(--accent-amber); }
.statusbar-dot.error { background: var(--accent-red); box-shadow: 0 0 4px var(--accent-red); }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-subtle); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--border-hover); }

/* Responsive */
@media (max-width: 900px) {
  .right-panel { display: none; }
  .module-grid { grid-template-columns: 1fr; }
  .metrics-grid { grid-template-columns: repeat(2, 1fr); }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}

/* Animations */
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.panel { animation: fadeIn 0.2s ease; }

/* Code blocks in messages */
.message pre { background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 12px; overflow-x: auto; font-family: var(--font-mono); font-size: 12px; margin: 8px 0; }
.message code { background: var(--bg-secondary); padding: 2px 6px; border-radius: 4px; font-family: var(--font-mono); font-size: 13px; color: var(--accent-cyan); }

/* Info Badge */
.info-badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; font-family: var(--font-mono); background: rgba(99,102,241,0.1); color: var(--accent-indigo); border: 1px solid rgba(99,102,241,0.2); }

/* Category badges */
.cat-core { border-left: 3px solid var(--accent-indigo); }
.cat-governance { border-left: 3px solid var(--accent-purple); }
.cat-calculator { border-left: 3px solid var(--accent-cyan); }
.cat-infrastructure { border-left: 3px solid var(--accent-green); }
.cat-genesis { border-left: 3px solid var(--accent-amber); }

""" + self.custom_css + """
</style>"""

    def _generate_html_structure(self) -> str:
        components_html = "".join(c.render_html() for c in self.components)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{self.title}</title>
{self._generate_css()}
</head>
<body>

<!-- Animated Background -->
<div class="bg-animated">
  <div class="bg-grid"></div>
  <div class="bg-glow"></div>
  <div class="bg-glow-2"></div>
</div>

<!-- Top Bar -->
<div class="topbar">
  <div class="brand">
    <div class="brand-icon">M</div>
    <span>MAGNATRIX-OS</span>
  </div>
  <div class="status-pill">System Online</div>
  <div class="version-tag" id="version">v2.0.0</div>
</div>

<!-- Main Layout -->
<div class="main-layout">
  <!-- Sidebar -->
  <div class="sidebar">
    <button class="nav-btn active" data-panel="chat" title="Chat">
      <span class="icon">&#x1F4AC;</span>
    </button>
    <button class="nav-btn" data-panel="modules" title="Modules">
      <span class="icon">&#x2699;&#xFE0F;</span>
    </button>
    <button class="nav-btn" data-panel="metrics" title="Metrics">
      <span class="icon">&#x1F4CA;</span>
    </button>
    <button class="nav-btn" data-panel="stats" title="Stats">
      <span class="icon">&#x1F4C8;</span>
    </button>
    <button class="nav-btn" data-panel="terminal" title="Terminal">
      <span class="icon">&#x1F5B0;</span>
    </button>
    <button class="nav-btn" data-panel="config" title="Config">
      <span class="icon">&#x1F527;</span>
    </button>
    <button class="nav-btn" data-panel="logs" title="Logs">
      <span class="icon">&#x1F4C3;</span>
    </button>
    <button class="nav-btn" data-panel="system" title="System">
      <span class="icon">&#x1F4BB;</span>
    </button>
  </div>

  <!-- Content -->
  <div class="content">
    <!-- CHAT PANEL -->
    <div class="panel" id="panel-chat">
      <div class="chat-container">
        <div class="chat-messages" id="chat-messages">
          <div class="message assistant">
            <div class="message-header">MAGNATRIX-OS</div>
            <div>Welcome to MAGNATRIX-OS. I am your private, uncensored AI operating system. How can I help you today?</div>
          </div>
        </div>
        <div class="chat-input-area">
          <textarea class="chat-input" id="chat-input" placeholder="Type your message..." rows="1"></textarea>
          <button class="send-btn" id="send-btn">&#x27A4;</button>
        </div>
      </div>
    </div>

    <!-- MODULES PANEL -->
    <div class="panel hidden" id="panel-modules">
      <div class="card-title">Core Modules <span class="info-badge" id="badge-modules">Loading...</span></div>
      <div class="module-grid" id="module-grid"></div>
    </div>

    <!-- METRICS PANEL -->
    <div class="panel hidden" id="panel-metrics">
      <div class="card-title">System Metrics</div>
      <div class="metrics-grid" id="metrics-grid"></div>
      <div class="card-title" style="margin-top:8px">Module Status</div>
      <div class="module-grid" id="metrics-modules"></div>
    </div>

    <!-- STATS PANEL (new canvas gauges) -->
    {StatsPanel("stats").render_html()}

    <!-- TERMINAL PANEL -->
    {TerminalPanel("terminal").render_html()}

    <!-- CONFIG PANEL -->
    <div class="panel hidden" id="panel-config">
      <div class="card-title">Configuration</div>
      <div class="config-list" id="config-list"></div>
    </div>

    <!-- LOGS PANEL -->
    <div class="panel hidden" id="panel-logs">
      <div class="card-title">System Logs</div>
      <div class="log-stream" id="log-stream"></div>
    </div>

    <!-- SYSTEM PANEL -->
    <div class="panel hidden" id="panel-system">
      <div class="card-title">System Information</div>
      <div class="metrics-grid" id="system-info"></div>
    </div>
  </div>

  <!-- Right Panel -->
  <div class="right-panel" id="right-panel">
    <div class="section-title">Overview</div>
    <div class="quick-stat">
      <span class="quick-stat-label">Status</span>
      <span class="quick-stat-value" style="color:var(--accent-green)">Healthy</span>
    </div>
    <div class="quick-stat">
      <span class="quick-stat-label">Uptime</span>
      <span class="quick-stat-value" id="uptime">0s</span>
    </div>
    <div class="quick-stat">
      <span class="quick-stat-label">Modules</span>
      <span class="quick-stat-value" id="module-count">-</span>
    </div>
    <div class="quick-stat">
      <span class="quick-stat-label">Requests</span>
      <span class="quick-stat-value" id="request-count">0</span>
    </div>
    <div class="section-title" style="margin-top:12px">Resources</div>
    <div id="resource-bars">
      <div class="metric-card" style="margin-bottom:8px">
        <div class="metric-label">CPU</div>
        <div class="metric-value small" id="cpu-val">0%</div>
        <div class="metric-bar"><div class="metric-bar-fill" id="cpu-bar" style="width:0%"></div></div>
      </div>
      <div class="metric-card" style="margin-bottom:8px">
        <div class="metric-label">Memory</div>
        <div class="metric-value small" id="mem-val">0%</div>
        <div class="metric-bar"><div class="metric-bar-fill" id="mem-bar" style="width:0%"></div></div>
      </div>
      <div class="metric-card" style="margin-bottom:8px">
        <div class="metric-label">Disk</div>
        <div class="metric-value small" id="disk-val">0%</div>
        <div class="metric-bar"><div class="metric-bar-fill" id="disk-bar" style="width:0%"></div></div>
      </div>
    </div>
  </div>
</div>

<!-- Status Bar -->
<div class="statusbar">
  <div class="statusbar-left">
    <div class="statusbar-item">
      <div class="statusbar-dot"></div>
      <span id="status-text">Connected</span>
    </div>
    <div class="statusbar-item">Modules: <span id="sb-modules">-</span></div>
    <div class="statusbar-item">Files: <span id="sb-files">-</span></div>
  </div>
  <div class="statusbar-right">
    <div class="statusbar-item">Core: <span id="sb-core">-</span></div>
    <div class="statusbar-item">Gov: <span id="sb-gov">-</span></div>
    <div class="statusbar-item">Calc: <span id="sb-calc">-</span></div>
  </div>
</div>
"""

    def _generate_js(self) -> str:
        components_js = "".join(c.render_js() for c in self.components)
        return f"""<script>
(function() {{
  const API = {{
    async chat(msg) {{
      try {{
        const res = await fetch('/api/chat', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ message: msg }}) }});
        return await res.json();
      }} catch(e) {{ return {{ text: 'Error: ' + e.message, error: true }}; }}
    }},
    async metrics() {{ try {{ const res = await fetch('/api/metrics'); return await res.json(); }} catch(e) {{ return {{}}; }} }},
    async modules() {{ try {{ const res = await fetch('/api/modules'); return await res.json(); }} catch(e) {{ return []; }} }},
    async logs() {{ try {{ const res = await fetch('/api/logs'); return await res.json(); }} catch(e) {{ return []; }} }},
    async system() {{ try {{ const res = await fetch('/api/system'); return await res.json(); }} catch(e) {{ return {{}}; }} }},
    async health() {{ try {{ const res = await fetch('/api/health'); return await res.json(); }} catch(e) {{ return {{}}; }} }}
  }};

  const $ = id => document.getElementById(id);
  const chatMessages = $('chat-messages');
  const chatInput = $('chat-input');
  const sendBtn = $('send-btn');
  let typingEl = null;

  function addMessage(text, sender) {{
    const div = document.createElement('div');
    div.className = 'message ' + sender;
    const header = sender === 'user' ? 'You' : 'MAGNATRIX-OS';
    const color = sender === 'user' ? 'var(--accent-indigo)' : 'var(--accent-cyan)';
    div.innerHTML = `<div class="message-header" style="color:${{color}}">${{header}}</div><div>${{escapeHtml(text)}}</div>`;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }}

  function showTyping() {{
    if (typingEl) typingEl.remove();
    typingEl = document.createElement('div');
    typingEl.className = 'message assistant';
    typingEl.innerHTML = '<div class="message-header">MAGNATRIX-OS</div><div class="typing-indicator"><span></span><span></span><span></span></div>';
    chatMessages.appendChild(typingEl);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }}

  function hideTyping() {{
    if (typingEl) {{ typingEl.remove(); typingEl = null; }}
  }}

  function escapeHtml(t) {{
    return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }}

  async function sendMessage() {{
    const text = chatInput.value.trim();
    if (!text) return;
    chatInput.value = '';
    chatInput.style.height = '44px';
    addMessage(text, 'user');
    showTyping();
    const res = await API.chat(text);
    hideTyping();
    if (res.error) {{
      addMessage('Service unavailable. Response mocked: ' + text, 'assistant');
    }} else {{
      addMessage(res.text || JSON.stringify(res), 'assistant');
    }}
  }}

  sendBtn.addEventListener('click', sendMessage);
  chatInput.addEventListener('keydown', e => {{
    if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); sendMessage(); }}
  }});
  chatInput.addEventListener('input', function() {{
    this.style.height = '44px';
    this.style.height = Math.min(120, this.scrollHeight) + 'px';
  }});

  // Navigation
  document.querySelectorAll('.nav-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
      $('panel-' + btn.dataset.panel).classList.remove('hidden');
      if (btn.dataset.panel === 'modules') loadModules();
      if (btn.dataset.panel === 'metrics') loadMetrics();
      if (btn.dataset.panel === 'stats') loadStats();
      if (btn.dataset.panel === 'config') loadConfig();
      if (btn.dataset.panel === 'logs') loadLogs();
      if (btn.dataset.panel === 'system') loadSystem();
    }});
  }});

  // Modules
  async function loadModules() {{
    const data = await API.modules();
    const grid = $('module-grid');
    grid.innerHTML = '';
    const categories = {{'core': 'cat-core', 'governance': 'cat-governance', 'calculator': 'cat-calculator'}};
    (data || []).forEach(m => {{
      const card = document.createElement('div');
      const catClass = categories[m.category] || 'cat-infrastructure';
      card.className = 'module-card ' + (m.active ? 'active' : 'inactive') + ' ' + catClass;
      card.innerHTML = `
        <div class="module-header">
          <span class="module-name">${{m.name}}</span>
          <div class="module-status ${{m.active ? 'online' : 'offline'}}"></div>
        </div>
        <div class="module-desc">${{m.description || 'No description'}}</div>
        <div class="module-meta">
          <span>${{m.state || 'unknown'}}</span>
          <span>${{m.load_time_ms ? m.load_time_ms.toFixed(0) + 'ms' : '-'}}</span>
        </div>
      `;
      grid.appendChild(card);
    }});
  }}

  // Metrics
  async function loadMetrics() {{
    const data = await API.metrics();
    const grid = $('metrics-grid');
    if (!grid.querySelector('.metric-card')) {{
      const metrics = [
        {{ label: 'CPU Usage', key: 'cpu', unit: '%' }},
        {{ label: 'Memory', key: 'memory', unit: '%' }},
        {{ label: 'Disk', key: 'disk', unit: '%' }},
        {{ label: 'Load', key: 'load', unit: '' }},
      ];
      metrics.forEach(m => {{
        const card = document.createElement('div');
        card.className = 'metric-card';
        card.innerHTML = `
          <div class="metric-label">${{m.label}}</div>
          <div class="metric-value" id="metric-${{m.key}}">0${{m.unit}}</div>
          <div class="metric-bar"><div class="metric-bar-fill" id="metric-bar-${{m.key}}" style="width:0%"></div></div>
        `;
        grid.appendChild(card);
      }});
    }}
    Object.keys(data).forEach(k => {{
      const el = $('metric-' + k);
      const bar = $('metric-bar-' + k);
      if (el && data[k]) {{
        el.textContent = (data[k].value || 0) + (data[k].unit || '');
        if (bar) {{
          const pct = Math.min(data[k].value || 0, 100);
          bar.style.width = pct + '%';
          bar.className = 'metric-bar-fill' + (pct > 90 ? ' danger' : pct > 70 ? ' warning' : '');
        }}
      }}
    }});
  }}

  // Stats Panel with canvas gauges
  async function loadStats() {{
    const data = await API.metrics();
    const health = await API.health();
    const cpu = data.cpu?.value || 0;
    const mem = data.memory?.value || 0;
    const disk = data.disk?.value || 0;
    const req = health.requests || 0;
    drawGauge('gauge-cpu', cpu, 100, 'var(--accent-indigo)');
    drawGauge('gauge-mem', mem, 100, 'var(--accent-purple)');
    drawGauge('gauge-disk', disk, 100, 'var(--accent-cyan)');
    drawGauge('gauge-req', req % 100, 100, 'var(--accent-green)');
    reqHistory.push(req);
    if (reqHistory.length > 20) reqHistory.shift();
    updateReqChart();
  }}

  // Config
  async function loadConfig() {{
    const list = $('config-list');
    list.innerHTML = '';
    const configs = [
      {{ key: 'system.name', value: 'MAGNATRIX-OS', type: 'str' }},
      {{ key: 'system.version', value: '2.0.0', type: 'str' }},
      {{ key: 'server.host', value: '0.0.0.0', type: 'str' }},
      {{ key: 'server.port', value: '8080', type: 'int' }},
      {{ key: 'llm.provider', value: 'ollama', type: 'str' }},
      {{ key: 'llm.model', value: 'qwen2.5:7b', type: 'str' }},
      {{ key: 'features.rag', value: 'true', type: 'bool' }},
      {{ key: 'features.mesh', value: 'false', type: 'bool' }},
    ];
    configs.forEach(cfg => {{
      const row = document.createElement('div');
      row.className = 'config-row';
      row.innerHTML = `
        <span class="config-key">${{cfg.key}}</span>
        <input class="config-value" value="${{cfg.value}}" type="${{cfg.type === 'bool' ? 'checkbox' : 'text'}}" ${{cfg.type === 'bool' && cfg.value === 'true' ? 'checked' : ''}}>
        <span class="config-type">${{cfg.type}}</span>
      `;
      list.appendChild(row);
    }});
  }}

  // Logs
  async function loadLogs() {{
    const data = await API.logs();
    const stream = $('log-stream');
    stream.innerHTML = '';
    (data || []).forEach(l => {{
      const entry = document.createElement('div');
      entry.className = 'log-entry';
      const time = new Date((l.timestamp || Date.now()) * 1000).toLocaleTimeString();
      entry.innerHTML = `<span class="log-time">${{time}}</span><span class="log-level ${{l.level.toLowerCase()}}">${{l.level}}</span><span class="log-msg">${{escapeHtml(l.message)}}</span>`;
      stream.appendChild(entry);
    }});
    stream.scrollTop = stream.scrollHeight;
  }}

  // System
  async function loadSystem() {{
    const data = await API.system();
    const grid = $('system-info');
    grid.innerHTML = '';
    const info = [
      {{ label: 'OS', value: data.os_name + ' ' + data.os_version }},
      {{ label: 'Architecture', value: data.arch }},
      {{ label: 'Processor', value: data.processor }},
      {{ label: 'Python', value: data.python_version }},
      {{ label: 'CPU Cores', value: data.cpu_count }},
      {{ label: 'Memory', value: (data.memory_total / (1024**3)).toFixed(1) + ' GB' }},
      {{ label: 'Hostname', value: data.hostname }},
      {{ label: 'Container', value: data.is_container ? 'Yes' : 'No' }},
    ];
    info.forEach(i => {{
      const card = document.createElement('div');
      card.className = 'metric-card';
      card.innerHTML = `<div class="metric-label">${{i.label}}</div><div class="metric-value small">${{i.value || '-'}}</div>`;
      grid.appendChild(card);
    }});
  }}

  // Update stats from health API
  async function updateStats() {{
    const health = await API.health();
    $('module-count').textContent = health.modules || '-';
    $('request-count').textContent = health.requests || 0;
    $('sb-modules').textContent = health.modules || '-';
    $('sb-files').textContent = health.files || '-';
    $('sb-core').textContent = health.core || '-';
    $('sb-gov').textContent = health.governance || '-';
    $('sb-calc').textContent = health.calculators || '-';
    $('badge-modules').textContent = (health.modules || 0) + ' active';
    if (health.status === 'ok') {{
      $('status-text').textContent = 'Connected';
      document.querySelector('.statusbar-dot').className = 'statusbar-dot';
    }} else {{
      $('status-text').textContent = 'Degraded';
      document.querySelector('.statusbar-dot').className = 'statusbar-dot warning';
    }}
    // Update resource bars
    const metrics = await API.metrics();
    if (metrics.cpu) {{ $('cpu-val').textContent = metrics.cpu.value + '%'; $('cpu-bar').style.width = metrics.cpu.value + '%'; }}
    if (metrics.memory) {{ $('mem-val').textContent = metrics.memory.value + '%'; $('mem-bar').style.width = metrics.memory.value + '%'; }}
    if (metrics.disk) {{ $('disk-val').textContent = metrics.disk.value + '%'; $('disk-bar').style.width = metrics.disk.value + '%'; }}
    $('cpu-bar').className = 'metric-bar-fill' + ((metrics.cpu?.value || 0) > 70 ? ' warning' : '');
    $('mem-bar').className = 'metric-bar-fill' + ((metrics.memory?.value || 0) > 90 ? ' danger' : (metrics.memory?.value || 0) > 70 ? ' warning' : '');
  }}

  {components_js}

  // Uptime counter
  let uptime = 0;
  setInterval(() => {{
    uptime++;
    const h = Math.floor(uptime / 3600);
    const m = Math.floor((uptime % 3600) / 60);
    const s = uptime % 60;
    $('uptime').textContent = h > 0 ? `${{h}}h ${{m}}m` : `${{m}}m ${{s}}s`;
  }}, 1000);

  setInterval(updateStats, 3000);
  updateStats();
  loadModules();
}})();
{self.custom_js}
</script>
</body>
</html>"""

    def generate_html(self) -> str:
        """Generate the complete dashboard HTML."""
        return self._generate_html_structure() + self._generate_js()

    def save(self, path: str) -> None:
        """Save generated dashboard to file."""
        Path(path).write_text(self.generate_html(), encoding="utf-8")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "theme": self.theme_name,
            "title": self.title,
            "components": [c.name for c in self.components],
            "html_size": len(self.generate_html()),
        }


class DashboardManager:
    """Manages dashboard lifecycle: generate, update, serve."""

    def __init__(self, repo_root: Optional[str] = None) -> None:
        self.root = Path(repo_root).resolve() if repo_root else Path(os.path.dirname(__file__)).parent.resolve()
        self.frontend = DashboardFrontend()
        self._html_path = self.root / "core" / "dashboard.html"

    def generate(self, theme: str = "dark") -> str:
        self.frontend.set_theme(theme)
        html = self.frontend.generate_html()
        self._html_path.write_text(html, encoding="utf-8")
        return str(self._html_path)

    def regenerate(self) -> str:
        return self.generate(self.frontend.theme_name)

    def switch_theme(self, theme: str) -> str:
        return self.generate(theme)

    def stats(self) -> Dict[str, Any]:
        return {
            "frontend": self.frontend.get_stats(),
            "html_path": str(self._html_path),
            "html_exists": self._html_path.exists(),
            "html_size": self._html_path.stat().st_size if self._html_path.exists() else 0,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== Dashboard Frontend Engine Demo ===\n")
    engine = DashboardFrontend(theme="genesis")
    stats = engine.get_stats()
    print(f"Theme: {stats['theme']}")
    print(f"Components: {stats['components']}")
    print(f"HTML size: {stats['html_size']} bytes")
    print("\nGenerating dashboard.html...")
    engine.save("/tmp/dashboard_genesis.html")
    print("Saved to /tmp/dashboard_genesis.html")

    manager = DashboardManager()
    path = manager.generate("dark")
    print(f"\nDashboardManager generated: {path}")
    print(f"Stats: {manager.stats()}")


if __name__ == "__main__":
    _demo()
