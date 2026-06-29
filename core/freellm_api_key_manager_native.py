"""Free LLM API Key Manager -- Store, rotate, validate API keys."""
from dataclasses import dataclass
from pathlib import Path
import json, base64, hashlib

@dataclass
class ApiKeyEntry:
    key_id: str = ""
    provider_id: str = ""
    key_hash: str = ""
    key_prefix: str = ""
    key_suffix: str = ""
    created_at: float = 0.0
    last_used: float = 0.0
    usage_count: int = 0
    active: bool = True
    label: str = ""

class FreellmApiKeyManager:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._keys: dict[str, ApiKeyEntry] = {}
        self._keys_path = self.root / "freellm_api_keys.enc.json"
        self._persist_path = self.root / "freellm_key_registry.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._keys = {k: ApiKeyEntry(**v) for k, v in data.get("keys", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "keys": {k: v.__dict__ for k, v in self._keys.items()}
        }, indent=2))

    def _hash_key(self, key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def add_key(self, key_id: str, provider_id: str, key: str, label: str = "") -> ApiKeyEntry:
        import time
        entry = ApiKeyEntry(
            key_id=key_id, provider_id=provider_id,
            key_hash=self._hash_key(key),
            key_prefix=key[:4] if len(key) >= 4 else "",
            key_suffix=key[-4:] if len(key) >= 4 else "",
            created_at=time.time(), label=label
        )
        self._keys[key_id] = entry
        key_data = {}
        if self._keys_path.exists():
            key_data = json.loads(self._keys_path.read_text())
        key_data[key_id] = base64.b64encode(key.encode()).decode()
        self._keys_path.write_text(json.dumps(key_data, indent=2))
        self._save()
        return entry

    def get_key(self, key_id: str) -> str | None:
        if not self._keys_path.exists():
            return None
        key_data = json.loads(self._keys_path.read_text())
        encoded = key_data.get(key_id)
        if encoded:
            key = base64.b64decode(encoded).decode()
            entry = self._keys.get(key_id)
            if entry:
                import time
                entry.last_used = time.time()
                entry.usage_count += 1
                self._save()
            return key
        return None

    def deactivate(self, key_id: str) -> bool:
        entry = self._keys.get(key_id)
        if entry:
            entry.active = False
            self._save()
            return True
        return False

    def delete(self, key_id: str) -> bool:
        if key_id in self._keys:
            del self._keys[key_id]
            if self._keys_path.exists():
                key_data = json.loads(self._keys_path.read_text())
                key_data.pop(key_id, None)
                self._keys_path.write_text(json.dumps(key_data, indent=2))
            self._save()
            return True
        return False

    def list_by_provider(self, provider_id: str) -> list[ApiKeyEntry]:
        return [k for k in self._keys.values() if k.provider_id == provider_id and k.active]

    def to_dict(self) -> dict:
        return {"key_count": len(self._keys), "active": sum(1 for k in self._keys.values() if k.active)}

    def get_stats(self) -> dict:
        by_provider = {}
        for k in self._keys.values():
            by_provider[k.provider_id] = by_provider.get(k.provider_id, 0) + 1
        return {"total": len(self._keys), "active": sum(1 for k in self._keys.values() if k.active), "by_provider": by_provider}

__all__ = ["FreellmApiKeyManager", "ApiKeyEntry"]
