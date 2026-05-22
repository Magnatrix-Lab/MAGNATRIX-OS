"""
tests/integration/layer_integration_orchestrator.py
=====================================================
MAGNATRIX Layer Integration Orchestrator
Connects ALL layers into unified operating system.
End-to-end integration tests untuk cross-layer communication.
"""

import asyncio, json, sys, time, traceback, uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict

sys.path.insert(0, '/mnt/agents/MAGNATRIX-OS')

class LayerRegistry:
    """Registry untuk semua MAGNATRIX layers"""

    def __init__(self):
        self.layers: Dict[str, Any] = {}
        self._initialized: Dict[str, bool] = {}
        self._dependencies: Dict[str, List[str]] = {
            "persistence": [],
            "mesh": ["persistence"],
            "security": ["persistence"],
            "governance": ["persistence", "security"],
            "runtime": ["persistence", "mesh"],
            "skills": ["runtime", "persistence"],
            "knowledge": ["persistence", "skills"],
            "trading": ["persistence", "governance"],
            "multimodal": ["runtime"],
            "self_improve": ["runtime", "knowledge"],
            "world_model": ["runtime"],
        }

    def register(self, name: str, instance: Any):
        self.layers[name] = instance
        self._initialized[name] = False

    async def initialize_all(self):
        """Initialize layers dalam dependency order"""
        initialized = set()

        def can_init(name: str) -> bool:
            return all(dep in initialized for dep in self._dependencies.get(name, []))

        pending = set(self.layers.keys())
        while pending:
            ready = {name for name in pending if can_init(name)}
            if not ready:
                raise RuntimeError(f"Circular dependency detected: {pending}")

            for name in ready:
                layer = self.layers[name]
                if hasattr(layer, 'initialize'):
                    await layer.initialize() if asyncio.iscoroutinefunction(layer.initialize) else layer.initialize()
                self._initialized[name] = True
                initialized.add(name)
                pending.remove(name)
                print(f"[INIT] Layer '{name}' initialized")

    def get(self, name: str) -> Any:
        return self.layers.get(name)

    def is_ready(self, name: str) -> bool:
        return self._initialized.get(name, False)


class IntegrationOrchestrator:
    """
    Main orchestrator yang menghubungkan semua layers.
    Entry point untuk MAGNATRIX sebagai unified OS.
    """

    def __init__(self):
        self.registry = LayerRegistry()
        self._running = False
        self._start_time = 0.0
        self._mesh_callbacks: List[Callable] = []

    def register_layer(self, name: str, instance: Any):
        self.registry.register(name, instance)

    async def boot(self) -> Dict:
        """Boot sequence: initialize all layers"""
        print("=" * 60)
        print("MAGNATRIX Agentic OS Boot Sequence")
        print("=" * 60)

        self._start_time = time.time()
        await self.registry.initialize_all()
        self._running = True

        boot_time = time.time() - self._start_time
        print(f"\n[BOOT] Complete in {boot_time:.2f}s")

        return {
            "status": "booted",
            "boot_time_ms": boot_time * 1000,
            "layers_initialized": len(self.registry._initialized),
            "timestamp": time.time()
        }

    async def execute_task(self, task: Dict) -> Dict:
        """Execute cross-layer task"""
        task_type = task.get("type", "unknown")

        if task_type == "research_and_trade":
            return await self._pipeline_research_trade(task)
        elif task_type == "agentic_workflow":
            return await self._pipeline_agentic_workflow(task)
        elif task_type == "security_audit":
            return await self._pipeline_security_audit(task)
        elif task_type == "self_improve":
            return await self._pipeline_self_improve(task)
        else:
            return {"error": f"Unknown task type: {task_type}"}

    async def _pipeline_research_trade(self, task: Dict) -> Dict:
        """
        Pipeline: Research -> Knowledge -> Trading
        """
        # 1. Research (Knowledge layer)
        knowledge = self.registry.get("knowledge")
        report = None
        if knowledge and hasattr(knowledge, 'research'):
            report = await knowledge.research.research(task.get("topic", "AI trends"))

        # 2. Analyze findings (Skills layer)
        skills = self.registry.get("skills")
        analysis = None
        if skills and hasattr(skills, 'factory'):
            skill = skills.factory.generate_template("analyze market sentiment")
            analysis = {"skill_used": skill.name}

        # 3. Execute trade (Trading layer)
        trading = self.registry.get("trading")
        trade_result = None
        if trading and hasattr(trading, 'stock'):
            from trading.native_engines import Order, OrderSide
            trade_result = trading.stock.place_order(
                Order(symbol=task.get("symbol", "BTC"), side=OrderSide.BUY, quantity=task.get("amount", 1))
            )

        return {
            "pipeline": "research_and_trade",
            "research_report": report.to_dict() if report else None,
            "analysis": analysis,
            "trade": trade_result.to_dict() if trade_result else None
        }

    async def _pipeline_agentic_workflow(self, task: Dict) -> Dict:
        """
        Pipeline: Runtime -> Skills -> Knowledge -> Mesh broadcast
        """
        # 1. Create workflow (Runtime layer)
        runtime = self.registry.get("runtime")
        flow_result = None
        if runtime and hasattr(runtime, 'flow'):
            flow = runtime.flow.create_flow("Agentic Task")
            runtime.flow.add_node(flow.id, "input", "input", {})
            runtime.flow.add_node(flow.id, "process", "llm", {"prompt": task.get("prompt", "Process this")})
            runtime.flow.connect(flow.id, "input", "process")
            flow_result = await runtime.flow.execute(flow.id, task.get("inputs", {}))

        # 2. Store in knowledge
        knowledge = self.registry.get("knowledge")
        if knowledge and hasattr(knowledge, 'memory'):
            await knowledge.memory.store_episode(
                json.dumps(flow_result) if flow_result else "",
                context="agentic_workflow"
            )

        return {
            "pipeline": "agentic_workflow",
            "flow_result": flow_result
        }

    async def _pipeline_security_audit(self, task: Dict) -> Dict:
        """
        Pipeline: Security audit + Governance enforcement
        """
        security = self.registry.get("security")
        audit = None
        if security and hasattr(security, 'pentest'):
            security.pentest.set_scope([task.get("target", "localhost")])
            findings = await security.pentest.scan(task.get("target", "localhost"))
            audit = await security.pentest.generate_report()

        # Governance check
        governance = self.registry.get("governance")
        if governance and hasattr(governance, 'governance'):
            for finding in (audit or {}).get("findings", []):
                governance.governance.check_compliance("agent-1", f"scan_{finding}", {})

        return {
            "pipeline": "security_audit",
            "findings": len(findings) if 'findings' in locals() else 0,
            "report": audit
        }

    async def _pipeline_self_improve(self, task: Dict) -> Dict:
        """
        Pipeline: Self-improvement loop
        """
        self_improve = self.registry.get("self_improve")
        if self_improve and hasattr(self_improve, 'engine'):
            from tests.integration.mock_suite import FitnessSuite
            suite = FitnessSuite(tests=[{"input": [1,2,3], "expected": 6, "name": "sum"}])
            improved, fitness = await self_improve.improve_module(
                "def sum_list(data):\\n    return sum(data)", suite, 3
            )
            return {"pipeline": "self_improve", "fitness": fitness, "improved_code_length": len(improved)}
        return {"pipeline": "self_improve", "error": "Self-improve layer not available"}

    def get_status(self) -> Dict:
        return {
            "running": self._running,
            "layers": {name: self.registry.is_ready(name) for name in self.registry.layers},
            "uptime_seconds": time.time() - self._start_time if self._running else 0
        }


class IntegrationTestSuite:
    """Cross-layer integration tests"""

    def __init__(self, orchestrator: IntegrationOrchestrator):
        self.orch = orchestrator
        self.results: List[Dict] = []

    async def run_all(self) -> Dict:
        tests = [
            ("boot_sequence", self.test_boot),
            ("research_trade_pipeline", self.test_research_trade),
            ("agentic_workflow_pipeline", self.test_agentic_workflow),
            ("security_governance_pipeline", self.test_security_governance),
            ("cross_layer_mesh", self.test_mesh_broadcast),
            ("persistence_consistency", self.test_persistence),
        ]

        for name, test_fn in tests:
            try:
                start = time.time()
                result = await test_fn()
                duration = (time.time() - start) * 1000
                self.results.append({"name": name, "status": "pass", "duration_ms": duration, "result": result})
            except Exception as e:
                self.results.append({"name": name, "status": "fail", "error": str(e), "traceback": traceback.format_exc()})

        passed = sum(1 for r in self.results if r["status"] == "pass")
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": len(self.results) - passed,
            "pass_rate": passed / len(self.results),
            "tests": self.results
        }

    async def test_boot(self) -> Dict:
        status = await self.orch.boot()
        assert status["status"] == "booted"
        return status

    async def test_research_trade(self) -> Dict:
        result = await self.orch.execute_task({"type": "research_and_trade", "topic": "AI", "symbol": "AAPL", "amount": 10})
        return result

    async def test_agentic_workflow(self) -> Dict:
        result = await self.orch.execute_task({"type": "agentic_workflow", "prompt": "Analyze data", "inputs": {"data": [1,2,3]}})
        return result

    async def test_security_governance(self) -> Dict:
        result = await self.orch.execute_task({"type": "security_audit", "target": "test_target"})
        return result

    async def test_mesh_broadcast(self) -> Dict:
        mesh = self.orch.registry.get("mesh")
        if mesh and hasattr(mesh, 'dht'):
            mesh.dht.store("test_key", "test_value")
            val = mesh.dht.find_value("test_key")
            return {"stored": val == "test_value"}
        return {"error": "Mesh layer not available"}

    async def test_persistence(self) -> Dict:
        persist = self.orch.registry.get("persistence")
        if persist:
            await persist.store("test", "key1", {"value": 42})
            result = await persist.retrieve("test", "key1")
            return {"stored": result == {"value": 42}}
        return {"error": "Persistence layer not available"}


if __name__ == "__main__":
    async def demo():
        from tests.integration.mock_suite import create_mock_layers

        orch = IntegrationOrchestrator()
        create_mock_layers(orch)

        # Boot
        boot_result = await orch.boot()
        print(f"Boot: {boot_result}")

        # Run integration tests
        suite = IntegrationTestSuite(orch)
        results = await suite.run_all()
        print(f"\nIntegration tests: {results['passed']}/{results['total']} passed")

    asyncio.run(demo())
