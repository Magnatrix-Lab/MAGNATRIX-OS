"""
tests/integration/mock_suite.py
==============================
Mock layer instances untuk integration testing.
"""

import asyncio, json, time, uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

class MockKnowledge:
    def __init__(self):
        self.research = MockResearch()
        self.memory = MockMemory()

class MockResearch:
    async def research(self, topic: str, depth: int = 3):
        class FakeReport:
            def to_dict(self):
                return {"topic": topic, "sources": 5, "summary": f"Research on {topic}"}
        return FakeReport()

class MockMemory:
    async def store_episode(self, content: str, context: str = "", **kwargs):
        pass

class MockSkills:
    def __init__(self):
        self.factory = MockFactory()

class MockFactory:
    def generate_template(self, goal: str, **kwargs):
        class FakeSkill:
            name = f"skill-{goal[:10]}"
        return FakeSkill()

class MockTrading:
    def __init__(self):
        self.stock = MockStock()

class MockStock:
    def place_order(self, order):
        order.status = "filled"
        order.filled_price = 100.0
        return order

class MockSecurity:
    def __init__(self):
        self.pentest = MockPentest()

class MockPentest:
    def set_scope(self, targets):
        pass
    async def scan(self, target: str):
        return []
    async def generate_report(self):
        return {"findings": 0}

class MockGovernance:
    def __init__(self):
        self.governance = MockGov()

class MockGov:
    def check_compliance(self, agent_id: str, action: str, context: Dict):
        class FakeResult:
            value = "COMPLIANT"
        return FakeResult()

class MockRuntime:
    def __init__(self):
        self.flow = MockFlow()

class MockFlow:
    def create_flow(self, name: str):
        class FakeFlow:
            id = str(uuid.uuid4())[:8]
        return FakeFlow()
    def add_node(self, *args):
        pass
    def connect(self, *args):
        pass
    async def execute(self, *args):
        return {"flow_id": "mock", "results": {}}

class MockMesh:
    def __init__(self):
        self.dht = MockDHT()

class MockDHT:
    def __init__(self):
        self._store = {}
    def store(self, key: str, value: Any):
        self._store[key] = value
    def find_value(self, key: str):
        return self._store.get(key)

class MockPersistence:
    async def store(self, table: str, key: str, data: Dict):
        pass
    async def retrieve(self, table: str, key: str):
        return {"value": 42}

class MockSelfImprove:
    def __init__(self):
        self.engine = MockEvolver()

class MockEvolver:
    pass

class FitnessSuite:
    def __init__(self, tests=None):
        self.tests = tests or []

def create_mock_layers(orch):
    """Register mock layers untuk integration testing"""
    orch.register_layer("knowledge", MockKnowledge())
    orch.register_layer("skills", MockSkills())
    orch.register_layer("trading", MockTrading())
    orch.register_layer("security", MockSecurity())
    orch.register_layer("governance", MockGovernance())
    orch.register_layer("runtime", MockRuntime())
    orch.register_layer("mesh", MockMesh())
    orch.register_layer("persistence", MockPersistence())
    orch.register_layer("self_improve", MockSelfImprove())
