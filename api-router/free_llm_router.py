#!/usr/bin/env python3
"""
free_llm_router.py — MAGNATRIX Layer 1.5 Free LLM API Router
Integrasi FreeLLMAPI-style: aggregate ~11 free AI providers jadi satu
OpenAI-compatible endpoint dengan auto-failover, rate-limit tracking,
sticky sessions, dan usage analytics.

Providers supported:
  Google, Groq, Cerebras, SambaNova, Mistral, OpenRouter,
  GitHub Models, Cloudflare, Cohere, Z.ai (Zhipu), NVIDIA (disabled default)

Usage:
  python free_llm_router.py              # standalone test
  # atau import ke gateway_server.py untuk integrasi penuh
"""

import json
import os
import random
import re
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


class FreeLLMRouter:
    """
    OpenAI-compatible proxy router yang menggabungkan free-tier dari
    banyak AI provider. Auto-failover, sticky session, rate tracking.
    """

    PROVIDER_DEFAULTS: Dict[str, Dict[str, Any]] = {
        "google": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "models": [
                "gemini-2.5-flash-preview",
                "gemini-2.5-pro-preview",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
            ],
            "rpm_limit": 15,
            "rpd_limit": 1500,
            "tpm_limit": 1_000_000,
            "tpd_limit": 10_000_000,
            "priority": 1,
            "cost_per_1m_tokens": 0.0,
            "enabled": True,
        },
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "models": [
                "llama-3.3-70b-versatile",
                "llama-4-scout-17b-16e-instruct",
                "qwen-2.5-32b",
                "gemma2-9b-it",
                "deepseek-r1-distill-llama-70b",
            ],
            "rpm_limit": 30,
            "rpd_limit": 14_400,
            "tpm_limit": 6_000,
            "tpd_limit": 500_000,
            "priority": 2,
            "cost_per_1m_tokens": 0.0,
            "enabled": True,
        },
        "cerebras": {
            "base_url": "https://api.cerebras.ai/v1",
            "models": [
                "llama-3.3-70b",
                "llama-4-scout-17b-16e-instruct",
                "qwen3-235b-a22b",
            ],
            "rpm_limit": 60,
            "rpd_limit": 1_000,
            "tpm_limit": 60_000,
            "tpd_limit": 1_000_000,
            "priority": 3,
            "cost_per_1m_tokens": 0.0,
            "enabled": True,
        },
        "sambanova": {
            "base_url": "https://api.sambanova.ai/v1",
            "models": [
                "DeepSeek-V3-0324",
                "Meta-Llama-3.3-70B-Instruct",
                "Meta-Llama-4-Scout-17B-16E-Instruct",
                "Qwen2.5-72B-Instruct",
            ],
            "rpm_limit": 30,
            "rpd_limit": 1_000,
            "tpm_limit": 30_000,
            "tpd_limit": 500_000,
            "priority": 4,
            "cost_per_1m_tokens": 0.0,
            "enabled": True,
        },
        "mistral": {
            "base_url": "https://api.mistral.ai/v1",
            "models": [
                "mistral-large-2407",
                "mistral-medium-2312",
                "codestral-2405",
                "devstral-2501",
            ],
            "rpm_limit": 1,
            "rpd_limit": 500,
            "tpm_limit": 500_000,
            "tpd_limit": 1_000_000,
            "priority": 5,
            "cost_per_1m_tokens": 0.0,
            "enabled": True,
        },
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1",
            "models": [
                "cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
                "microsoft/mai-ds-r1:free",
                "nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
                "qwen/qwen3-30b-a3b:free",
                "google/gemma-3-27b-it:free",
            ],
            "rpm_limit": 20,
            "rpd_limit": 200,
            "tpm_limit": 200_000,
            "tpd_limit": 1_000_000,
            "priority": 6,
            "cost_per_1m_tokens": 0.0,
            "enabled": True,
        },
        "github_models": {
            "base_url": "https://models.github.ai/inference",
            "models": [
                "gpt-4.1",
                "gpt-4o",
                "o3-mini",
                "meta-llama/Llama-4-Scout-17B-16E-Instruct",
                "microsoft/Phi-4-multimodal-instruct",
            ],
            "rpm_limit": 10,
            "rpd_limit": 150,
            "tpm_limit": 50_000,
            "tpd_limit": 500_000,
            "priority": 7,
            "cost_per_1m_tokens": 0.0,
            "enabled": True,
        },
        "cloudflare": {
            "base_url": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
            "models": [
                "@cf/meta/llama-3.1-8b-instruct",
                "@cf/mistral/mistral-7b-instruct-v0.2",
                "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
            ],
            "rpm_limit": 60,
            "rpd_limit": 10_000,
            "tpm_limit": 100_000,
            "tpd_limit": 1_000_000,
            "priority": 8,
            "cost_per_1m_tokens": 0.0,
            "enabled": True,
            "needs_account_id": True,
        },
        "cohere": {
            "base_url": "https://api.cohere.com/compatibility/v1",
            "models": [
                "command-r-plus",
                "command-a-03-2025",
                "command-r",
            ],
            "rpm_limit": 10,
            "rpd_limit": 1_000,
            "tpm_limit": 100_000,
            "tpd_limit": 1_000_000,
            "priority": 9,
            "cost_per_1m_tokens": 0.0,
            "enabled": True,
        },
        "zai": {
            "base_url": "https://api.z.ai/v1",
            "models": [
                "glm-4.5",
                "glm-4.7-flash",
                "glm-4-flash",
            ],
            "rpm_limit": 60,
            "rpd_limit": 10_000,
            "tpm_limit": 500_000,
            "tpd_limit": 5_000_000,
            "priority": 10,
            "cost_per_1m_tokens": 0.0,
            "enabled": True,
        },
        "nvidia": {
            "base_url": "https://integrate.api.nvidia.com/v1",
            "models": [
                "nvidia/llama-3.1-nemotron-70b-instruct",
                "nvidia/llama-3.3-nemotron-super-49b-v1",
                "meta/llama-3.1-8b-instruct",
            ],
            "rpm_limit": 60,
            "rpd_limit": 1_000,
            "tpm_limit": 60_000,
            "tpd_limit": 1_000_000,
            "priority": 11,
            "cost_per_1m_tokens": 0.0,
            "enabled": False,
        },
    }

    FALLBACK_ATTEMPTS = 20
    SESSION_TTL_SECONDS = 1800
    COOLDOWN_SECONDS = 60

    def __init__(self, fallback_attempts: int = 20):
        self.fallback_attempts = fallback_attempts
        self.providers: Dict[str, Dict[str, Any]] = {}
        self.keys: Dict[str, str] = {}
        self.usage: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "requests": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "errors": 0,
                "last_error": None,
                "last_used": None,
                "rpm_window": [],
                "rpd_window": [],
            }
        )
        self.sessions: Dict[str, Tuple[str, str, float]] = {}
        self._load_from_env()
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Environment loading
    # ------------------------------------------------------------------
    def _load_from_env(self) -> None:
        """Load API keys dari environment variables."""
        key_map = {
            "google": "GOOGLE_API_KEY",
            "groq": "GROQ_API_KEY",
            "cerebras": "CEREBRAS_API_KEY",
            "sambanova": "SAMBANOVA_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "github_models": "GITHUB_TOKEN",
            "cloudflare": "CF_API_TOKEN",
            "cohere": "COHERE_API_KEY",
            "zai": "ZAI_API_KEY",
            "nvidia": "NVIDIA_API_KEY",
        }
        for provider, env_var in key_map.items():
            val = os.environ.get(env_var)
            if val:
                self.keys[provider] = val
                self.providers[provider] = dict(self.PROVIDER_DEFAULTS[provider])
                self.providers[provider]["key"] = val
            else:
                # tetap masukkan provider tapi nonaktif jika key tidak ada
                cfg = dict(self.PROVIDER_DEFAULTS[provider])
                cfg["enabled"] = False
                cfg["key"] = None
                self.providers[provider] = cfg

        # Cloudflare account id
        self.cf_account_id = os.environ.get("CF_ACCOUNT_ID", "")
        if "cloudflare" in self.providers and self.cf_account_id:
            base = self.providers["cloudflare"]["base_url"]
            self.providers["cloudflare"]["base_url"] = base.replace(
                "{account_id}", self.cf_account_id
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _now(self) -> float:
        return time.time()

    def _check_rate_limits(self, provider: str) -> Tuple[bool, str]:
        """Cek apakah provider masih di bawah rate limit."""
        cfg = self.providers.get(provider)
        if not cfg or not cfg.get("enabled") or not cfg.get("key"):
            return False, "disabled or no key"

        u = self.usage[provider]
        now = self._now()

        # RPM
        rpm_window = [t for t in u["rpm_window"] if now - t < 60]
        u["rpm_window"] = rpm_window
        if len(rpm_window) >= cfg["rpm_limit"]:
            return False, f"RPM limit {cfg['rpm_limit']} reached"

        # RPD
        rpd_window = [t for t in u["rpd_window"] if now - t < 86400]
        u["rpd_window"] = rpd_window
        if len(rpd_window) >= cfg["rpd_limit"]:
            return False, f"RPD limit {cfg['rpd_limit']} reached"

        return True, "ok"

    def _record_request(self, provider: str, tokens_in: int = 0, tokens_out: int = 0, error: Optional[str] = None) -> None:
        """Catat penggunaan request ke provider."""
        with self._lock:
            u = self.usage[provider]
            u["requests"] += 1
            u["tokens_in"] += tokens_in
            u["tokens_out"] += tokens_out
            u["last_used"] = datetime.now(timezone.utc).isoformat()
            u["rpm_window"].append(self._now())
            u["rpd_window"].append(self._now())
            if error:
                u["errors"] += 1
                u["last_error"] = error

    def _get_session_model(self, session_id: Optional[str], requested_model: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Sticky session: kembalikan provider+model yang sama untuk session_id dalam 30 menit."""
        if not session_id:
            return None, None
        with self._lock:
            if session_id in self.sessions:
                prov, mod, ts = self.sessions[session_id]
                if self._now() - ts < self.SESSION_TTL_SECONDS:
                    ok, reason = self._check_rate_limits(prov)
                    if ok:
                        return prov, mod
            return None, None

    def _set_session_model(self, session_id: Optional[str], provider: str, model: str) -> None:
        if session_id:
            with self._lock:
                self.sessions[session_id] = (provider, model, self._now())

    def _rank_providers(self, requested_model: Optional[str] = None) -> List[str]:
        """Ranking provider berdasarkan priority dan health."""
        candidates = []
        for name, cfg in self.providers.items():
            if not cfg.get("enabled") or not cfg.get("key"):
                continue
            ok, reason = self._check_rate_limits(name)
            if not ok:
                continue
            # model match jika requested_model diberikan
            if requested_model and requested_model not in cfg.get("models", []):
                # fallback: cek partial match
                if not any(requested_model in m for m in cfg.get("models", [])):
                    continue
            candidates.append((name, cfg["priority"]))

        candidates.sort(key=lambda x: x[1])
        return [c[0] for c in candidates]

    def _select_provider(self, requested_model: Optional[str] = None, session_id: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Pilih provider+model terbaik untuk request."""
        # sticky session dulu
        prov, mod = self._get_session_model(session_id, requested_model)
        if prov:
            return prov, mod

        ranked = self._rank_providers(requested_model)
        if not ranked:
            return None, None

        # pilih provider pertama yang healthy
        chosen = ranked[0]
        cfg = self.providers[chosen]
        # pilih model: requested_model jika ada dan match, else default model pertama
        models = cfg.get("models", [])
        model = models[0] if models else "unknown"
        if requested_model:
            for m in models:
                if requested_model == m or requested_model in m:
                    model = m
                    break

        return chosen, model

    def _build_url(self, provider: str) -> str:
        """Build full URL untuk chat completions endpoint."""
        base = self.providers[provider]["base_url"].rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/chat/completions"

    def _build_headers(self, provider: str) -> Dict[str, str]:
        """Build request headers."""
        key = self.providers[provider]["key"]
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://magnatrix-os.local"
            headers["X-Title"] = "MAGNATRIX OS"
        if provider == "github_models":
            headers["Accept"] = "application/vnd.github+json"
        return headers

    def _make_request(self, provider: str, model: str, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 1024, stream: bool = False, tools: Optional[List[Dict]] = None, **extra) -> Tuple[bool, Dict[str, Any]]:
        """Kirim HTTP request ke provider dan kembalikan (success, response_dict)."""
        url = self._build_url(provider)
        headers = self._build_headers(provider)
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
        if extra:
            for k, v in extra.items():
                if k not in payload:
                    payload[k] = v

        try:
            import urllib.request
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                return True, data
        except Exception as e:
            return False, {"error": str(e), "provider": provider}



    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def chat_completions(self, messages: List[Dict[str, str]], model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1024, stream: bool = False, tools: Optional[List[Dict]] = None, session_id: Optional[str] = None, **extra) -> Dict[str, Any]:
        """
        OpenAI-compatible chat completions dengan auto-failover.
        Mencoba hingga FALLBACK_ATTEMPTS provider sebelum menyerah.
        """
        request_id = f"req-{int(time.time() * 1000)}-{random.randint(1000, 9999)}"
        start_ts = self._now()
        last_error: Optional[str] = None
        attempted: List[str] = []

        for attempt in range(self.fallback_attempts):
            prov, mod = self._select_provider(model, session_id)
            if not prov:
                break

            attempted.append(prov)
            success, result = self._make_request(
                prov, mod, messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                tools=tools,
                **extra
            )

            if success and "error" not in result:
                latency = round(self._now() - start_ts, 3)
                # hitung tokens rough estimation
                tokens_in = sum(len(m.get("content", "").split()) for m in messages)
                tokens_out = 0
                try:
                    if "usage" in result and result["usage"]:
                        tokens_out = result["usage"].get("completion_tokens", 0)
                        tokens_in = result["usage"].get("prompt_tokens", tokens_in)
                    else:
                        # rough estimation dari content
                        for choice in result.get("choices", []):
                            msg = choice.get("message", {})
                            tokens_out += len(msg.get("content", "").split())
                except Exception:
                    pass

                self._record_request(prov, tokens_in, tokens_out)
                self._set_session_model(session_id, prov, mod)

                # tambahkan metadata magnatrix
                result["magnatrix_meta"] = {
                    "request_id": request_id,
                    "provider": prov,
                    "model": mod,
                    "latency_seconds": latency,
                    "attempt": attempt + 1,
                    "fallback_used": attempt > 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                return result

            # gagal → cooldown provider ini, coba next
            last_error = result.get("error", "unknown error")
            self._record_request(prov, error=last_error)
            # cooldown singkat agar tidak langsung retry ke provider yang sama
            time.sleep(min(0.5 * attempt, 3.0))

        # semua provider habis
        latency = round(self._now() - start_ts, 3)
        return {
            "id": request_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model or "fallback-exhausted",
            "choices": [],
            "error": {
                "message": f"All {len(attempted)} providers exhausted after {self.fallback_attempts} attempts. Last error: {last_error}",
                "type": "router_error",
                "attempted_providers": attempted,
            },
            "magnatrix_meta": {
                "request_id": request_id,
                "latency_seconds": latency,
                "attempted": len(attempted),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    def get_models(self) -> List[Dict[str, str]]:
        """Kembalikan list semua model yang tersedia dari semua provider aktif."""
        models = []
        for name, cfg in self.providers.items():
            if not cfg.get("enabled") or not cfg.get("key"):
                continue
            for m in cfg.get("models", []):
                models.append({
                    "id": m,
                    "object": "model",
                    "owned_by": name,
                })
        return models

    def get_usage_report(self) -> Dict[str, Any]:
        """Laporan penggunaan dan estimasi penghematan biaya."""
        total_requests = 0
        total_tokens = 0
        total_errors = 0
        per_provider = {}

        for name, cfg in self.providers.items():
            u = self.usage[name]
            req_count = u["requests"]
            tok_count = u["tokens_in"] + u["tokens_out"]
            err_count = u["errors"]
            total_requests += req_count
            total_tokens += tok_count
            total_errors += err_count

            # estimasi biaya jika pakai paid tier (asumsi $0.50 per 1M tokens rata-rata)
            market_cost_per_1m = 0.50
            saved = round((tok_count / 1_000_000) * market_cost_per_1m, 4)

            per_provider[name] = {
                "enabled": cfg.get("enabled", False),
                "requests": req_count,
                "tokens_in": u["tokens_in"],
                "tokens_out": u["tokens_out"],
                "errors": err_count,
                "last_error": u["last_error"],
                "last_used": u["last_used"],
                "estimated_cost_saved_usd": saved,
                "rpm_window_len": len(u["rpm_window"]),
                "rpd_window_len": len(u["rpd_window"]),
            }

        # total estimasi penghematan
        total_saved = round((total_tokens / 1_000_000) * 0.50, 4)
        return {
            "summary": {
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "total_errors": total_errors,
                "active_providers": sum(1 for p in self.providers.values() if p.get("enabled")),
                "configured_providers": len(self.providers),
                "estimated_cost_saved_usd": total_saved,
                "free_tier_capacity_per_month_tokens": 1_300_000_000,
            },
            "per_provider": per_provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_health(self) -> Dict[str, Any]:
        """Health check semua provider."""
        health = {}
        for name, cfg in self.providers.items():
            ok, reason = self._check_rate_limits(name)
            health[name] = {
                "enabled": cfg.get("enabled", False),
                "has_key": bool(cfg.get("key")),
                "healthy": ok,
                "reason": reason if not ok else "healthy",
                "priority": cfg.get("priority"),
                "models_count": len(cfg.get("models", [])),
            }
        return {
            "overall": "healthy" if any(h["healthy"] for h in health.values()) else "degraded",
            "providers": health,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def export_openai_format(self) -> Dict[str, Any]:
        """Export /v1/models dalam format OpenAI."""
        models = self.get_models()
        return {
            "object": "list",
            "data": models,
        }

    # ------------------------------------------------------------------
    # HTTP server wrapper (built-in, no external deps)
    # ------------------------------------------------------------------
    def run_server(self, host: str = "0.0.0.0", port: int = 3001):
        """Jalankan built-in HTTP server yang OpenAI-compatible."""
        from http.server import BaseHTTPRequestHandler, HTTPServer

        router = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def _send_json(self, data, status=200):
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data, default=str).encode())

            def do_GET(self):
                if self.path == "/v1/models":
                    self._send_json(router.export_openai_format())
                elif self.path == "/health":
                    self._send_json(router.get_health())
                elif self.path == "/usage":
                    self._send_json(router.get_usage_report())
                else:
                    self._send_json({"error": "Not found", "status": 404}, 404)

            def do_POST(self):
                if self.path == "/v1/chat/completions":
                    content_length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_length)
                    try:
                        data = json.loads(body.decode()) if body else {}
                    except json.JSONDecodeError:
                        self._send_json({"error": "Invalid JSON"}, 400)
                        return

                    # extract session dari Authorization header atau body
                    auth = self.headers.get("Authorization", "")
                    session_id = None
                    if auth.startswith("Bearer "):
                        session_id = auth.split(" ", 1)[1]

                    result = router.chat_completions(
                        messages=data.get("messages", []),
                        model=data.get("model"),
                        temperature=data.get("temperature", 0.7),
                        max_tokens=data.get("max_tokens", 1024),
                        stream=data.get("stream", False),
                        tools=data.get("tools"),
                        session_id=session_id,
                    )
                    status = 200 if "error" not in result else 503
                    self._send_json(result, status)
                else:
                    self._send_json({"error": "Not found", "status": 404}, 404)

            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                self.end_headers()

        server = HTTPServer((host, port), Handler)
        print(f"[FreeLLM Router] OpenAI-compatible server running on http://{host}:{port}")
        print("  GET  /v1/models        → list available models")
        print("  GET  /health           → provider health check")
        print("  GET  /usage            → usage report + cost savings")
        print("  POST /v1/chat/completions → chat with auto-failover")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[FreeLLM Router] Server stopped")


# ===================================================================
# Standalone Demo
# ===================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX Free LLM Router — Standalone Test")
    print("=" * 60)

    router = FreeLLMRouter()

    # tampilkan health check
    print("\n[1] Health Check:")
    health = router.get_health()
    for prov, status in health["providers"].items():
        icon = "🟢" if status["healthy"] else "🔴"
        print(f"  {icon} {prov:20s} — {status['reason']}")

    # tampilkan models
    print("\n[2] Available Models:")
    models = router.get_models()
    for m in models[:10]:
        print(f"  • {m['id']} ({m['owned_by']})")
    if len(models) > 10:
        print(f"  ... dan {len(models) - 10} model lainnya")

    # tampilkan usage report (awal kosong)
    print("\n[3] Usage Report:")
    report = router.get_usage_report()
    print(f"  Active providers : {report['summary']['active_providers']}")
    print(f"  Free capacity    : ~{report['summary']['free_tier_capacity_per_month_tokens'] / 1e9:.1f}B tokens/bulan")

    # jika tidak ada provider aktif, tampilkan instruksi
    if report["summary"]["active_providers"] == 0:
        print("\n[!] Tidak ada provider yang aktif. Set API key di environment:")
        print("    export GOOGLE_API_KEY=xxx")
        print("    export GROQ_API_KEY=xxx")
        print("    export OPENROUTER_API_KEY=xxx")
        print("    ... (lihat .env.example untuk daftar lengkap)")
        print("\nMenjalankan server tanpa provider aktif (akan return error)...")

    # jalankan server jika arg --server diberikan
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        router.run_server()
    else:
        print("\n[4] Gunakan 'python free_llm_router.py --server' untuk menjalankan HTTP server")
        print("[5] Atau import ke gateway_server.py untuk integrasi penuh ke MAGNATRIX API Gateway")

    print("\n" + "=" * 60)
    print("FreeLLM Router ready.")
    print("=" * 60)
