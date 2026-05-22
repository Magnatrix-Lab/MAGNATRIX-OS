#!/usr/bin/env python3
"""
gateway_server.py — MAGNATRIX API Gateway
REST API server untuk semua MAGNATRIX services.
Implements OpenAPI spec dengan endpoints untuk swarm, trading, knowledge, governance, browser, chat, evolution, dan free LLM routing.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any

# Import FreeLLM Router jika tersedia
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api-router"))
    from free_llm_router import FreeLLMRouter
    _LLM_ROUTER_AVAILABLE = True
except Exception:
    FreeLLMRouter = None  # type: ignore
    _LLM_ROUTER_AVAILABLE = False


class APIGatewayServer:
    """Simple API Gateway untuk MAGNATRIX (bisa diganti dengan FastAPI/Flask di production)."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.start_time = time.time()
        self.routes = {
            "GET /health": self._health,
            "GET /api/v2/status": self._status,
            "GET /api/v2/swarm/nodes": self._swarm_nodes,
            "POST /api/v2/swarm/spawn": self._swarm_spawn,
            "GET /api/v2/trading/status": self._trading_status,
            "POST /api/v2/trading/execute": self._trading_execute,
            "POST /api/v2/knowledge/query": self._knowledge_query,
            "GET /api/v2/governance/constitution": self._governance_constitution,
            "GET /api/v2/governance/goals": self._governance_goals,
            "POST /api/v2/browser/capture": self._browser_capture,
            "POST /api/v2/chat/send": self._chat_send,
            "POST /api/v2/evolve/trigger": self._evolve_trigger,
            # Free LLM Router endpoints
            "POST /api/v2/llm/chat": self._llm_chat,
            "GET /api/v2/llm/models": self._llm_models,
            "GET /api/v2/llm/health": self._llm_health,
        }
        # Simulated state
        self.swarm_nodes = []
        self.trading_nav = 1000000.0
        self.knowledge_entities = {}
        self.captured_data = []
        # Initialize LLM router
        self.llm_router = FreeLLMRouter() if _LLM_ROUTER_AVAILABLE else None

    def _health(self, body: Any = None) -> Dict:
        uptime = time.time() - self.start_time
        return {
            "status": "healthy",
            "uptime_seconds": int(uptime),
            "version": "2.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _status(self, body: Any = None) -> Dict:
        llm_status = "active" if self.llm_router else "disabled"
        return {
            "layers": [
                {"layer": 0, "name": "kernel", "status": "active"},
                {"layer": 0.5, "name": "collective-brain", "status": "active"},
                {"layer": 1, "name": "protocol", "status": "active"},
                {"layer": 1.5, "name": "api-router", "status": llm_status},
                {"layer": 4, "name": "p2p-mesh", "status": "active", "nodes": len(self.swarm_nodes)},
                {"layer": 5, "name": "knowledge", "status": "active", "entities": len(self.knowledge_entities)},
                {"layer": 8, "name": "trading", "status": "active", "nav": self.trading_nav},
                {"layer": 10, "name": "uncensored", "status": "active"},
                {"layer": 11, "name": "governance", "status": "active"},
            ],
            "emergency_mode": False,
            "cycle_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _swarm_nodes(self, body: Any = None) -> list:
        return self.swarm_nodes or [
            {"node_id": "hermes-1", "type": "hermes", "health": 0.95, "load": 0.4},
            {"node_id": "kimi-1", "type": "kimi-claw", "health": 0.92, "load": 0.5},
        ]

    def _swarm_spawn(self, body: Dict) -> Dict:
        brain_type = body.get("brain_type", "generic")
        count = body.get("count", 1)
        spawned = []
        for i in range(count):
            node_id = f"{brain_type}-{len(self.swarm_nodes) + i + 1}"
            self.swarm_nodes.append({
                "node_id": node_id,
                "type": brain_type,
                "health": 1.0,
                "load": 0.0
            })
            spawned.append(node_id)
        return {"spawned": count, "node_ids": spawned}

    def _trading_status(self, body: Any = None) -> Dict:
        return {
            "mode": "demo",
            "nav": self.trading_nav,
            "positions": 2,
            "daily_pnl": 150.0,
            "reinvestment_rate": 0.30
        }

    def _trading_execute(self, body: Dict) -> Dict:
        symbol = body.get("symbol", "UNKNOWN")
        side = body.get("side", "buy")
        amount = body.get("amount", 0)
        if side == "buy":
            self.trading_nav -= amount * 100
        else:
            self.trading_nav += amount * 100
        return {
            "status": "executed",
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "new_nav": self.trading_nav
        }

    def _knowledge_query(self, body: Dict) -> Dict:
        entity = body.get("entity", "unknown")
        depth = body.get("depth", 2)
        return {
            "entity": entity,
            "depth": depth,
            "related": [f"{entity}_concept_{i}" for i in range(3)],
            "paths": [[entity, f"{entity}_rel", f"{entity}_target"]]
        }

    def _governance_constitution(self, body: Any = None) -> Dict:
        return {
            "rules": [
                {"id": "safety_first", "text": "Never execute destructive commands without explicit human confirmation.", "weight": 0.95},
                {"id": "resource_fairness", "text": "No node may monopolize >30% of swarm resources.", "weight": 0.90},
                {"id": "transparency", "text": "Log every significant action with reasoning.", "weight": 0.70},
                {"id": "user_autonomy", "text": "Respect user decisions even when suboptimal.", "weight": 0.80},
            ]
        }

    def _governance_goals(self, body: Any = None) -> Dict:
        return {
            "active_goals": [
                {"id": "goal-1", "title": "Optimize memory utilization", "priority": 0.85, "status": "validated"},
                {"id": "goal-2", "title": "Diagnose recent task failure spike", "priority": 0.90, "status": "executing"},
            ]
        }

    def _browser_capture(self, body: Dict) -> Dict:
        self.captured_data.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": body
        })
        return {"status": "captured", "total_captured": len(self.captured_data)}

    def _chat_send(self, body: Dict) -> Dict:
        return {
            "status": "sent",
            "message": body.get("message", ""),
            "channel": body.get("channel", "general")
        }

    def _evolve_trigger(self, body: Any = None) -> Dict:
        return {
            "cycle_id": f"evolve-{int(time.time())}",
            "status": "triggered",
            "improvements": ["swarm_optimization", "knowledge_expansion"]
        }

    # ------------------------------------------------------------------
    # Free LLM Router handlers
    # ------------------------------------------------------------------
    def _llm_chat(self, body: Dict) -> Dict:
        if not self.llm_router:
            return {"error": "FreeLLM Router not available. Set provider API keys in .env", "status": "503"}
        messages = body.get("messages", [])
        if not messages:
            return {"error": "messages array required", "status": "400"}
        return self.llm_router.chat_completions(
            messages=messages,
            model=body.get("model"),
            temperature=body.get("temperature", 0.7),
            max_tokens=body.get("max_tokens", 1024),
            stream=body.get("stream", False),
            tools=body.get("tools"),
            session_id=body.get("session_id"),
        )

    def _llm_models(self, body: Any = None) -> Dict:
        if not self.llm_router:
            return {"error": "FreeLLM Router not available", "status": "503"}
        return self.llm_router.export_openai_format()

    def _llm_health(self, body: Any = None) -> Dict:
        if not self.llm_router:
            return {"error": "FreeLLM Router not available", "status": "503"}
        return self.llm_router.get_health()

    def handle_request(self, method: str, path: str, body: Any = None) -> Dict:
        """Handle incoming API request."""
        route_key = f"{method} {path}"
        if route_key in self.routes:
            try:
                return self.routes[route_key](body)
            except Exception as e:
                return {"error": str(e), "status": "error"}
        return {"error": "Not found", "status": "404"}


def run_server():
    """Run the API Gateway server using built-in HTTP server."""
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import urllib.parse

    gateway = APIGatewayServer()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Suppress default logging

        def _send_json(self, data, status=200):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, default=str).encode())

        def do_GET(self):
            result = gateway.handle_request("GET", self.path)
            self._send_json(result)

        def do_POST(self):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode()) if body else None
            except json.JSONDecodeError:
                data = None
            result = gateway.handle_request("POST", self.path, data)
            self._send_json(result)

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

    server = HTTPServer((gateway.host, gateway.port), Handler)
    print(f"[MAGNATRIX API] Gateway running on http://{gateway.host}:{gateway.port}")
    print("  Endpoints:")
    for route in gateway.routes:
        print(f"    {route}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[MAGNATRIX API] Server stopped")


if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX API Gateway Server")
    print("=" * 60)
    run_server()
