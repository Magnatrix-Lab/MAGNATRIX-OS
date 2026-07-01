#!/usr/bin/env python3
"""llm_gateway_native.py — MAGNATRIX-OS Unified LLM Provider Abstraction"""
from __future__ import annotations
import json, random, threading, time, urllib.error, urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

@dataclass
class LLMProvider:
    name: str; base_url: str; api_key: str; model_map: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=lambda:{"Content-Type":"application/json"})
    timeout: float = 30.0; cost_per_1k: float = 0.0; speed_score: float = 5.0
    quality_score: float = 5.0; enabled: bool = True; last_error: float = 0.0
    error_count: int = 0; max_errors: int = 5; cooldown: float = 60.0

@dataclass
class LLMRequest:
    model: str; messages: List[Dict[str, str]]; temperature: float = 0.7
    max_tokens: int = 1024; top_p: float = 1.0; stream: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LLMResponse:
    text: str; model: str; provider: str; usage: Dict[str, int] = field(default_factory=dict)
    latency: float = 0.0; finish_reason: str = "stop"; raw: Optional[Dict[str, Any]] = None

class LLMGatewayNative:
    def __init__(self, workspace: str = "./llm_gateway") -> None:
        self.workspace = Path(workspace); self.workspace.mkdir(parents=True, exist_ok=True)
        self._providers: Dict[str, LLMProvider] = {}; self._lock = threading.RLock()
        self._config_path = self.workspace / "providers.json"; self._load()

    def _load(self) -> None:
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, pd in data.items(): self._providers[name] = LLMProvider(**pd)
            except Exception: pass

    def _save(self) -> None:
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump({name: asdict(p) for name, p in self._providers.items()}, f, indent=2, default=str)

    def register_provider(self, name, base_url, api_key, model_map=None, headers=None, cost_per_1k=0.0, speed_score=5.0, quality_score=5.0, timeout=30.0):
        with self._lock:
            self._providers[name] = LLMProvider(name=name, base_url=base_url.rstrip("/"), api_key=api_key, model_map=model_map or {}, headers=headers or {"Content-Type":"application/json"}, cost_per_1k=cost_per_1k, speed_score=speed_score, quality_score=quality_score, timeout=timeout)
            self._save()

    def remove_provider(self, name: str) -> bool:
        with self._lock:
            if name in self._providers: del self._providers[name]; self._save(); return True
            return False

    def list_providers(self) -> List[str]:
        with self._lock: return [n for n, p in self._providers.items() if p.enabled]

    def _is_available(self, provider: LLMProvider) -> bool:
        if not provider.enabled: return False
        if provider.error_count >= provider.max_errors:
            if time.time() - provider.last_error < provider.cooldown: return False
            provider.error_count = 0
        return True

    def _select_provider(self, model, priority="balanced", preferred=None):
        with self._lock:
            candidates = []
            for name, prov in self._providers.items():
                if not self._is_available(prov): continue
                supported = [model] + list(prov.model_map.keys())
                if model not in supported and not prov.model_map: continue
                candidates.append(prov)
            if not candidates: return None
            if preferred:
                pref = [p for p in candidates if p.name in preferred]
                if pref: candidates = pref
            if priority == "cost": candidates.sort(key=lambda p: p.cost_per_1k)
            elif priority == "speed": candidates.sort(key=lambda p: -p.speed_score)
            elif priority == "quality": candidates.sort(key=lambda p: -p.quality_score)
            else:
                random.shuffle(candidates)
                candidates.sort(key=lambda p: (p.quality_score + p.speed_score) / (1 + p.cost_per_1k), reverse=True)
            return candidates[0] if candidates else None

    def _normalize_request(self, req: LLMRequest, provider: LLMProvider):
        mapped = provider.model_map.get(req.model, req.model)
        payload = {"model": mapped, "messages": req.messages, "temperature": req.temperature, "max_tokens": req.max_tokens, "top_p": req.top_p, "stream": req.stream}
        if "anthropic" in provider.base_url.lower() or "claude" in provider.name.lower():
            payload = {"model": mapped, "messages": req.messages, "max_tokens": req.max_tokens, "temperature": req.temperature, "top_p": req.top_p, "stream": req.stream}
        return payload

    def _parse_response(self, raw: Dict[str, Any], provider: LLMProvider):
        text = ""
        if "choices" in raw: text = raw["choices"][0].get("message", {}).get("content", "")
        elif "content" in raw:
            if isinstance(raw["content"], list): text = "".join(b.get("text", "") for b in raw["content"] if b.get("type") == "text")
            else: text = raw["content"]
        elif "candidates" in raw: text = raw["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
        usage = raw.get("usage", {})
        if isinstance(usage, dict): usage = {"prompt_tokens": usage.get("prompt_tokens", 0), "completion_tokens": usage.get("completion_tokens", 0), "total_tokens": usage.get("total_tokens", 0)}
        return LLMResponse(text=text, model=raw.get("model", "unknown"), provider=provider.name, usage=usage, finish_reason=raw.get("choices", [{}])[0].get("finish_reason", "stop") if "choices" in raw else "stop", raw=raw)

    def _http_post(self, url, payload, headers, timeout):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def chat(self, model, messages, temperature=0.7, max_tokens=1024, top_p=1.0, priority="balanced", preferred=None, max_retries=3):
        req = LLMRequest(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, top_p=top_p)
        last_error = None
        for attempt in range(max_retries):
            provider = self._select_provider(model, priority=priority, preferred=preferred)
            if provider is None: raise RuntimeError("No available LLM providers for model: " + model)
            start = time.time()
            try:
                payload = self._normalize_request(req, provider)
                headers = dict(provider.headers); headers["Authorization"] = f"Bearer {provider.api_key}"
                url = f"{provider.base_url}/v1/chat/completions"
                raw = self._http_post(url, payload, headers, provider.timeout)
                resp = self._parse_response(raw, provider); resp.latency = time.time() - start
                return resp
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                last_error = e
                with self._lock: provider.error_count += 1; provider.last_error = time.time(); self._save()
                time.sleep(1.0 * (attempt + 1)); continue
            except Exception as e: last_error = e; break
        raise RuntimeError(f"LLM request failed after {max_retries} attempts: {last_error}")

    def quick_chat(self, model, prompt, **kwargs): return self.chat(model=model, messages=[{"role": "user", "content": prompt}], **kwargs).text

    def health_check(self):
        with self._lock:
            return {name: {"enabled": p.enabled, "available": self._is_available(p), "errors": p.error_count, "last_error": p.last_error, "cost": p.cost_per_1k, "speed": p.speed_score, "quality": p.quality_score} for name, p in self._providers.items()}

if __name__ == "__main__":
    gw = LLMGatewayNative()
    print("LLM Gateway initialized. Providers:", gw.list_providers())
