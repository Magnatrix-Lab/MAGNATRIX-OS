#!/usr/bin/env python3
"""
MAGNATRIX-OS — Layer 6: Hermes Skill Engine
Native Python, zero external dependencies.
Based on NousResearch/hermes-agent (149.5k stars) — AMATI-PELAJARI-TIRU pattern.
Self-improving AI agent with closed learning loop.
"""
from __future__ import annotations
import json, hashlib, threading, time, random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum


class SkillStatus(Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    BETA = "beta"
    ARCHIVED = "archived"


@dataclass
class Skill:
    name: str
    description: str
    code_blocks: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0
    success_rate: float = 0.0
    version: int = 1
    dependencies: List[str] = field(default_factory=list)
    status: SkillStatus = SkillStatus.BETA

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "code_blocks": self.code_blocks,
            "tags": self.tags,
            "created_at": self.created_at,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "version": self.version,
            "dependencies": self.dependencies,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Skill":
        s = cls(
            name=d["name"],
            description=d["description"],
            code_blocks=d.get("code_blocks", []),
            tags=d.get("tags", []),
            created_at=d.get("created_at", time.time()),
            usage_count=d.get("usage_count", 0),
            success_rate=d.get("success_rate", 0.0),
            version=d.get("version", 1),
            dependencies=d.get("dependencies", []),
        )
        s.status = SkillStatus(d.get("status", "beta"))
        return s


class SkillRegistry:
    """Register, load, delete, search, dependency graph, version control."""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._lock = threading.RLock()
        self._tag_index: Dict[str, Set[str]] = {}

    def register(self, skill: Skill) -> bool:
        with self._lock:
            if skill.name in self._skills:
                # Version increment on update
                existing = self._skills[skill.name]
                skill.version = existing.version + 1
            self._skills[skill.name] = skill
            for tag in skill.tags:
                self._tag_index.setdefault(tag, set()).add(skill.name)
            return True

    def get(self, name: str) -> Optional[Skill]:
        with self._lock:
            return self._skills.get(name)

    def delete(self, name: str) -> bool:
        with self._lock:
            if name not in self._skills:
                return False
            skill = self._skills.pop(name)
            for tag in skill.tags:
                self._tag_index.get(tag, set()).discard(name)
            return True

    def search(self, query: str = "", tags: List[str] = None) -> List[Skill]:
        with self._lock:
            results = []
            for skill in self._skills.values():
                if query and query.lower() not in skill.name.lower() and query.lower() not in skill.description.lower():
                    continue
                if tags and not all(t in skill.tags for t in tags):
                    continue
                results.append(skill)
            return sorted(results, key=lambda s: s.success_rate, reverse=True)

    def dependency_graph(self, name: str) -> List[str]:
        """Return transitive dependency list."""
        with self._lock:
            visited = set()
            stack = [name]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                skill = self._skills.get(current)
                if skill:
                    stack.extend(skill.dependencies)
            return list(visited - {name})

    def list_all(self) -> List[Skill]:
        with self._lock:
            return list(self._skills.values())


class SkillExtractor:
    """Extract reusable pattern from execution log."""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self._pattern_cache: List[Dict] = []
        self._lock = threading.Lock()

    def observe_execution(self, input_data: str, output_data: str, success: bool, skill_name: str = ""):
        with self._lock:
            self._pattern_cache.append({
                "input": input_data[:200],
                "output": output_data[:200],
                "success": success,
                "skill": skill_name,
                "timestamp": time.time(),
            })

    def extract_skills(self, min_success_count: int = 3) -> List[Skill]:
        with self._lock:
            # Group by similar input patterns
            groups: Dict[str, List[Dict]] = {}
            for entry in self._pattern_cache:
                key = entry["skill"] or hashlib.md5(entry["input"].encode()).hexdigest()[:8]
                groups.setdefault(key, []).append(entry)

            new_skills = []
            for key, entries in groups.items():
                successes = [e for e in entries if e["success"]]
                if len(successes) >= min_success_count:
                    # Create skill from repeated success pattern
                    skill = Skill(
                        name=f"auto_skill_{key}_{int(time.time())}",
                        description=f"Auto-extracted skill from {len(successes)} successes",
                        code_blocks=[f"# Pattern: {e['input'][:50]} -> {e['output'][:50]}" for e in successes[:5]],
                        tags=["auto-extracted", key],
                        success_rate=len(successes) / len(entries),
                    )
                    new_skills.append(skill)
            return new_skills


class SkillExecutor:
    """Execute skill with parameter binding, sandboxed, rollback."""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self._execution_log: List[Dict] = []
        self._lock = threading.Lock()

    def execute(self, skill_name: str, params: Dict = None, timeout: float = 30.0) -> Dict:
        skill = self.registry.get(skill_name)
        if not skill:
            return {"status": "error", "error": f"Skill {skill_name} not found"}

        start = time.time()
        try:
            # Sandbox: only allow whitelisted operations
            result = self._run_sandboxed(skill, params or {})
            elapsed = time.time() - start

            with self._lock:
                self._execution_log.append({
                    "skill": skill_name,
                    "params": params,
                    "result": result,
                    "elapsed": elapsed,
                    "success": result.get("status") == "success",
                    "timestamp": time.time(),
                })

            # Update skill stats
            skill.usage_count += 1
            total_success = sum(1 for e in self._execution_log if e["skill"] == skill_name and e["success"])
            total = sum(1 for e in self._execution_log if e["skill"] == skill_name)
            skill.success_rate = total_success / total if total > 0 else 0.0

            return result

        except Exception as e:
            return {"status": "error", "error": str(e), "skill": skill_name}

    def _run_sandboxed(self, skill: Skill, params: Dict) -> Dict:
        # Stub: simulate execution
        if random.random() < 0.1:  # 10% failure rate for demo
            raise Exception("Simulated execution failure")
        return {
            "status": "success",
            "skill": skill.name,
            "params": params,
            "output": f"Executed {skill.name} with {len(params)} params",
        }

    def get_log(self, skill_name: str = "") -> List[Dict]:
        with self._lock:
            if skill_name:
                return [e for e in self._execution_log if e["skill"] == skill_name]
            return self._execution_log[:]


class MemoryManager:
    """Three-layer memory: Session + PersistentFacts + ProceduralSkills."""

    def __init__(self):
        self._session: Dict[str, Any] = {}
        self._facts: Dict[str, Any] = {}
        self._skills_memory: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def session_set(self, key: str, value: Any):
        with self._lock:
            self._session[key] = value

    def session_get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._session.get(key, default)

    def fact_set(self, key: str, value: Any, confidence: float = 1.0):
        with self._lock:
            self._facts[key] = {"value": value, "confidence": confidence, "updated": time.time()}

    def fact_get(self, key: str) -> Optional[Dict]:
        with self._lock:
            return self._facts.get(key)

    def skill_memory_set(self, skill_name: str, key: str, value: Any):
        with self._lock:
            self._skills_memory.setdefault(skill_name, {})[key] = value

    def skill_memory_get(self, skill_name: str, key: str) -> Any:
        with self._lock:
            return self._skills_memory.get(skill_name, {}).get(key)


class ReflectiveEngine:
    """Nightly/scheduled review — analyze execution journal, suggest improvements."""

    def __init__(self, executor: SkillExecutor, registry: SkillRegistry, extractor: SkillExtractor):
        self.executor = executor
        self.registry = registry
        self.extractor = extractor

    def review(self) -> Dict:
        log = self.executor.get_log()
        if not log:
            return {"status": "no_data"}

        # Analyze failures
        failures = [e for e in log if not e["success"]]
        success_rate = sum(1 for e in log if e["success"]) / len(log)

        # Suggest improvements
        suggestions = []
        for failure in failures:
            suggestions.append({
                "skill": failure["skill"],
                "issue": failure.get("error", "unknown"),
                "suggestion": "Add error handling or parameter validation",
            })

        # Extract new skills from successful patterns
        new_skills = self.extractor.extract_skills(min_success_count=3)
        for skill in new_skills:
            self.registry.register(skill)

        return {
            "status": "reviewed",
            "total_executions": len(log),
            "success_rate": success_rate,
            "failures": len(failures),
            "suggestions": suggestions,
            "new_skills_extracted": len(new_skills),
        }


class LearningLoop:
    """Closed loop: Experience → Extract → Refine → Store → Reuse."""

    def __init__(self, executor: SkillExecutor, extractor: SkillExtractor, registry: SkillRegistry, memory: MemoryManager):
        self.executor = executor
        self.extractor = extractor
        self.registry = registry
        self.memory = memory
        self._metrics = {
            "total_experiences": 0,
            "skills_created": 0,
            "learning_velocity": 0.0,
        }
        self._lock = threading.Lock()

    def cycle(self, input_data: str, output_data: str, success: bool, skill_hint: str = ""):
        # Experience
        self.extractor.observe_execution(input_data, output_data, success, skill_hint)
        with self._lock:
            self._metrics["total_experiences"] += 1

        # Extract
        new_skills = self.extractor.extract_skills(min_success_count=3)
        for skill in new_skills:
            self.registry.register(skill)
            with self._lock:
                self._metrics["skills_created"] += 1

        # Metrics
        all_skills = self.registry.list_all()
        with self._lock:
            self._metrics["learning_velocity"] = self._metrics["skills_created"] / max(1, self._metrics["total_experiences"])

    def get_metrics(self) -> Dict:
        with self._lock:
            return dict(self._metrics)


class UserModelStub:
    """Track user preferences, interaction patterns."""

    def __init__(self):
        self._preferences: Dict[str, Any] = {}
        self._interaction_count = 0
        self._lock = threading.Lock()

    def record_interaction(self, interaction_type: str, metadata: Dict = None):
        with self._lock:
            self._interaction_count += 1
            self._preferences.setdefault(interaction_type, 0)
            self._preferences[interaction_type] += 1

    def get_preferences(self) -> Dict:
        with self._lock:
            return dict(self._preferences)


class PlatformGatewayStub:
    """Unified messaging interface — Telegram, Discord, Slack, WhatsApp, Signal, CLI."""

    def __init__(self):
        self._platforms: Dict[str, bool] = {}
        self._messages: List[Dict] = []
        self._lock = threading.Lock()

    def register_platform(self, name: str, enabled: bool = True):
        with self._lock:
            self._platforms[name] = enabled

    def send(self, platform: str, message: str, target: str = "") -> bool:
        with self._lock:
            if not self._platforms.get(platform, False):
                return False
            self._messages.append({
                "platform": platform,
                "message": message,
                "target": target,
                "timestamp": time.time(),
            })
            return True

    def get_messages(self, platform: str = "") -> List[Dict]:
        with self._lock:
            if platform:
                return [m for m in self._messages if m["platform"] == platform]
            return self._messages[:]


class ModelRouter:
    """Route to multiple LLM providers with failover and cost optimization."""

    def __init__(self):
        self._providers: Dict[str, Dict] = {}
        self._latency_tracker: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def register_provider(self, name: str, endpoint: str, models: List[str], cost_per_token: float = 0.0):
        with self._lock:
            self._providers[name] = {
                "endpoint": endpoint,
                "models": models,
                "cost_per_token": cost_per_token,
                "healthy": True,
            }

    def route(self, model: str = "", strategy: str = "least_latency") -> Optional[str]:
        with self._lock:
            healthy = [(n, p) for n, p in self._providers.items() if p["healthy"]]
            if not healthy:
                return None
            if strategy == "least_latency":
                return min(healthy, key=lambda x: sum(self._latency_tracker.get(x[0], [1.0])))[0]
            if strategy == "cheapest":
                return min(healthy, key=lambda x: x[1]["cost_per_token"])[0]
            return healthy[0][0]

    def record_latency(self, provider: str, latency: float):
        with self._lock:
            self._latency_tracker.setdefault(provider, []).append(latency)
            if len(self._latency_tracker[provider]) > 100:
                self._latency_tracker[provider] = self._latency_tracker[provider][-50:]


class CronScheduler:
    """Scheduled tasks with natural language cron parser stub."""

    def __init__(self):
        self._tasks: List[Dict] = {}
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def schedule(self, name: str, interval_sec: float, callback: Callable, once: bool = False):
        self._tasks[name] = {
            "interval": interval_sec,
            "callback": callback,
            "last_run": 0,
            "once": once,
        }

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._running:
            now = time.time()
            for name, task in list(self._tasks.items()):
                if now - task["last_run"] >= task["interval"]:
                    task["last_run"] = now
                    try:
                        task["callback"]()
                    except Exception as e:
                        print(f"[CRON] Task {name} failed: {e}")
                    if task["once"]:
                        del self._tasks[name]
            time.sleep(1.0)

    def stop(self):
        self._running = False


class SubagentSpawner:
    """Spawn isolated subagents for parallel workstreams."""

    def __init__(self):
        self._subagents: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._counter = 0

    def spawn(self, task: str, params: Dict = None) -> str:
        with self._lock:
            self._counter += 1
            agent_id = f"subagent_{self._counter}"
            self._subagents[agent_id] = {
                "task": task,
                "params": params or {},
                "status": "running",
                "created": time.time(),
                "result": None,
            }
            # Simulate async execution
            threading.Thread(target=self._execute, args=(agent_id,), daemon=True).start()
            return agent_id

    def _execute(self, agent_id: str):
        agent = self._subagents.get(agent_id)
        if not agent:
            return
        time.sleep(random.uniform(0.5, 2.0))  # Simulate work
        agent["status"] = "completed"
        agent["result"] = f"Result for {agent['task']}"

    def get_status(self, agent_id: str) -> Optional[Dict]:
        with self._lock:
            return self._subagents.get(agent_id)

    def collect_results(self) -> List[Dict]:
        with self._lock:
            return [a for a in self._subagents.values() if a["status"] == "completed"]


class TerminalBackendStub:
    """Abstract terminal — local, Docker, SSH, cloud sandbox."""

    def __init__(self):
        self._sessions: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def create_session(self, backend_type: str = "local") -> str:
        with self._lock:
            sid = f"term_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
            self._sessions[sid] = {
                "type": backend_type,
                "created": time.time(),
                "commands": [],
                "outputs": [],
            }
            return sid

    def execute(self, session_id: str, command: str) -> str:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return f"Error: Session {session_id} not found"
            session["commands"].append(command)
            output = f"$ {command}\n[Executed in {session['type']} backend]\n"
            session["outputs"].append(output)
            return output


class SkillKernelBridge:
    """Bridge to event_bus and service_registry."""

    def __init__(self, event_bus=None, service_registry=None):
        self.event_bus = event_bus
        self.service_registry = service_registry

    def publish_skill_event(self, event_type: str, skill_name: str, data: Dict = None):
        if self.event_bus:
            try:
                self.event_bus.publish(f"skills.{event_type}", {
                    "skill": skill_name,
                    "data": data or {},
                    "timestamp": time.time(),
                })
            except Exception:
                pass

    def register_service(self):
        if self.service_registry:
            try:
                self.service_registry.register("skill_engine", {"status": "running", "skills": 0})
            except Exception:
                pass


class HermesEngine:
    """Main orchestrator — compose all components, boot sequence, lifecycle."""

    def __init__(self):
        self.registry = SkillRegistry()
        self.extractor = SkillExtractor(self.registry)
        self.executor = SkillExecutor(self.registry)
        self.memory = MemoryManager()
        self.reflective = ReflectiveEngine(self.executor, self.registry, self.extractor)
        self.learning = LearningLoop(self.executor, self.extractor, self.registry, self.memory)
        self.user_model = UserModelStub()
        self.platform = PlatformGatewayStub()
        self.model_router = ModelRouter()
        self.cron = CronScheduler()
        self.subagents = SubagentSpawner()
        self.terminal = TerminalBackendStub()
        self.bridge = SkillKernelBridge()
        self._booted = False

    def boot(self):
        self.bridge.register_service()
        self.cron.start()
        # Register some default skills
        self.registry.register(Skill(
            name="echo", description="Echo back input",
            code_blocks=["def echo(x): return x"],
            tags=["basic", "utility"],
        ))
        self.registry.register(Skill(
            name="summarize", description="Summarize text",
            code_blocks=["def summarize(text): return text[:100] + '...'"],
            tags=["nlp", "text"],
        ))
        self._booted = True
        print("[HermesEngine] Booted with 2 default skills")

    def shutdown(self):
        self.cron.stop()
        print("[HermesEngine] Shutdown complete")

    def run_skill(self, name: str, params: Dict = None) -> Dict:
        if not self._booted:
            return {"status": "error", "error": "Engine not booted"}
        return self.executor.execute(name, params)

    def spawn_task(self, task: str, params: Dict = None) -> str:
        return self.subagents.spawn(task, params)

    def review_cycle(self) -> Dict:
        return self.reflective.review()

    def get_stats(self) -> Dict:
        return {
            "skills": len(self.registry.list_all()),
            "learning": self.learning.get_metrics(),
            "executions": len(self.executor.get_log()),
            "platforms": list(self.platform._platforms.keys()),
        }


def run_demo():
    print("=" * 60)
    print("MAGNATRIX-OS Hermes Skill Engine Demo")
    print("=" * 60)

    engine = HermesEngine()
    engine.boot()

    # Run skills
    print("\n--- Running Skills ---")
    for i in range(10):
        result = engine.run_skill("echo", {"input": f"Hello {i}"})
        print(f"  Skill run #{i+1}: {result.get('status')}")

    # Simulate learning
    print("\n--- Learning Loop ---")
    for i in range(20):
        engine.learning.cycle(
            input_data=f"task_{i}",
            output_data=f"result_{i}",
            success=i % 7 != 0,  # Some failures
        )

    metrics = engine.learning.get_metrics()
    print(f"  Total experiences: {metrics['total_experiences']}")
    print(f"  Skills created: {metrics['skills_created']}")
    print(f"  Learning velocity: {metrics['learning_velocity']:.3f}")

    # Spawn subagents
    print("\n--- Subagent Spawning ---")
    ids = [engine.spawn_task(f"research_{i}") for i in range(3)]
    time.sleep(2)
    results = engine.subagents.collect_results()
    print(f"  Spawned {len(ids)} subagents, {len(results)} completed")

    # Review
    print("\n--- Reflective Review ---")
    review = engine.review_cycle()
    print(f"  Review status: {review['status']}")
    print(f"  Total executions: {review['total_executions']}")
    print(f"  Success rate: {review['success_rate']:.2%}")
    print(f"  New skills extracted: {review['new_skills_extracted']}")

    # Stats
    print("\n--- Engine Stats ---")
    stats = engine.get_stats()
    print(f"  Skills registered: {stats['skills']}")
    print(f"  Total executions: {stats['executions']}")

    engine.shutdown()
    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
