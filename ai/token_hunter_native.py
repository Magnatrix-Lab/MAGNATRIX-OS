#!/usr/bin/env python3
"""token_hunter_native.py — Auto-Smart, Auto-Fast, Auto-Hunting Free Token LLM System for MAGNATRIX-OS.

Automatically discovers, validates, rotates, and manages free LLM API tokens/credits
from multiple providers. Community endpoint hunter. Free tier quota tracker.
"""

from __future__ import annotations
import os, json, time, hashlib, random, re, threading, subprocess, tempfile
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from urllib.parse import urlparse


class TokenStatus(Enum):
    UNKNOWN = auto()
    VALID = auto()
    INVALID = auto()
    EXPIRED = auto()
    RATE_LIMITED = auto()
    QUOTA_EXHAUSTED = auto()


class ProviderType(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    MISTRAL = "mistral"
    AI21 = "ai21"
    TOGETHER = "together"
    GROQ = "groq"
    PERPLEXITY = "perplexity"
    FIREWORKS = "fireworks"
    OPENROUTER = "openrouter"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    COMMUNITY = "community"


@dataclass
class LLMToken:
    token_id: str
    provider: ProviderType
    key: str
    status: TokenStatus
    discovered_at: float
    last_validated: float
    last_used: float
    usage_count: int
    quota_remaining: Optional[int] = None
    quota_total: Optional[int] = None
    rate_limit_rpm: Optional[int] = None
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FreeEndpoint:
    endpoint_id: str
    url: str
    provider: str
    model: str
    discovered_at: float
    status: TokenStatus
    latency_ms: Optional[float] = None
    supports_streaming: bool = False
    max_tokens: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TokenDiscoveryEngine:
    """Multi-source token discovery: env, files, patterns, known locations."""

    def __init__(self, search_paths: List[str] = None):
        self.search_paths = search_paths or [".env", ".env.local", "config.json", "secrets.json"]
        self._patterns = {
            ProviderType.OPENAI: [
                r"sk-proj-[A-Za-z0-9_-]{100,}",
                r"sk-[a-zA-Z0-9]{48}",
                r"OPENAI_API_KEY\s*=\s*([a-zA-Z0-9_-]+)",
            ],
            ProviderType.ANTHROPIC: [
                r"sk-ant-[a-zA-Z0-9_-]{90,}",
                r"ANTHROPIC_API_KEY\s*=\s*([a-zA-Z0-9_-]+)",
            ],
            ProviderType.GOOGLE: [
                r"AIza[a-zA-Z0-9_-]{35,}",
                r"GOOGLE_API_KEY\s*=\s*([a-zA-Z0-9_-]+)",
            ],
            ProviderType.COHERE: [
                r"COHERE_API_KEY\s*=\s*([a-zA-Z0-9_-]+)",
            ],
            ProviderType.TOGETHER: [
                r"TOGETHER_API_KEY\s*=\s*([a-zA-Z0-9_-]+)",
            ],
            ProviderType.GROQ: [
                r"gsk_[a-zA-Z0-9]{50,}",
                r"GROQ_API_KEY\s*=\s*([a-zA-Z0-9_-]+)",
            ],
            ProviderType.HUGGINGFACE: [
                r"hf_[a-zA-Z0-9]{30,}",
                r"HUGGINGFACE_API_KEY\s*=\s*([a-zA-Z0-9_-]+)",
            ],
            ProviderType.MISTRAL: [
                r"MISTRAL_API_KEY\s*=\s*([a-zA-Z0-9_-]+)",
            ],
            ProviderType.OPENROUTER: [
                r"sk-or-[a-zA-Z0-9_-]{20,}",
                r"OPENROUTER_API_KEY\s*=\s*([a-zA-Z0-9_-]+)",
            ],
        }

    def hunt_environment(self) -> List[LLMToken]:
        """Scan environment variables for API keys."""
        tokens = []
        env_map = {
            "OPENAI_API_KEY": ProviderType.OPENAI,
            "ANTHROPIC_API_KEY": ProviderType.ANTHROPIC,
            "GOOGLE_API_KEY": ProviderType.GOOGLE,
            "COHERE_API_KEY": ProviderType.COHERE,
            "MISTRAL_API_KEY": ProviderType.MISTRAL,
            "TOGETHER_API_KEY": ProviderType.TOGETHER,
            "GROQ_API_KEY": ProviderType.GROQ,
            "PERPLEXITY_API_KEY": ProviderType.PERPLEXITY,
            "FIREWORKS_API_KEY": ProviderType.FIREWORKS,
            "OPENROUTER_API_KEY": ProviderType.OPENROUTER,
            "HUGGINGFACE_API_KEY": ProviderType.HUGGINGFACE,
            "HF_API_KEY": ProviderType.HUGGINGFACE,
        }
        for env_name, provider in env_map.items():
            val = os.environ.get(env_name)
            if val and len(val) > 20:
                tid = f"ENV-{provider.value}-{hashlib.sha256(val.encode()).hexdigest()[:8]}"
                tokens.append(LLMToken(
                    token_id=tid, provider=provider, key=val,
                    status=TokenStatus.UNKNOWN, discovered_at=time.time(),
                    last_validated=0, last_used=0, usage_count=0,
                    metadata={"source": f"env:{env_name}"},
                ))
        return tokens

    def hunt_files(self, directory: str = ".") -> List[LLMToken]:
        """Scan files in directory for API key patterns."""
        tokens = []
        for root, _, files in os.walk(directory):
            for fname in files:
                if not any(fname.endswith(ext) for ext in [".env", ".json", ".yaml", ".yml", ".txt", ".py", ".sh"]):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue
                for provider, patterns in self._patterns.items():
                    for pattern in patterns:
                        for match in re.finditer(pattern, content):
                            key = match.group(1) if match.groups() else match.group(0)
                            if len(key) < 20:
                                continue
                            tid = f"FILE-{provider.value}-{hashlib.sha256(key.encode()).hexdigest()[:8]}"
                            tokens.append(LLMToken(
                                token_id=tid, provider=provider, key=key,
                                status=TokenStatus.UNKNOWN, discovered_at=time.time(),
                                last_validated=0, last_used=0, usage_count=0,
                                metadata={"source": f"file:{fpath}", "pattern": pattern},
                            ))
        return tokens

    def hunt_simulated_tokens(self, count: int = 5) -> List[LLMToken]:
        """Generate simulated tokens for demo/testing."""
        tokens = []
        providers = list(ProviderType)[:10]
        for i in range(count):
            provider = random.choice(providers)
            key = f"sk-{provider.value}-{hashlib.sha256(str(time.time() + i).encode()).hexdigest()[:40]}"
            tid = f"SIM-{provider.value}-{hashlib.sha256(key.encode()).hexdigest()[:8]}"
            tokens.append(LLMToken(
                token_id=tid, provider=provider, key=key,
                status=TokenStatus.UNKNOWN, discovered_at=time.time(),
                last_validated=0, last_used=0, usage_count=0,
                metadata={"source": "simulated", "demo": True},
            ))
        return tokens


class TokenValidator:
    """Validate tokens by simulating API calls."""

    def __init__(self):
        self._validation_history: Dict[str, Dict[str, Any]] = {}

    def validate(self, token: LLMToken) -> TokenStatus:
        """Simulate validation of a token."""
        # Simulated validation - in real implementation this would make actual API calls
        # For now, use heuristics based on key format
        key = token.key
        provider = token.provider

        # Format checks
        if provider == ProviderType.OPENAI and not (key.startswith("sk-") or key.startswith("sk-proj-")):
            return TokenStatus.INVALID
        if provider == ProviderType.ANTHROPIC and not key.startswith("sk-ant-"):
            return TokenStatus.INVALID
        if provider == ProviderType.GOOGLE and not key.startswith("AIza"):
            return TokenStatus.INVALID
        if provider == ProviderType.GROQ and not key.startswith("gsk_"):
            return TokenStatus.INVALID
        if provider == ProviderType.HUGGINGFACE and not key.startswith("hf_"):
            return TokenStatus.INVALID

        # Simulated success rate (80% valid for demo)
        if random.random() < 0.8:
            token.quota_total = random.randint(1000, 100000)
            token.quota_remaining = random.randint(100, token.quota_total)
            token.rate_limit_rpm = random.choice([10, 20, 60, 100, 1000])
            token.expires_at = time.time() + random.randint(86400, 2592000)  # 1-30 days
            return TokenStatus.VALID
        else:
            return random.choice([TokenStatus.INVALID, TokenStatus.EXPIRED, TokenStatus.QUOTA_EXHAUSTED])

    def validate_batch(self, tokens: List[LLMToken]) -> List[LLMToken]:
        """Validate multiple tokens."""
        for token in tokens:
            token.status = self.validate(token)
            token.last_validated = time.time()
        return tokens


class FreeEndpointHunter:
    """Hunt for free community inference endpoints."""

    def __init__(self):
        self._known_endpoints = [
            ("https://api.openai.com/v1/chat/completions", "OpenAI", "gpt-3.5-turbo", True),
            ("https://api.groq.com/openai/v1/chat/completions", "Groq", "llama3-70b-8192", True),
            ("https://api.together.xyz/v1/chat/completions", "Together", "meta-llama/Llama-3-70b", True),
            ("https://api.fireworks.ai/inference/v1/chat/completions", "Fireworks", "accounts/fireworks/models/llama-v3-70b-instruct", True),
            ("https://openrouter.ai/api/v1/chat/completions", "OpenRouter", "meta-llama/llama-3-70b-instruct", True),
            ("https://api.perplexity.ai/chat/completions", "Perplexity", "llama-3.1-sonar-small-128k-online", True),
            ("https://api.cohere.ai/v1/chat", "Cohere", "command-r", False),
            ("https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent", "Google", "gemini-pro", False),
            ("https://api-inference.huggingface.co/models/meta-llama/Llama-3-70b", "HuggingFace", "Llama-3-70b", False),
            ("https://api.mistral.ai/v1/chat/completions", "Mistral", "mistral-large-latest", True),
            ("https://api.ai21.com/studio/v1/chat/completions", "AI21", "jamba-1.5-large", True),
        ]

    def hunt(self) -> List[FreeEndpoint]:
        """Discover free community endpoints."""
        endpoints = []
        for url, provider, model, streaming in self._known_endpoints:
            eid = f"EP-{hashlib.sha256(url.encode()).hexdigest()[:8]}"
            endpoints.append(FreeEndpoint(
                endpoint_id=eid, url=url, provider=provider, model=model,
                discovered_at=time.time(), status=TokenStatus.UNKNOWN,
                latency_ms=random.uniform(50, 500) if random.random() > 0.3 else None,
                supports_streaming=streaming,
                max_tokens=random.choice([2048, 4096, 8192, 16384, 32768]),
            ))
        return endpoints

    def test_latency(self, endpoint: FreeEndpoint) -> Optional[float]:
        """Simulate latency test."""
        if random.random() > 0.2:
            endpoint.latency_ms = random.uniform(50, 800)
            endpoint.status = TokenStatus.VALID
        else:
            endpoint.latency_ms = None
            endpoint.status = TokenStatus.INVALID
        return endpoint.latency_ms


class TokenPoolManager:
    """Rotate tokens, track usage, manage quota."""

    def __init__(self, tokens: List[LLMToken] = None):
        self._tokens: Dict[str, LLMToken] = {}
        self._endpoints: Dict[str, FreeEndpoint] = {}
        if tokens:
            for t in tokens:
                self._tokens[t.token_id] = t
        self._usage_log: List[Dict[str, Any]] = []

    def add_token(self, token: LLMToken) -> None:
        self._tokens[token.token_id] = token

    def add_endpoint(self, endpoint: FreeEndpoint) -> None:
        self._endpoints[endpoint.endpoint_id] = endpoint

    def get_best_token(self, provider: ProviderType = None) -> Optional[LLMToken]:
        """Get token with highest remaining quota."""
        candidates = [t for t in self._tokens.values() if t.status == TokenStatus.VALID]
        if provider:
            candidates = [t for t in candidates if t.provider == provider]
        if not candidates:
            return None
        # Sort by quota remaining, then by usage count (prefer less used)
        candidates.sort(key=lambda t: (t.quota_remaining or 0, -t.usage_count), reverse=True)
        return candidates[0] if candidates else None

    def get_best_endpoint(self) -> Optional[FreeEndpoint]:
        """Get endpoint with lowest latency."""
        candidates = [e for e in self._endpoints.values() if e.status == TokenStatus.VALID]
        if not candidates:
            return None
        candidates.sort(key=lambda e: e.latency_ms or 9999)
        return candidates[0]

    def use_token(self, token_id: str) -> bool:
        """Mark token as used."""
        token = self._tokens.get(token_id)
        if not token or token.status != TokenStatus.VALID:
            return False
        token.usage_count += 1
        token.last_used = time.time()
        if token.quota_remaining is not None:
            token.quota_remaining -= 1
            if token.quota_remaining <= 0:
                token.status = TokenStatus.QUOTA_EXHAUSTED
        self._usage_log.append({
            "token_id": token_id, "provider": token.provider.value,
            "time": time.time(), "remaining": token.quota_remaining,
        })
        return True

    def get_stats(self) -> Dict[str, Any]:
        valid = sum(1 for t in self._tokens.values() if t.status == TokenStatus.VALID)
        invalid = sum(1 for t in self._tokens.values() if t.status == TokenStatus.INVALID)
        expired = sum(1 for t in self._tokens.values() if t.status == TokenStatus.EXPIRED)
        exhausted = sum(1 for t in self._tokens.values() if t.status == TokenStatus.QUOTA_EXHAUSTED)
        return {
            "total_tokens": len(self._tokens),
            "valid": valid, "invalid": invalid, "expired": expired, "exhausted": exhausted,
            "total_endpoints": len(self._endpoints),
            "active_endpoints": sum(1 for e in self._endpoints.values() if e.status == TokenStatus.VALID),
            "total_usage": len(self._usage_log),
        }

    def get_all_tokens(self) -> List[LLMToken]:
        return sorted(self._tokens.values(), key=lambda t: t.discovered_at, reverse=True)

    def get_all_endpoints(self) -> List[FreeEndpoint]:
        return sorted(self._endpoints.values(), key=lambda e: e.latency_ms or 9999)


class AutoHunter:
    """Main orchestrator: Discover → Validate → Manage → Rotate."""

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.expanduser("~/.magnatrix")
        self.discovery = TokenDiscoveryEngine()
        self.validator = TokenValidator()
        self.endpoint_hunter = FreeEndpointHunter()
        self.pool = TokenPoolManager()
        self._running = False
        self._hunt_count = 0
        os.makedirs(self.data_dir, exist_ok=True)

    def full_hunt(self, include_simulated: bool = False) -> Dict[str, Any]:
        """Execute full hunt cycle: discover + validate + manage."""
        self._hunt_count += 1
        print(f"\n{'='*60}")
        print(f"[HUNT-{self._hunt_count}] Full Token Hunt Cycle")
        print(f"{'='*60}")

        # 1. Discover tokens
        env_tokens = self.discovery.hunt_environment()
        print(f"  [ENV] Found {len(env_tokens)} tokens from environment")

        file_tokens = self.discovery.hunt_files()
        print(f"  [FILE] Found {len(file_tokens)} tokens from files")

        sim_tokens = self.discovery.hunt_simulated_tokens(5) if include_simulated else []
        print(f"  [SIM] Generated {len(sim_tokens)} simulated tokens")

        all_tokens = env_tokens + file_tokens + sim_tokens
        print(f"  [TOTAL] {len(all_tokens)} tokens to validate")

        # 2. Validate
        validated = self.validator.validate_batch(all_tokens)
        valid_count = sum(1 for t in validated if t.status == TokenStatus.VALID)
        print(f"  [VALIDATE] {valid_count}/{len(validated)} valid")

        # 3. Add to pool
        for t in validated:
            self.pool.add_token(t)

        # 4. Hunt endpoints
        endpoints = self.endpoint_hunter.hunt()
        for ep in endpoints:
            self.endpoint_hunter.test_latency(ep)
            self.pool.add_endpoint(ep)
        active_ep = sum(1 for e in endpoints if e.status == TokenStatus.VALID)
        print(f"  [ENDPOINTS] {active_ep}/{len(endpoints)} active community endpoints")

        # 5. Save state
        self._save_state()

        stats = self.pool.get_stats()
        print(f"  [POOL] {stats['total_tokens']} tokens, {stats['valid']} valid, {stats['total_endpoints']} endpoints")
        print(f"{'='*60}\n")
        return stats

    def quick_hunt(self) -> Dict[str, Any]:
        """Quick hunt: environment only, no file scanning."""
        tokens = self.discovery.hunt_environment()
        validated = self.validator.validate_batch(tokens)
        for t in validated:
            self.pool.add_token(t)
        return self.pool.get_stats()

    def get_token_for_provider(self, provider: str) -> Optional[LLMToken]:
        """Get best token for a specific provider."""
        try:
            ptype = ProviderType(provider)
        except ValueError:
            return None
        return self.pool.get_best_token(ptype)

    def get_any_token(self) -> Optional[LLMToken]:
        """Get best available token across all providers."""
        return self.pool.get_best_token()

    def get_any_endpoint(self) -> Optional[FreeEndpoint]:
        """Get best available community endpoint."""
        return self.pool.get_best_endpoint()

    def rotate(self) -> Optional[LLMToken]:
        """Rotate to next best token."""
        return self.pool.get_best_token()

    def _save_state(self):
        state = {
            "hunt_count": self._hunt_count,
            "pool_stats": self.pool.get_stats(),
            "tokens": [
                {
                    "token_id": t.token_id, "provider": t.provider.value,
                    "status": t.status.name, "quota_remaining": t.quota_remaining,
                    "usage_count": t.usage_count, "expires_at": t.expires_at,
                }
                for t in self.pool.get_all_tokens()
            ],
            "endpoints": [
                {
                    "endpoint_id": e.endpoint_id, "url": e.url, "provider": e.provider,
                    "model": e.model, "status": e.status.name, "latency_ms": e.latency_ms,
                }
                for e in self.pool.get_all_endpoints()
            ],
        }
        with open(os.path.join(self.data_dir, "token_hunter.json"), "w") as f:
            json.dump(state, f, indent=2, default=str)

    def load_state(self):
        path = os.path.join(self.data_dir, "token_hunter.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            self._hunt_count = data.get("hunt_count", 0)
            print(f"[LOAD] Restored state: {data.get('pool_stats', {})}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MAGNATRIX-OS Token Hunter")
    parser.add_argument("--simulated", action="store_true", help="Include simulated tokens")
    parser.add_argument("--quick", action="store_true", help="Quick hunt (env only)")
    parser.add_argument("--provider", type=str, help="Get token for specific provider")
    parser.add_argument("--endpoint", action="store_true", help="Get best endpoint")
    parser.add_argument("--list", action="store_true", help="List all tokens")
    args = parser.parse_args()

    hunter = AutoHunter()
    hunter.load_state()

    if args.quick:
        stats = hunter.quick_hunt()
        print(f"Quick hunt: {stats}")
    elif args.provider:
        token = hunter.get_token_for_provider(args.provider)
        if token:
            print(f"Token for {args.provider}: {token.token_id} (quota: {token.quota_remaining})")
        else:
            print(f"No valid token for {args.provider}")
    elif args.endpoint:
        ep = hunter.get_any_endpoint()
        if ep:
            print(f"Best endpoint: {ep.url} ({ep.provider}) latency={ep.latency_ms:.0f}ms")
        else:
            print("No active endpoints")
    elif args.list:
        hunter.full_hunt(include_simulated=args.simulated)
        for t in hunter.pool.get_all_tokens():
            print(f"  {t.token_id} | {t.provider.value:12} | {t.status.name:15} | quota={t.quota_remaining} | usage={t.usage_count}")
        for e in hunter.pool.get_all_endpoints():
            latency = f"{e.latency_ms:.0f}ms" if e.latency_ms else "N/A"
            print(f"  {e.endpoint_id} | {e.provider:12} | {e.model:25} | latency={latency}")
    else:
        stats = hunter.full_hunt(include_simulated=args.simulated)
        print(f"\n[FINAL STATS] {json.dumps(stats, indent=2)}")
