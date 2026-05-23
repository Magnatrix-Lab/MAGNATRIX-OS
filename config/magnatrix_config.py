#!/usr/bin/env python3
"""
MAGNATRIX-OS — Config Manager
Native Python, zero external dependencies.
Layer configuration, hot-reload, validation.
"""
from __future__ import annotations
import json, os, time, threading
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


@dataclass
class LayerConfig:
    enabled: bool = True
    timeout: float = 30.0
    retry: int = 3
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    feature_flags: Dict[str, bool] = field(default_factory=dict)


@dataclass
class SecurityConfig:
    encryption_key_path: str = ""
    jwt_secret: str = ""
    allowed_origins: List[str] = field(default_factory=list)
    rate_limit: Dict[str, Any] = field(default_factory=lambda: {"requests": 100, "window": 60})


@dataclass
class NetworkConfig:
    listen_host: str = "0.0.0.0"
    listen_port: int = 8080
    mesh_bootstrap: List[str] = field(default_factory=list)
    stun_servers: List[str] = field(default_factory=lambda: ["stun.l.google.com:19302"])
    turn_servers: List[str] = field(default_factory=list)


@dataclass
class DatabaseConfig:
    sqlite_path: str = "data/magnatrix.db"
    wal_mode: bool = True
    pool_size: int = 5
    migration_version: int = 1


@dataclass
class AIModelConfig:
    model_paths: Dict[str, str] = field(default_factory=dict)
    inference_threads: int = 4
    quantization: str = "none"
    context_window: int = 4096


class ConfigLoader:
    """Load config from JSON/YAML/ENV with priority: ENV > file > default."""

    def __init__(self, filepath: str = "config/magnatrix.json"):
        self.filepath = filepath
        self._data: Dict = {}

    def load(self) -> Dict:
        # Start with defaults
        config = self._default_config()
        # Override from file
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    file_config = json.load(f)
                self._deep_merge(config, file_config)
            except Exception:
                pass
        # Override from ENV
        env_prefix = "MAGNATRIX_"
        for key, val in os.environ.items():
            if key.startswith(env_prefix):
                path = key[len(env_prefix):].lower().split("__")
                self._set_nested(config, path, self._parse_env_value(val))
        self._data = config
        return config

    def _default_config(self) -> Dict:
        return {
            "layer_0_kernel": asdict(LayerConfig(timeout=30.0, resource_limits={"cpu": 0.1, "memory": 128}, feature_flags={"health_check": True, "auto_restart": True})),
            "layer_1_protocol": asdict(LayerConfig(timeout=5.0, feature_flags={"encryption": "aes256gcm", "handshake_timeout": 5})),
            "layer_1_5_api_router": asdict(LayerConfig(timeout=10.0, feature_flags={"rate_limit": 100, "jwt_expiry": 3600})),
            "layer_2_identity": asdict(LayerConfig(timeout=10.0, feature_flags={"key_rotation": 86400, "did_method": "magnatrix"})),
            "layer_3_runtime": asdict(LayerConfig(timeout=30.0, resource_limits={"max_agents": 100, "sandbox": True})),
            "layer_4_p2p_mesh": asdict(LayerConfig(timeout=15.0, feature_flags={"bootstrap": [], "stun": ["stun.l.google.com:19302"]})),
            "layer_5_knowledge": asdict(LayerConfig(timeout=20.0, feature_flags={"vector_dim": 768, "index_type": "hnsw"})),
            "layer_6_skills": asdict(LayerConfig(timeout=30.0, feature_flags={"max_skills": 500, "auto_update": True})),
            "layer_7_browser": asdict(LayerConfig(timeout=30.0, feature_flags={"headless": True, "timeout": 30})),
            "layer_8_hft": asdict(LayerConfig(timeout=5.0, feature_flags={"dry_run": True, "max_position_pct": 0.1})),
            "layer_9_security": asdict(LayerConfig(timeout=30.0, feature_flags={"scan_interval": 3600, "auto_patch": False})),
            "layer_10_uncensored_ai": asdict(LayerConfig(timeout=60.0, feature_flags={"temperature": 0.7, "max_tokens": 4096})),
            "layer_11_governance": asdict(LayerConfig(timeout=30.0, feature_flags={"proposal_quorum": 0.51, "voting_period": 86400})),
            "layer_12_ide": asdict(LayerConfig(timeout=30.0, feature_flags={"theme": "dark", "auto_save": True})),
            "layer_13_offensive": asdict(LayerConfig(timeout=60.0, feature_flags={"recon_passive_only": True, "scope": []})),
            "layer_13_5_repo_hunter": asdict(LayerConfig(timeout=3600.0, feature_flags={"scan_interval": 3600, "target_categories": ["ai", "security", "agent"]})),
            "security": asdict(SecurityConfig()),
            "network": asdict(NetworkConfig()),
            "database": asdict(DatabaseConfig()),
            "ai_model": asdict(AIModelConfig()),
        }

    def _deep_merge(self, base: Dict, override: Dict):
        for key, val in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(val, dict):
                self._deep_merge(base[key], val)
            else:
                base[key] = val

    def _set_nested(self, d: Dict, path: List[str], value: Any):
        for p in path[:-1]:
            d = d.setdefault(p, {})
        d[path[-1]] = value

    def _parse_env_value(self, val: str) -> Any:
        val = val.strip()
        if val.lower() in ("true", "yes", "1"):
            return True
        if val.lower() in ("false", "no", "0"):
            return False
        try:
            return int(val)
        except ValueError:
            pass
        try:
            return float(val)
        except ValueError:
            pass
        if val.startswith("[") and val.endswith("]"):
            try:
                return json.loads(val)
            except Exception:
                pass
        return val


class ConfigValidator:
    """Validate config completeness, dependency check, warn on missing."""

    REQUIRED_LAYERS = [f"layer_{i}" for i in range(14)]

    def validate(self, config: Dict) -> Dict[str, List[str]]:
        errors = []
        warnings = []
        for i in range(14):
            key = f"layer_{i}_kernel" if i == 0 else f"layer_{i}_{['protocol','api_router','identity','runtime','p2p_mesh','knowledge','skills','browser','hft','security','uncensored_ai','governance','ide','offensive','repo_hunter'][i-1]}"
            if key not in config:
                warnings.append(f"Missing config for {key}")
        if "security" not in config:
            errors.append("Missing security config")
        if "network" not in config:
            errors.append("Missing network config")
        return {"errors": errors, "warnings": warnings}


class ConfigManager:
    """Hot-reload, export, diff changes."""

    def __init__(self, filepath: str = "config/magnatrix.json"):
        self.filepath = filepath
        self.loader = ConfigLoader(filepath)
        self._config = self.loader.load()
        self._lock = threading.Lock()
        self._mtime = 0
        self._watch_thread: Optional[threading.Thread] = None
        self._running = False

    def get(self, path: str = "", default: Any = None) -> Any:
        with self._lock:
            d = self._config
            if not path:
                return d
            for p in path.split("."):
                if isinstance(d, dict) and p in d:
                    d = d[p]
                else:
                    return default
            return d

    def reload(self) -> bool:
        with self._lock:
            new_config = self.loader.load()
            self._config = new_config
            return True

    def export(self, path: str = None) -> str:
        path = path or self.filepath
        with self._lock:
            data = dict(self._config)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return path

    def diff(self, other: Dict) -> Dict[str, Any]:
        with self._lock:
            return self._compute_diff(self._config, other)

    def _compute_diff(self, a: Dict, b: Dict, path: str = "") -> Dict:
        diff = {}
        all_keys = set(a.keys()) | set(b.keys())
        for key in all_keys:
            p = f"{path}.{key}" if path else key
            if key not in a:
                diff[p] = {"status": "added", "value": b[key]}
            elif key not in b:
                diff[p] = {"status": "removed", "value": a[key]}
            elif isinstance(a[key], dict) and isinstance(b[key], dict):
                nested = self._compute_diff(a[key], b[key], p)
                diff.update(nested)
            elif a[key] != b[key]:
                diff[p] = {"status": "changed", "old": a[key], "new": b[key]}
        return diff

    def start_watch(self, interval: float = 5.0):
        self._running = True
        self._watch_thread = threading.Thread(target=self._watch_loop, args=(interval,), daemon=True)
        self._watch_thread.start()

    def _watch_loop(self, interval: float):
        while self._running:
            try:
                if os.path.exists(self.filepath):
                    mtime = os.path.getmtime(self.filepath)
                    if mtime > self._mtime:
                        self._mtime = mtime
                        self.reload()
            except Exception:
                pass
            time.sleep(interval)

    def stop_watch(self):
        self._running = False
        if self._watch_thread:
            self._watch_thread.join(timeout=2.0)


def run_demo():
    print("=" * 60)
    print("MAGNATRIX-OS Config Manager Demo")
    print("=" * 60)

    mgr = ConfigManager()
    print(f"\nLayer 0 (kernel) timeout: {mgr.get('layer_0_kernel.timeout')}s")
    print(f"Layer 8 (hft) dry_run: {mgr.get('layer_8_hft.feature_flags.dry_run')}")
    print(f"Security JWT expiry: {mgr.get('layer_1_5_api_router.feature_flags.jwt_expiry')}")
    print(f"Network STUN: {mgr.get('network.stun_servers')}")
    print(f"Database WAL: {mgr.get('database.wal_mode')}")

    validator = ConfigValidator()
    result = validator.validate(mgr.get())
    print(f"\nValidation: {len(result['errors'])} errors, {len(result['warnings'])} warnings")

    export_path = mgr.export("config/magnatrix_export.json")
    print(f"Exported to: {export_path}")

    print("\nDemo complete.")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
