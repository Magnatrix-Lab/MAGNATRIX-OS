#!/usr/bin/env python3
"""Trading Dashboard — HTTP Server + API"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8080

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/status":
            self._json({
                "status": "running", "mode": "paper",
                "positions": 2, "pnl": -28.0, "active_strategy": "ema_crossover",
                "win_rate": 0.33, "max_drawdown": 0.0359
            })
        elif self.path == "/api/trades":
            self._json([{"id": 1, "symbol": "BTC/USDT", "side": "BUY", "pnl": 12.5}])
        elif self.path == "/":
            self._html("""
            <!DOCTYPE html><html><head><style>
            body{font-family:sans-serif;background:#111;color:#0f0;padding:20px}
            table{border-collapse:collapse;width:100%}th,td{border:1px solid #333;padding:8px}
            th{background:#222}.green{color:#0f0}.red{color:#f00}
            </style></head><body>
            <h1>MAGNATRIX Trading Dashboard</h1>
            <table><tr><th>ID</th><th>Symbol</th><th>Side</th><th>PnL</th></tr>
            <tr><td>1</td><td>BTC/USDT</td><td>BUY</td><td class="green">+$12.50</td></tr>
            </table></body></html>
            """)
        else:
            self.send_error(404)

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, fmt, *args): pass

if __name__ == "__main__":
    print(f"Dashboard: http://localhost:{PORT}")
    HTTPServer(("", PORT), DashboardHandler).serve_forever()
