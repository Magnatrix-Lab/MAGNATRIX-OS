#!/usr/bin/env python3
"""
MAGNATRIX-OS Web UI Native Layer
================================
Pure Python, stdlib only. Generates dashboard HTML/JS and serves via built-in HTTP.

Classes:
    WebUIManager      — Main UI orchestrator, generates and serves dashboard
    ComponentRegistry   — Register UI components (panels, widgets, charts)
    PanelBuilder        — Build individual panels (trading, AI, security, etc.)
    WebSocketHandler    — Real-time WebSocket-like communication (SSE fallback)
    ThemeManager        — Dark/light theme, CSS generation
    AssetBundler        — Bundle JS/CSS assets (concatenation, minification simulation)
    RouteHandler        — HTTP route handling for dashboard API endpoints
    DataFeed            — Push real-time data to UI (layer status, metrics, logs)
    ChartRenderer       — Generate chart data (JSON for Chart.js or canvas)
    FormBuilder         — Generate HTML forms from Python schemas
    TableRenderer       — Generate sortable/filterable tables from data
    ModalManager        — Modal dialog management (alerts, confirmations, prompts)
"""

import json
import threading
import time
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse


# ═══════════════════════════════════════════════════════════════════════════════
# ThemeManager — CSS generation for dark/light themes
# ═══════════════════════════════════════════════════════════════════════════════

class ThemeManager:
    """Generates CSS for dark glassmorphism theme (light mode supported)."""

    DARK = {
        "bg": "#0a0a0f",
        "surface": "rgba(20, 20, 30, 0.7)",
        "surface_hover": "rgba(30, 30, 45, 0.8)",
        "border": "rgba(255, 255, 255, 0.08)",
        "text": "#e0e0e0",
        "text_secondary": "#888888",
        "accent": "#00d4aa",
        "accent_hover": "#00b894",
        "danger": "#ff4757",
        "warning": "#ffa502",
        "success": "#2ed573",
        "glass": "backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);",
        "shadow": "0 8px 32px rgba(0, 0, 0, 0.4)",
        "panel_radius": "12px",
        "font": "'Segoe UI', system-ui, -apple-system, sans-serif",
    }

    LIGHT = {
        "bg": "#f0f2f5",
        "surface": "rgba(255, 255, 255, 0.85)",
        "surface_hover": "rgba(245, 245, 250, 0.9)",
        "border": "rgba(0, 0, 0, 0.08)",
        "text": "#1a1a2e",
        "text_secondary": "#666666",
        "accent": "#00b894",
        "accent_hover": "#009975",
        "danger": "#e74c3c",
        "warning": "#f39c12",
        "success": "#27ae60",
        "glass": "backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);",
        "shadow": "0 8px 32px rgba(0, 0, 0, 0.1)",
        "panel_radius": "12px",
        "font": "'Segoe UI', system-ui, -apple-system, sans-serif",
    }

    def __init__(self, mode="dark"):
        self.mode = mode
        self.tokens = self.DARK if mode == "dark" else self.LIGHT

    def set_mode(self, mode):
        self.mode = mode
        self.tokens = self.DARK if mode == "dark" else self.LIGHT

    def generate_css(self):
        t = self.tokens
        return f"""
:root {{
    --bg: {t['bg']}; --surface: {t['surface']}; --surface-hover: {t['surface_hover']};
    --border: {t['border']}; --text: {t['text']}; --text-secondary: {t['text_secondary']};
    --accent: {t['accent']}; --accent-hover: {t['accent_hover']};
    --danger: {t['danger']}; --warning: {t['warning']}; --success: {t['success']};
    --shadow: {t['shadow']}; --radius: {t['panel_radius']}; --font: {t['font']};
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    background: var(--bg); color: var(--text); font-family: var(--font);
    min-height: 100vh; overflow-x: hidden;
}}
.glass {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); {t['glass']}
    box-shadow: var(--shadow);
}}
.panel {{
    padding: 16px; transition: transform 0.2s, background 0.2s;
}}
.panel:hover {{ background: var(--surface-hover); }}
.status-green {{ color: var(--success); }}
.status-yellow {{ color: var(--warning); }}
.status-red {{ color: var(--danger); }}
.btn {{
    background: var(--accent); color: #fff; border: none; padding: 8px 16px;
    border-radius: 6px; cursor: pointer; font-family: var(--font); transition: background 0.2s;
}}
.btn:hover {{ background: var(--accent-hover); }}
.grid-dashboard {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px; padding: 16px;
}}
.header {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 16px; position: sticky; top: 0; z-index: 100;
}}
.log-viewer {{
    height: 200px; overflow-y: auto; font-family: monospace; font-size: 12px;
    background: rgba(0,0,0,0.2); border-radius: 8px; padding: 8px;
}}
.log-entry {{ margin-bottom: 2px; }}
.modal-overlay {{
    position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    display: none; justify-content: center; align-items: center; z-index: 200;
}}
.modal-overlay.active {{ display: flex; }}
.modal-box {{
    background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 24px; max-width: 420px; width: 90%; {t['glass']}
}}
.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
th {{ cursor: pointer; user-select: none; color: var(--text-secondary); }}
th:hover {{ color: var(--accent); }}
input, select, textarea {{
    background: rgba(0,0,0,0.2); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: 6px; font-family: var(--font); width: 100%;
}}
@media (max-width: 768px) {{
    .grid-dashboard {{ grid-template-columns: 1fr; padding: 8px; }}
    .header {{ flex-direction: column; gap: 8px; }}
}}
"""


# ═══════════════════════════════════════════════════════════════════════════════
# AssetBundler — Bundle JS/CSS assets (concatenation, minification simulation)
# ═══════════════════════════════════════════════════════════════════════════════

class AssetBundler:
    """Concatenates and simulates minification for JS/CSS assets."""

    def __init__(self):
        self._js = []
        self._css = []

    def add_js(self, code: str):
        self._js.append(code.strip())

    def add_css(self, code: str):
        self._css.append(code.strip())

    def bundle_js(self) -> str:
        return "\n".join(self._js)

    def bundle_css(self) -> str:
        return "\n".join(self._css)

    def simulate_minify(self, code: str) -> str:
        """Basic minification: strip comments and extra whitespace."""
        lines = []
        for line in code.splitlines():
            line = line.strip()
            if line and not line.startswith("//"):
                lines.append(line)
        return " ".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# ChartRenderer — Generate chart data (JSON for Chart.js or canvas)
# ═══════════════════════════════════════════════════════════════════════════════

class ChartRenderer:
    """Generates chart configuration JSON and minimal canvas rendering logic."""

    CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"

    @staticmethod
    def line(labels, datasets, title=""):
        return {
            "type": "line",
            "data": {"labels": labels, "datasets": datasets},
            "options": {
                "responsive": True,
                "plugins": {"legend": {"labels": {"color": "#e0e0e0"}}},
                "scales": {
                    "x": {"ticks": {"color": "#888"}, "grid": {"color": "rgba(255,255,255,0.05)"}},
                    "y": {"ticks": {"color": "#888"}, "grid": {"color": "rgba(255,255,255,0.05)"}},
                },
            },
        }

    @staticmethod
    def bar(labels, datasets, title=""):
        return {
            "type": "bar",
            "data": {"labels": labels, "datasets": datasets},
            "options": {
                "responsive": True,
                "plugins": {"legend": {"labels": {"color": "#e0e0e0"}}},
                "scales": {
                    "x": {"ticks": {"color": "#888"}, "grid": {"color": "rgba(255,255,255,0.05)"}},
                    "y": {"ticks": {"color": "#888"}, "grid": {"color": "rgba(255,255,255,0.05)"}},
                },
            },
        }

    @staticmethod
    def pie(labels, data, colors=None):
        colors = colors or ["#00d4aa", "#ffa502", "#ff4757", "#2ed573", "#3742fa", "#ff6348"]
        return {
            "type": "pie",
            "data": {
                "labels": labels,
                "datasets": [{"data": data, "backgroundColor": colors[: len(labels)]}],
            },
            "options": {"responsive": True, "plugins": {"legend": {"labels": {"color": "#e0e0e0"}}}},
        }

    def render_html(self, chart_id, config):
        return f"""
<div style="position:relative;height:250px;width:100%;">
    <canvas id="{chart_id}"></canvas>
</div>
<script>
    new Chart(document.getElementById('{chart_id}'), {json.dumps(config)});
</script>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# FormBuilder — Generate HTML forms from Python schemas
# ═══════════════════════════════════════════════════════════════════════════════

class FormBuilder:
    """Generates HTML forms from simple schema dictionaries."""

    TYPE_MAP = {
        "str": "text",
        "int": "number",
        "float": "number",
        "bool": "checkbox",
        "text": "textarea",
        "select": "select",
        "email": "email",
        "password": "password",
        "date": "date",
    }

    def generate(self, schema: dict, form_id: str = None) -> str:
        form_id = form_id or f"form_{uuid.uuid4().hex[:8]}"
        fields = []
        for name, spec in schema.items():
            if isinstance(spec, str):
                spec = {"type": spec}
            ftype = spec.get("type", "str")
            label = spec.get("label", name.replace("_", " ").title())
            required = "required" if spec.get("required") else ""
            placeholder = spec.get("placeholder", "")
            options = spec.get("options", [])

            input_html = ""
            if ftype == "select":
                opts = "".join(f'<option value="{o}">{o}</option>' for o in options)
                input_html = f'<select name="{name}" {required}>{opts}</select>'
            elif ftype == "textarea":
                input_html = f'<textarea name="{name}" rows="3" placeholder="{placeholder}" {required}></textarea>'
            elif ftype == "bool":
                input_html = f'<input type="checkbox" name="{name}" style="width:auto;">'
            else:
                html_type = self.TYPE_MAP.get(ftype, "text")
                input_html = f'<input type="{html_type}" name="{name}" placeholder="{placeholder}" {required}>'

            fields.append(f"""
                <div style="margin-bottom:12px;">
                    <label style="display:block;margin-bottom:4px;font-size:13px;color:var(--text-secondary);">{label}</label>
                    {input_html}
                </div>
            """)

        return f"""
<form id="{form_id}" onsubmit="return false;">
    {''.join(fields)}
    <button type="submit" class="btn">Submit</button>
</form>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# TableRenderer — Generate sortable/filterable tables from data
# ═══════════════════════════════════════════════════════════════════════════════

class TableRenderer:
    """Generates HTML tables with sorting, filtering, and pagination."""

    def __init__(self, page_size=10):
        self.page_size = page_size

    def render(self, data: list, columns: list = None, table_id: str = None) -> str:
        if not data:
            return "<p style='color:var(--text-secondary);padding:12px;'>No data available.</p>"
        table_id = table_id or f"tbl_{uuid.uuid4().hex[:8]}"
        columns = columns or list(data[0].keys())

        headers = "".join(
            f'<th onclick="sortTable(\'{table_id}\', {i})">{c}</th>' for i, c in enumerate(columns)
        )
        rows = ""
        for row in data[: self.page_size]:
            cells = "".join(f"<td>{row.get(c, '')}</td>" for c in columns)
            rows += f"<tr>{cells}</tr>"

        return f"""
<div class="table-wrap">
    <input type="text" placeholder="Filter..." onkeyup="filterTable('{table_id}', this.value)"
        style="margin-bottom:8px;max-width:300px;">
    <table id="{table_id}">
        <thead><tr>{headers}</tr></thead>
        <tbody>{rows}</tbody>
    </table>
</div>
<script>
function sortTable(id, col) {{
    const table = document.getElementById(id);
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    const asc = table.dataset.sortCol != col || table.dataset.sortDir != 'asc';
    rows.sort((a,b) => {{
        const av = a.cells[col].textContent.trim();
        const bv = b.cells[col].textContent.trim();
        return asc ? av.localeCompare(bv) : bv.localeCompare(av);
    }});
    table.dataset.sortCol = col; table.dataset.sortDir = asc ? 'asc' : 'desc';
    rows.forEach(r => table.querySelector('tbody').appendChild(r));
}}
function filterTable(id, q) {{
    const table = document.getElementById(id);
    table.querySelectorAll('tbody tr').forEach(r => {{
        r.style.display = r.textContent.toLowerCase().includes(q.toLowerCase()) ? '' : 'none';
    }});
}}
</script>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# ModalManager — Modal dialog management (alerts, confirmations, prompts)
# ═══════════════════════════════════════════════════════════════════════════════

class ModalManager:
    """Generates modal HTML/JS for alerts, confirmations, and prompts."""

    def alert(self, message: str, title: str = "Alert") -> str:
        return self._modal_html(title, message, buttons='<button class="btn" onclick="closeModal()">OK</button>')

    def confirm(self, message: str, title: str = "Confirm", on_yes: str = "") -> str:
        return self._modal_html(
            title,
            message,
            buttons=f"""
                <button class="btn" style="background:var(--danger);" onclick="closeModal()">Cancel</button>
                <button class="btn" onclick="{on_yes}; closeModal();">Confirm</button>
            """,
        )

    def _modal_html(self, title, body, buttons):
        return f"""
<div class="modal-overlay" id="modal-overlay">
    <div class="modal-box">
        <h3 style="margin-bottom:12px;">{title}</h3>
        <p style="margin-bottom:16px;color:var(--text-secondary);">{body}</p>
        <div style="display:flex;gap:8px;justify-content:flex-end;">{buttons}</div>
    </div>
</div>
<script>
function openModal() {{ document.getElementById('modal-overlay').classList.add('active'); }}
function closeModal() {{ document.getElementById('modal-overlay').classList.remove('active'); }}
</script>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# DataFeed — Push real-time data to UI (layer status, metrics, logs)
# ═══════════════════════════════════════════════════════════════════════════════

class DataFeed:
    """Holds live data and formats it for SSE or polling consumers."""

    def __init__(self):
        self._lock = threading.Lock()
        self._metrics = {}
        self._logs = []
        self._layer_status = {}
        self._listeners = []

    def set_metric(self, key, value):
        with self._lock:
            self._metrics[key] = {"value": value, "ts": time.time()}

    def set_layer_status(self, layer, status, message=""):
        """status: green | yellow | red"""
        with self._lock:
            self._layer_status[layer] = {"status": status, "message": message, "ts": time.time()}

    def log(self, level, message, source="system"):
        entry = {"ts": time.time(), "level": level, "message": message, "source": source}
        with self._lock:
            self._logs.append(entry)
            if len(self._logs) > 500:
                self._logs = self._logs[-250:]

    def get_snapshot(self):
        with self._lock:
            return {
                "metrics": dict(self._metrics),
                "layers": dict(self._layer_status),
                "logs": list(self._logs[-50:]),
            }

    def format_sse(self, event_type="update", data=None):
        payload = json.dumps(data or self.get_snapshot())
        return f"event: {event_type}\ndata: {payload}\n\n"


# ═══════════════════════════════════════════════════════════════════════════════
# WebSocketHandler — Real-time WebSocket-like communication (SSE fallback)
# ═══════════════════════════════════════════════════════════════════════════════

class WebSocketHandler:
    """Server-Sent Events (SSE) fallback for real-time push."""

    def __init__(self, data_feed: DataFeed, interval=2):
        self.feed = data_feed
        self.interval = interval
        self._clients = []
        self._thread = None
        self._running = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _broadcast_loop(self):
        while self._running:
            snapshot = self.feed.get_snapshot()
            dead = []
            for q in self._clients:
                try:
                    q.put(self.feed.format_sse("update", snapshot))
                except Exception:
                    dead.append(q)
            for d in dead:
                self._clients.remove(d)
            time.sleep(self.interval)

    def register(self, queue):
        self._clients.append(queue)

    def handle_request(self, handler):
        """Called from HTTP request handler to stream SSE."""
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Cache-Control", "no-cache")
        handler.send_header("Connection", "keep-alive")
        handler.end_headers()

        import queue
        q = queue.Queue()
        self.register(q)
        try:
            while self._running:
                try:
                    chunk = q.get(timeout=5)
                    handler.wfile.write(chunk.encode())
                    handler.wfile.flush()
                except queue.Empty:
                    handler.wfile.write(b":heartbeat\n\n")
                    handler.wfile.flush()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# ComponentRegistry — Register UI components (panels, widgets, charts)
# ═══════════════════════════════════════════════════════════════════════════════

class ComponentRegistry:
    """Registry for panels, widgets, and charts."""

    def __init__(self):
        self._panels = {}
        self._widgets = {}
        self._charts = {}

    def register_panel(self, name, builder_fn):
        self._panels[name] = builder_fn

    def register_widget(self, name, render_fn):
        self._widgets[name] = render_fn

    def register_chart(self, name, config_fn):
        self._charts[name] = config_fn

    def get_panel(self, name):
        return self._panels.get(name)

    def list_panels(self):
        return list(self._panels.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# PanelBuilder — Build individual panels (trading, AI, security, etc.)
# ═══════════════════════════════════════════════════════════════════════════════

class PanelBuilder:
    """Builds 15+ panels for each MAGNATRIX-OS layer."""

    PANELS = [
        "Overview", "Trading", "AI Core", "Security", "Network",
        "Storage", "Compute", "Messaging", "Scheduler", "Analytics",
        "Logs", "Settings", "Health", "Alerts", "Wallet",
    ]

    def __init__(self, registry: ComponentRegistry, data_feed: DataFeed,
                 chart_renderer: ChartRenderer, form_builder: FormBuilder,
                 table_renderer: TableRenderer, modal_manager: ModalManager):
        self.registry = registry
        self.feed = data_feed
        self.chart = chart_renderer
        self.form = form_builder
        self.table = table_renderer
        self.modal = modal_manager
        self._register_defaults()

    def _register_defaults(self):
        for name in self.PANELS:
            self.registry.register_panel(name, lambda n=name: self._build_panel(n))

    def _build_panel(self, name: str) -> str:
        status = self.feed._layer_status.get(name.lower(), {"status": "green", "message": "Operational"})
        status_color = f"status-{status['status']}"
        chart_html = ""
        if name == "Overview":
            chart_cfg = self.chart.line(
                ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
                [{"label": "CPU", "data": [12, 19, 30, 25, 40, 35], "borderColor": "#00d4aa", "tension": 0.4}],
            )
            chart_html = self.chart.render_html(f"chart_{name.lower()}", chart_cfg)
        elif name == "Trading":
            chart_cfg = self.chart.bar(["BTC", "ETH", "XRP", "SOL"], [{"label": "Volume", "data": [45, 30, 20, 55], "backgroundColor": "#ffa502"}])
            chart_html = self.chart.render_html(f"chart_{name.lower()}", chart_cfg)
        elif name == "AI Core":
            chart_cfg = self.chart.pie(["Inference", "Training", "Idle"], [60, 25, 15])
            chart_html = self.chart.render_html(f"chart_{name.lower()}", chart_cfg)
        elif name == "Wallet":
            data = [{"Asset": "BTC", "Balance": 1.5, "USD": 45000}, {"Asset": "ETH", "Balance": 10, "USD": 25000}]
            chart_html = self.table.render(data, columns=["Asset", "Balance", "USD"])
        elif name == "Settings":
            chart_html = self.form.generate({
                "theme": {"type": "select", "label": "Theme", "options": ["dark", "light"]},
                "refresh": {"type": "int", "label": "Refresh Interval (s)", "placeholder": "2"},
                "api_key": {"type": "password", "label": "API Key", "placeholder": "sk-..."},
            })
        elif name == "Logs":
            logs = self.feed._logs[-20:]
            log_lines = "".join(
                f'<div class="log-entry"><span style="color:#888">{datetime.fromtimestamp(l["ts"]).strftime("%H:%M:%S")}</span> '
                f'<span style="color:{ {"info":"#00d4aa","warn":"#ffa502","error":"#ff4757"}.get(l["level"],"#e0e0e0") }">[{l["level"].upper()}]</span> {l["message"]}</div>'
                for l in logs
            )
            chart_html = f'<div class="log-viewer">{log_lines}</div>'
        elif name == "Alerts":
            chart_html = self.modal.confirm("Reset all alerts?", on_yes="console.log('reset')")

        return f"""
<div class="glass panel" id="panel-{name.lower().replace(' ', '-')}">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h4 style="font-size:14px;letter-spacing:0.5px;text-transform:uppercase;">{name}</h4>
        <span class="{status_color}" style="font-size:11px;font-weight:600;">● {status['status'].upper()}</span>
    </div>
    {chart_html}
</div>
"""

    def build_all(self) -> str:
        return "".join(self.registry.get_panel(p)() for p in self.registry.list_panels())


# ═══════════════════════════════════════════════════════════════════════════════
# RouteHandler — HTTP route handling for dashboard API endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class RouteHandler:
    """Simple router for dashboard API endpoints."""

    def __init__(self, data_feed: DataFeed, theme_manager: ThemeManager):
        self.feed = data_feed
        self.theme = theme_manager
        self._routes = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register("GET", "/api/status", self._api_status)
        self.register("GET", "/api/metrics", self._api_metrics)
        self.register("GET", "/api/logs", self._api_logs)
        self.register("POST", "/api/theme", self._api_theme)
        self.register("GET", "/api/export/json", self._api_export_json)
        self.register("GET", "/api/export/csv", self._api_export_csv)

    def register(self, method, path, handler):
        self._routes[(method, path)] = handler

    def dispatch(self, method, path, handler_obj):
        parsed = urlparse(path)
        key = (method, parsed.path)
        if key in self._routes:
            return self._routes[key](handler_obj, parse_qs(parsed.query))
        return None

    def _api_status(self, handler, qs):
        return {"status": "ok", "layers": self.feed._layer_status}

    def _api_metrics(self, handler, qs):
        return {"metrics": self.feed._metrics}

    def _api_logs(self, handler, qs):
        limit = int(qs.get("limit", [50])[0])
        return {"logs": self.feed._logs[-limit:]}

    def _api_theme(self, handler, qs):
        # In real usage, read POST body; here stub returns current
        return {"theme": self.theme.mode}

    def _api_export_json(self, handler, qs):
        return self.feed.get_snapshot()

    def _api_export_csv(self, handler, qs):
        lines = ["timestamp,level,source,message"]
        for l in self.feed._logs:
            lines.append(f'"{datetime.fromtimestamp(l["ts"]).isoformat()}",{l["level"]},{l["source"]},"{l["message"]}"')
        return {"csv": "\n".join(lines)}


# ═══════════════════════════════════════════════════════════════════════════════
# WebUIManager — Main UI orchestrator, generates and serves dashboard
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler wired back to WebUIManager."""

    manager = None

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/dashboard":
            self._serve_html(self.manager.generate_dashboard())
        elif path == "/sse":
            self.manager.ws_handler.handle_request(self)
        elif path == "/assets/style.css":
            self._serve_css(self.manager.theme.generate_css())
        elif path == "/assets/app.js":
            self._serve_js(self.manager.bundler.bundle_js())
        else:
            api = self.manager.router.dispatch("GET", self.path, self)
            if api is not None:
                self._serve_json(api)
            else:
                self.send_error(404)

    def do_POST(self):
        api = self.manager.router.dispatch("POST", self.path, self)
        if api is not None:
            self._serve_json(api)
        else:
            self.send_error(404)

    def _serve_html(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def _serve_css(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/css")
        self.end_headers()
        self.wfile.write(body.encode())

    def _serve_js(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript")
        self.end_headers()
        self.wfile.write(body.encode())

    def _serve_json(self, obj):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())


class WebUIManager:
    """Main orchestrator: generates and serves the MAGNATRIX-OS dashboard."""

    def __init__(self, host="0.0.0.0", port=7777, theme_mode="dark"):
        self.host = host
        self.port = port
        self.theme = ThemeManager(mode=theme_mode)
        self.bundler = AssetBundler()
        self.feed = DataFeed()
        self.ws_handler = WebSocketHandler(self.feed, interval=2)
        self.chart_renderer = ChartRenderer()
        self.form_builder = FormBuilder()
        self.table_renderer = TableRenderer(page_size=10)
        self.modal_manager = ModalManager()
        self.registry = ComponentRegistry()
        self.panel_builder = PanelBuilder(
            self.registry, self.feed, self.chart_renderer,
            self.form_builder, self.table_renderer, self.modal_manager,
        )
        self.router = RouteHandler(self.feed, self.theme)
        self._server = None
        self._server_thread = None
        self._build_js()

    def _build_js(self):
        self.bundler.add_js("""
// Auto-refresh with SSE fallback polling
let evtSource = null;
function connectSSE() {
    if (!!window.EventSource) {
        evtSource = new EventSource('/sse');
        evtSource.onmessage = (e) => {
            const data = JSON.parse(e.data);
            updateDashboard(data);
        };
    } else {
        setInterval(() => fetch('/api/status').then(r=>r.json()).then(updateDashboard), 5000);
    }
}
function updateDashboard(data) {
    if (data.layers) {
        for (const [layer, info] of Object.entries(data.layers)) {
            const el = document.querySelector(`#panel-${layer.toLowerCase().replace(/\\s+/g,'-')} .status-green, #panel-${layer.toLowerCase().replace(/\\s+/g,'-')} .status-yellow, #panel-${layer.toLowerCase().replace(/\\s+/g,'-')} .status-red`);
            if (el) { el.className = `status-${info.status}`; el.textContent = '● ' + info.status.toUpperCase(); }
        }
    }
}
// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.key === 'r' && e.ctrlKey) { e.preventDefault(); location.reload(); }
    if (e.key === 'Escape') { closeModal(); }
});
// Export helpers
function downloadJSON(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'});
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = filename; a.click();
}
function downloadCSV(csv, filename) {
    const blob = new Blob([csv], {type:'text/csv'});
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = filename; a.click();
}
connectSSE();
""")

    def generate_dashboard(self) -> str:
        panels = self.panel_builder.build_all()
        css = self.theme.generate_css()
        js = self.bundler.bundle_js()
        chart_cdn = self.chart_renderer.CHART_JS_CDN
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MAGNATRIX-OS Dashboard</title>
<link rel="stylesheet" href="/assets/style.css">
<script src="{chart_cdn}"></script>
</head>
<body>
    <div class="glass header">
        <div style="display:flex;align-items:center;gap:12px;">
            <div style="width:32px;height:32px;border-radius:8px;background:var(--accent);display:grid;place-items:center;font-weight:800;color:#fff;font-size:14px;">M</div>
            <h1 style="font-size:16px;letter-spacing:1px;">MAGNATRIX-OS</h1>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
            <span id="clock" style="color:var(--text-secondary);font-size:13px;"></span>
            <button class="btn" style="padding:6px 12px;font-size:12px;" onclick="downloadJSON({{layers:document.title}},'status.json')">Export JSON</button>
        </div>
    </div>
    <div class="grid-dashboard">
        {panels}
    </div>
    {self.modal_manager.alert("System initialized.", "Welcome")}
    <script>
        {js}
        setInterval(() => document.getElementById('clock').textContent = new Date().toLocaleTimeString(), 1000);
    </script>
</body>
</html>"""

    def start(self):
        DashboardHandler.manager = self
        self._server = HTTPServer((self.host, self.port), DashboardHandler)
        self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._server_thread.start()
        self.ws_handler.start()
        self.feed.log("info", f"Web UI listening on http://{self.host}:{self.port}", "web_ui")

    def stop(self):
        self.ws_handler.stop()
        if self._server:
            self._server.shutdown()

    def self_test(self):
        """Generate dashboard HTML and verify all panels present."""
        html = self.generate_dashboard()
        missing = []
        for name in self.panel_builder.PANELS:
            pid = f'panel-{name.lower().replace(" ", "-")}'
            if pid not in html:
                missing.append(name)
        ok = not missing
        return {"ok": ok, "missing_panels": missing, "html_length": len(html), "panels_found": len(self.panel_builder.PANELS) - len(missing)}


# ═══════════════════════════════════════════════════════════════════════════════
# Self-test entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    ui = WebUIManager(port=7777)
    result = ui.self_test()
    print(f"[Self-Test] Panels: {result['panels_found']}/{len(ui.panel_builder.PANELS)}")
    print(f"[Self-Test] HTML size: {result['html_length']} bytes")
    if result["ok"]:
        print("[Self-Test] All panels present. PASS")
        ui.start()
        print(f"[Self-Test] Server running. Open http://localhost:7777")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            ui.stop()
            print("[Self-Test] Server stopped.")
    else:
        print(f"[Self-Test] Missing panels: {result['missing_panels']}")
        sys.exit(1)
