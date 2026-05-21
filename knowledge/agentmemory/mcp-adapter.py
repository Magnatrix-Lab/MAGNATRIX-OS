#!/usr/bin/env python3
"""agentmemory MCP Adapter — Persistent Memory for MAGNATRIX"""

import json
import os

class AgentMemoryAdapter:
    def __init__(self, db_path="knowledge/memory.json"):
        self.db_path = db_path
        self.memory = self._load()

    def _load(self):
        if os.path.exists(self.db_path):
            with open(self.db_path) as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.db_path, "w") as f:
            json.dump(self.memory, f, indent=2)

    def store(self, brain, key, value):
        if brain not in self.memory:
            self.memory[brain] = {}
        self.memory[brain][key] = {"value": value, "timestamp": "2026-05-21"}
        self._save()
        return {"status": "stored", "brain": brain, "key": key}

    def query(self, brain, key):
        result = self.memory.get(brain, {}).get(key, {})
        return {"status": "found" if result else "not_found", "data": result}

if __name__ == "__main__":
    mem = AgentMemoryAdapter()
    mem.store("HERMES", "magnatrix_project", "Agentic OS for super AI")
    print(mem.query("HERMES", "magnatrix_project"))
    print(mem.query("HERMES", "unknown"))
