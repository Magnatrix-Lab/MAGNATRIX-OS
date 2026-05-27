# Quickstart Guide

Working end-to-end examples. Copy, paste, run. Every example is self-contained.

---

## Example 1: Create an Agent → Delegate Task → See Result (CrewAI)

```python
from runtime.multi_agent_swarm_native import SwarmOrchestrator, AgentCapabilities

# 1. Create orchestrator
orch = SwarmOrchestrator()

# 2. Register agents with roles
orch.register_agent("r1", "Alice", "researcher",
    AgentCapabilities(specialties=["research", "data"]))
orch.register_agent("w1", "Bob", "writer",
    AgentCapabilities(specialties=["write", "content"]))
orch.register_agent("c1", "Carol", "critic",
    AgentCapabilities(specialties=["review", "critique"]))

# 3. Submit task — auto-decomposed into subtasks
task = orch.submit_task("Research Python asyncio best practices")

# 4. Print results
print(f"Task: {task.description}")
print(f"Subtasks: {len(task.subtasks)}")
for st_id in task.subtasks:
    st = orch.delegator.get_task(st_id)
    print(f"  [{st.status}] {st.description[:50]}...")

orch.stop()
```

Run: `python example1.py`

Expected output:
```
Task: Research Python asyncio best practices
Subtasks: 2
  [assigned] Research: Research Python asyncio best practices...
  [assigned] Draft: Research Python asyncio best practices...
```

---

## Example 2: Multi-Agent Chat (AutoGen Pattern)

```python
from runtime.multi_agent_swarm_native import SwarmOrchestrator, AgentCapabilities
from runtime.agent_collaboration_native import AutoGenChat

orch = SwarmOrchestrator()
orch.register_agent("a1", "Researcher", "researcher",
    AgentCapabilities(specialties=["research"]))
orch.register_agent("a2", "Writer", "writer",
    AgentCapabilities(specialties=["write"]))
orch.register_agent("a3", "Critic", "critic",
    AgentCapabilities(specialties=["review"]))

chat = AutoGenChat(orch, ["a1", "a2", "a3"])
log = chat.start("Should we use asyncio or threading?")

for msg in log:
    print(f"[{msg['sender_name']}] {msg['text'][:60]}")

orch.stop()
```

---

## Example 3: State Machine Workflow (LangGraph)

```python
from runtime.agent_collaboration_native import LangGraphWorkflow, GraphState

workflow = LangGraphWorkflow()

# Define nodes
workflow.add_node("start", lambda s: s.update("phase", "started") or s)
workflow.add_node("gather", lambda s: s.update("data", "collected") or s)
workflow.add_node("process", lambda s: s.update("processed", True) or s)
workflow.add_node("end", lambda s: s.update("done", True) or s)

# Connect nodes
workflow.set_entry("start")
workflow.add_edge("start", "gather")
workflow.add_edge("gather", "process")
workflow.add_edge("process", "end")

# Run
state = workflow.run()
print("Path:", " → ".join(state.history))
print("Data:", state.data)
```

---

## Example 4: Vector Search (Document Retrieval)

```python
from knowledge.agentic_rag_native import VectorStore, HashEmbedding

# Create store
store = VectorStore()
emb = HashEmbedding()

# Add documents
store.add_document("doc1", "Python asyncio is great for concurrent I/O", emb.embed("asyncio"))
store.add_document("doc2", "Rust ownership model prevents data races", emb.embed("rust"))
store.add_document("doc3", "C++ memory management requires care", emb.embed("cpp"))

# Search
results = store.search("concurrent programming", top_k=2)
for doc_id, score in results:
    print(f"  {doc_id}: score={score:.3f}")
```

---

## Example 5: Graph Database (Knowledge Graph)

```python
from runtime.state_management_native import GraphDB

g = GraphDB()

# Create nodes
g.create_node("alice", ["Person"], {"name": "Alice", "role": "researcher"})
g.create_node("paper", ["Document"], {"title": "Swarm Intelligence"})

# Create edge
g.create_edge("alice", "paper", "authored")

# Query
path = g.shortest_path("alice", "paper")
print("Path:", " → ".join(path))

# Find all researchers
researchers = g.query(label="Person", property_filter={"role": "researcher"})
print("Researchers:", researchers)
```

---

## Example 6: Redis-Like Store

```python
from runtime.state_management_native import RedisLikeStore

store = RedisLikeStore()

# KV
store.set("key", "value", ttl_ms=5000)
print(store.get("key"))

# List
store.lpush("queue", "task1", "task2", "task3")
print(store.lrange("queue", 0, 2))

# Hash
store.hset("config", "model", "llama-3")
print(store.hget("config", "model"))

# Set
store.sadd("tags", "ai", "python", "swarm")
print(store.smembers("tags"))

# Pub/Sub
received = []
store.subscribe("alerts", lambda ch, msg: received.append(msg))
store.publish("alerts", "Agent Alice completed task")
print("Received:", received)
```

---

## Example 7: Theorem Prover

```python
from ai.theorem_prover_native import TheoremStatement, DraftSketchProver, Const

# Define a theorem
theorem = TheoremStatement(
    name="identity",
    hypotheses=[],
    conclusion=Const("A → A"),
)

# Prove it
dsp = DraftSketchProver()
result = dsp.prove(theorem)

print("Theorem:", result["theorem"])
print("Sketch:", result["sketch"])
print("Proof:", result["proof"])
print("Complete:", result["complete"])
```

---

## Example 8: JIT Compiler (4-Tier)

```python
from runtime.jit_compiler_native import Compiler

comp = Compiler()

# Compile and execute
source = """
result = 100 + 200 * 3
"""
comp.run(source)
print("Result:", comp.engine.interpreter.variables.get("result"))

# Force specific tier
comp.engine.interpreter.variables = {}
fn = comp.engine.force_tier("demo", comp.compile(source)[0], comp.compile(source)[1], "TurboFan")
fn()
print("TurboFan result:", comp.engine.interpreter.variables.get("result"))
```

---

## Example 9: Meta Agent with Tools

```python
from ai.meta_agent_native import MetaAgent

agent = MetaAgent(
    manifesto="You are a helpful agent. Use SEARCH, WRITE_FILE, TELL_USER.",
    max_steps=5,
)

# Override LLM untuk deterministic demo
responses = [
    "I will search. <TOOL: SEARCH>asyncio</TOOL>",
    "Found it. <TOOL: WRITE_FILE>output.txt|asyncio is great</TOOL>",
    "Done. <TASK_COMPLETED>",
]
idx = [0]
def _mock_llm(p):
    r = responses[idx[0] % len(responses)]
    idx[0] += 1
    return r
agent.llm_call = _mock_llm

result = agent.run("Tell me about asyncio")
print(f"Steps: {agent.step_count}")
print(f"Tools used: {agent._last_tool_called}")
```

---

## Example 10: Full GUI (Open Dashboard)

```bash
# No server needed — pure HTML/CSS/JS
cd website
python -m http.server 8080
# Open http://localhost:8080/dashboard.html
```

Or simply open `website/dashboard.html` directly in a browser.

20 panels available: Chat, Kanban, Models, Providers, Trading, Security, P2P, Router, CC Switch, Terminal, Settings, Profile, Skills, Memory, Schedules, Obsidian, Sessions, Gateway, Tools, Plugins.

---

## Running All Tests

```bash
# Run every native module's self-test
for f in $(find . -name "*_native.py"); do
    echo "Testing $f..."
    python "$f" > /dev/null 2>&1 && echo "  PASS" || echo "  FAIL"
done
```

Or test the tri-language bridge:
```bash
python tests/integration/test_tri_language.py
```

Expected: 22 tests, all pass in ~0.3s.
