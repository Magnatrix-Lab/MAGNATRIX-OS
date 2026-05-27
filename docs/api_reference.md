# API Reference

All public APIs from 135+ native modules. Organized by layer.

---

## AI Layer (`ai/`)

### `ai/meta_agent_native.py`

```python
class MetaAgent:
    def __init__(manifesto, model_name="mock", memory="", tools=None,
                 end_detection=None, tool_detection=None,
                 memory_management=None, memory_tracing=False, max_steps=20)
    def compose_request() -> str
    def llm_call(prompt: str) -> str           # Override untuk real LLM
    def detect_tool(text: str) -> (str, str)   # XML parsing: <TOOL: NAME>args</TOOL>
    def run(goal=None) -> str                  # Main agent loop
    def update_memory(text: str) -> None
    def get_memory_trace() -> List[str]

class ResearchAgent(MetaAgent): pass
class SummaryAgent(MetaAgent):
    def chunk_text(text: str) -> List[str]
class CodeAgent(MetaAgent): pass

class AgentOptimizer:
    def run_variation(manifesto, test_goal, score_fn=None) -> dict
    def optimize(base_manifesto, test_goal, variations, score_fn=None) -> dict

class AgentFactory:
    @staticmethod
    def discover_agents(agents_dir: str) -> List[Tuple[str, Optional[str]]]
    @staticmethod
    def load_agent_module(agent_dir: str) -> Optional[Type[MetaAgent]]
```

### `ai/theorem_prover_native.py`

```python
class Term: pass                    # Base class
class Var(Term): name: str
class Const(Term): name: str
class App(Term): fn: Term, arg: Term

class TheoremStatement:
    name: str
    hypotheses: List[Tuple[str, Term]]
    conclusion: Term

class ProofState:
    goals: List[Tuple[str, Term]]
    hypotheses: Dict[str, Term]
    steps: List[str]
    depth: int
    def is_complete() -> bool
    def current_goal() -> Optional[Tuple[str, Term]]
    def clone() -> ProofState

class TacticEngine:
    @staticmethod
    def apply(state: ProofState, tactic: Tactic) -> Union[ProofState, str]
    # Tactics: intro, apply, rewrite, split, simpl, sorry, qed, exact, elim, left, right

class StepProver:
    def predict_tactic(state: ProofState, theorem: TheoremStatement) -> Tactic

class TreeSearch:
    def bfs(initial: ProofState, theorem: TheoremStatement) -> Optional[List[Tactic]]
    def best_first(initial: ProofState, theorem: TheoremStatement) -> Optional[List[Tactic]]

class DraftSketchProver:
    def prove(theorem: TheoremStatement) -> Dict[str, Any]
    # Returns: theorem, sketch, subgoals, proof, complete, llm_calls
```

### `ai/autonomous_agent_native.py`

```python
class Task:
    id: str, description: str, status: str, result: str
    priority: int, depends_on: List[str]

class ToolRegistry:
    def register(name: str, fn: Callable[[str], str])
    def run(name: str, args: str) -> str
    def list() -> List[str]
    # Built-in: SEARCH, WRITE_FILE, READ_FILE, CALCULATE, HTTP_GET, EXECUTE_CODE

class MemoryManager:
    def add(role: str, content: str)
    def get_context(n: int = 10) -> str
    def store_fact(key: str, value: Any)
    def recall(key: str) -> Any

class GoalDecomposer:
    def decompose(goal: str) -> List[Task]

class Observer:
    @staticmethod
    def evaluate(task: Task) -> Tuple[str, float]  # (verdict, score)

class SelfCritique:
    @staticmethod
    def reflect(history: List[Dict]) -> Dict[str, Any]

class AutonomousAgent:
    def __init__(goal: str, max_steps: int, memory_path: str)
    def run(goal=None) -> str              # Full autonomous loop
    def get_status() -> Dict[str, Any]
```

### `ai/local_agent_native.py`

```python
class LocalLLM:
    def __init__(model_path: str = "mock-model.gguf")
    def load() -> bool
    def generate(prompt: str, max_tokens=512, temperature=0.7) -> str
    def get_stats() -> Dict[str, Any]

class PromptBuilder:
    @staticmethod
    def build(system: str, history: List[Dict], tools: List[Dict]) -> str

class MessageBuffer:
    def add(role: str, content: str)
    def get_context() -> List[Dict[str, str]]
    def clear()

class ToolParser:
    @staticmethod
    def parse(text: str) -> List[ToolCall]
    @staticmethod
    def has_tool_call(text: str) -> bool

class SimpleAgent:
    def __init__(llm: LocalLLM, tools: List[Tool], max_steps: int)
    def run(goal: str) -> str
    def get_history() -> List[Dict[str, str]]

class Evaluator:
    def add_case(input_text: str, expected_keywords: List[str], description: str)
    def evaluate(agent_factory: Callable) -> Dict[str, Any]

class Telemetry:
    def record(event: str, data: Dict)
    def summary() -> Dict[str, Any]
    def export() -> str
```

---

## Knowledge Layer (`knowledge/`)

### `knowledge/agentic_rag_native.py`

```python
class HashEmbedding:
    def embed(text: str) -> List[float]          # 128-dim deterministic
    def embed_batch(texts: List[str]) -> List[List[float]]

class VectorStore:
    def add_document(doc_id: str, text: str, embedding: List[float])
    def search(query_embedding: List[float], top_k=5) -> List[Tuple[str, float]]
    def delete(doc_id: str) -> bool

class SentenceChunker:
    def chunk(text: str, max_chunk_size=500, overlap=50) -> List[str]

class MCPClient:
    def __init__(server_url: str)
    def call_tool(tool_name: str, params: Dict) -> Dict
    def list_tools() -> List[Dict]

class AgenticRAGGraph:
    def __init__(vector_store: VectorStore, mcp_client: MCPClient, llm=None)
    def run(question: str, use_ddg=False) -> Dict[str, Any]
    # Returns: answer, sources, web_results, steps

class HybridRetriever:
    def __init__(vector_store: VectorStore)
    def retrieve(query: str, k: int = 5, use_web: bool = False) -> List[Dict]
```

### `knowledge/document_agent_native.py`

```python
class DocumentChunk:
    id: str, content: str, embedding: List[float], metadata: Dict

class DocumentAgent:
    def __init__(document_id: str, chunks: List[DocumentChunk])
    def query(question: str) -> str
    def summarize() -> str

class VectorIndex:
    def add(doc_chunks: List[DocumentChunk])
    def search(query: str, k: int) -> List[DocumentChunk]

class MetaAgent:
    def __init__(document_agents: List[DocumentAgent])
    def route(query: str) -> List[DocumentAgent]
    def query_all(query: str) -> Dict[str, str]

class Synthesizer:
    @staticmethod
    def merge(answers: List[str]) -> str
```

---

## Runtime Layer (`runtime/`)

### `runtime/multi_agent_swarm_native.py`

```python
class AgentCapabilities:
    tools: List[str], languages: List[str], max_tokens: int
    max_context: int, specialties: List[str]
    def matches(requirement: str) -> float          # 0.0-1.0

class AgentRegistration:
    agent_id: str, name: str, role: str
    capabilities: AgentCapabilities, status: str
    last_heartbeat: float, tasks_completed: int
    tasks_failed: int, reputation: float
    def is_alive(timeout=30.0) -> bool

class AgentRegistry:
    def register(agent: AgentRegistration) -> bool
    def unregister(agent_id: str) -> bool
    def heartbeat(agent_id: str) -> bool
    def update_status(agent_id: str, status: str) -> bool
    def find_by_role(role: str) -> List[AgentRegistration]
    def find_by_capability(requirement: str, min_score=0.3) -> List[(AgentRegistration, float)]
    def get_all_alive() -> List[AgentRegistration]
    def get(agent_id: str) -> Optional[AgentRegistration]
    def on_event(listener: Callable[[str, AgentRegistration], None])

class SharedMemory:
    # KV
    def set(key: str, value: Any, ttl: Optional[float] = None)
    def get(key: str, default=None) -> Any
    def delete(key: str) -> bool
    def keys(pattern="*") -> List[str]
    # Pub/Sub
    def publish(channel: str, message: Any) -> int
    def subscribe(channel: str, listener: Callable)
    def unsubscribe(channel: str, listener: Callable)
    # Graph
    def graph_add_node(graph: str, node_id: str, properties: Dict)
    def graph_add_edge(graph: str, from_node: str, to_node: str, relation: str, properties=None)
    def graph_neighbors(graph: str, node_id: str, relation=None) -> List[Tuple]
    def graph_traverse(graph: str, start: str, max_depth=3) -> List[List[str]]
    # Vector
    def vector_upsert(doc_id: str, text: str, payload=None)
    def vector_search(query: str, top_k=5) -> List[(str, float, Any)]

class MessageBus:
    def send(msg: AgentMessage) -> bool
    def recv(agent_id: str, timeout=1.0, msg_type=None) -> Optional[AgentMessage]
    def recv_all(agent_id: str, msg_type=None) -> List[AgentMessage]
    def subscribe_broadcast(agent_id: str, msg_type: str, callback: Callable)
    def stop()

class TaskDelegator:
    def create_task(description: str, required_caps="", created_by="system") -> Task
    def assign(task: Task, strategy="best_match") -> Optional[str]  # agent_id
    def decompose(task: Task) -> List[Task]
    def report_result(task_id: str, result: Any, success=True)
    def get_task(task_id: str) -> Optional[Task]
    def get_all_tasks() -> List[Task]

class ConsensusEngine:
    def propose(proposal_id: str, description: str, proposer_id: str, required_agents=3) -> bool
    def cast_vote(proposal_id: str, voter_id: str, vote: str, reason="") -> bool
    def get_result(proposal_id: str) -> Optional[str]
    def get_votes(proposal_id: str) -> List[Vote]

class AuctionHouse:
    def open_auction(task_id: str, task_description: str, timeout=5.0)
    def place_bid(bid: Bid) -> bool
    def resolve(task_id: str) -> Optional[Bid]

class SwarmOrchestrator:
    def register_agent(agent_id, name, role, capabilities) -> AgentRegistration
    def submit_task(description: str, strategy="best_match") -> Task
    def run_collaborative(goal: str, agents: List[str]) -> Dict[str, Any]
    def propose_consensus(description: str, proposer: str) -> str
    def stop()

class CollaborativeAgent:
    STATES = ["idle", "researching", "writing", "coding", "reviewing", "waiting", "done", "error"]
    def __init__(agent_id, name, role, orchestrator)
    def stop()

class MCPToolProtocol:
    def register_tool(agent_id, tool_name, schema, handler)
    def call_tool(caller_id, tool_name, arguments, timeout=5.0) -> Any
    def list_tools() -> List[Dict]
```

### `runtime/agent_collaboration_native.py`

```python
class CrewAIExecutor:
    def __init__(orchestrator: SwarmOrchestrator)
    def execute(goal: str) -> Dict[str, Any]

class AutoGenChat:
    def __init__(orchestrator: SwarmOrchestrator, participants: List[str])
    def start(topic: str) -> List[Dict[str, Any]]

class LangGraphWorkflow:
    def add_node(name: str, fn: Callable[[GraphState], GraphState])
    def add_edge(from_node: str, to_node: str, condition=None)
    def set_entry(node: str)
    def run(initial_state=None, max_steps=20) -> GraphState

class MCPCollaboration:
    def __init__(orchestrator: SwarmOrchestrator)
    def call_cross_agent_tool(caller: str, tool: str, args: Dict) -> Dict
    def list_all_tools() -> List[Dict]

class HierarchicalSwarm:
    def __init__(orchestrator: SwarmOrchestrator)
    def execute(goal: str, worker_ids: List[str]) -> Dict[str, Any]
```

### `runtime/state_management_native.py`

```python
class RedisLikeStore:
    def set(key, value, ttl_ms=None) -> bool
    def get(key) -> Any
    def delete(*keys) -> int
    def exists(*keys) -> int
    def keys(pattern="*") -> List[str]
    def incr(key, amount=1) -> int
    def lpush(key, *values) -> int
    def lrange(key, start, end) -> List[Any]
    def hset(key, field, value) -> int
    def hget(key, field) -> Any
    def hgetall(key) -> Dict[str, Any]
    def sadd(key, *members) -> int
    def smembers(key) -> Set[Any]
    def zadd(key, *score_members) -> int
    def zrange(key, start, end) -> List[Any]
    def publish(channel, message) -> int
    def subscribe(channel, listener)
    def unsubscribe(channel, listener)
    def xadd(stream, fields) -> str
    def xrange(stream, count=10) -> List[(str, Dict)]
    def save(path) -> bool
    def load(path) -> bool

class VectorDB:
    def __init__(dimension=128)
    def add(doc_id, text, metadata=None)
    def search(query, top_k=5, filter_meta=None) -> List[(str, float, Dict)]
    def delete(doc_id) -> bool
    def count() -> int

class GraphDB:
    def create_node(node_id, labels=None, properties=None)
    def create_edge(from_node, to_node, relation, properties=None) -> bool
    def get_node(node_id) -> Optional[Dict]
    def get_neighbors(node_id, relation=None) -> List[Tuple]
    def get_predecessors(node_id, relation=None) -> List[Tuple]
    def bfs_paths(start, end, max_depth=5) -> List[List[str]]
    def query(label=None, property_filter=None) -> List[str]
    def delete_node(node_id) -> bool
    def shortest_path(start, end, relation=None) -> Optional[List[str]]

class TemporalStore:
    def append(event_type, source, payload=None, tags=None) -> str
    def query(since=0, until=None, event_type=None, source=None, tags=None) -> List[TemporalEvent]
    def get_latest(n=10) -> List[TemporalEvent]
    def checkpoint(name, state)
    def restore(name) -> Optional[Dict]
    def export(path) -> bool
    def stats() -> Dict[str, Any]

class StateManager:
    def __init__()
    def agent_set(agent_id, key, value)
    def agent_get(agent_id, key) -> Any
    def agent_checkpoint(agent_id, state)
    def agent_restore(agent_id) -> Optional[Dict]
```

### `runtime/jit_compiler_native.py`

```python
class Parser:
    def __init__(source: str)
    def parse() -> List[ASTNode]

class BytecodeGenerator:
    def generate(ast_nodes) -> List[Bytecode]

class Interpreter:
    def run(bytecode, feedback, args=None) -> Any

class BaselineJIT:
    def compile(bytecode, feedback) -> JITFunction

class MidTierJIT:
    def compile(bytecode, feedback) -> JITFunction
    def _optimize(bytecode) -> List[Bytecode]  # constant folding

class OptimizingJIT:
    def compile(bytecode, feedback) -> JITFunction

class ExecutionEngine:
    def execute(name, bytecode, feedback, **kwargs) -> Any
    def _should_deopt(jit_fn, feedback) -> bool
    def force_tier(name, bytecode, feedback, tier) -> JITFunction

class Compiler:
    def compile(source, func_name="main") -> (List[Bytecode], FeedbackVector)
    def run(source, func_name="main", **kwargs) -> Any
    def run_with_tier(source, func_name, tier, **kwargs) -> Any
```

### `runtime/tri_language_bridge.py`

```python
class UnifiedCrypto:
    def __init__()
    def sha256(data) -> bytes
    def sha512(data) -> bytes
    def sha3_256(data) -> bytes
    def blake3(data) -> bytes
    def hmac_sha256(key, data) -> bytes
    def ed25519_keypair() -> (bytes, bytes)
    def ed25519_sign(sk, message) -> bytes
    def ed25519_verify(pk, message, sig) -> bool
    def chacha20_encrypt(key, nonce, plaintext) -> bytes
    def chacha20_decrypt(key, nonce, ciphertext) -> bytes
    def aes_gcm_encrypt(key, iv, plaintext) -> bytes
    def aes_gcm_decrypt(key, iv, ciphertext) -> bytes
    def argon2_hash(password, salt) -> bytes
    def random_bytes(n) -> bytes
    def base64(data) -> str
    def hex(data) -> str

class UnifiedHFT:
    def __init__()
    def create_order_book() -> OrderBook
    def place_order(book, side, price, qty, order_id)
    def get_spread(book) -> (float, float)
    def detect_arbitrage(venue_a, venue_b) -> List[Dict]

class TriLanguageHub:
    def __init__()
    def status() -> Dict[str, str]
    def benchmark(name, n=1000) -> Dict[str, float]
```

---

## Security Layer (`security/`)

### `security/rust_crypto_engine/src/lib.rs` (PyO3 bindings)

Exposed as Python module `crypto_engine`:
```python
crypto_engine.sha256(data: bytes) -> bytes
crypto_engine.sha512(data: bytes) -> bytes
crypto_engine.sha3_256(data: bytes) -> bytes
crypto_engine.blake3(data: bytes) -> bytes
crypto_engine.hmac_sha256(key: bytes, data: bytes) -> bytes
crypto_engine.ed25519_keypair() -> (bytes, bytes)
crypto_engine.ed25519_sign(sk: bytes, message: bytes) -> bytes
crypto_engine.ed25519_verify(pk: bytes, message: bytes, sig: bytes) -> bool
crypto_engine.chacha20_encrypt(key: bytes, nonce: bytes, plaintext: bytes) -> bytes
crypto_engine.chacha20_decrypt(key: bytes, nonce: bytes, ciphertext: bytes) -> bytes
crypto_engine.aes_gcm_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes
crypto_engine.aes_gcm_decrypt(key: bytes, iv: bytes, ciphertext: bytes) -> bytes
crypto_engine.argon2_hash(password: bytes, salt: bytes) -> bytes
crypto_engine.random_bytes(n: int) -> bytes
crypto_engine.base64(data: bytes) -> str
crypto_engine.hex(data: bytes) -> str
```

---

## Trading Layer (`trading/`)

### `trading/cpp_hft_engine/` (pybind11 bindings)

Exposed as Python module `hft_engine`:
```python
hft_engine.price_to_fixed(price: float) -> int       # int64_t, scale 1e8
hft_engine.fixed_to_price(fixed: int) -> float

hft_engine.OrderBook()  # C++ class
    .add_order(side: int, price: int, qty: int, id: str)
    .remove_order(id: str)
    .best_bid() -> int
    .best_ask() -> int
    .spread() -> int
    .depth_at_price(price: int, side: int) -> int

hft_engine.ArbitrageDetector(fee_a: float, fee_b: float)
    .detect(book_a: OrderBook, book_b: OrderBook) -> List[Dict]
    .opportunity_cost(profit: int, volume: int) -> float

hft_engine.HFTEngine()
    .process_tick(tick: Dict)
    .get_latency_us() -> int
    .book_manager() -> OrderBook
    .arb_detector() -> ArbitrageDetector
```

---

## GUI Layer (`website/`)

### Dashboard API

No JavaScript API — pure HTML/CSS/JS panels. Open `dashboard.html` in browser.

20 panels via iframe embeds:
```
panel_chat.html       — AI chat interface
panel_kanban.html     — Drag-and-drop task board
panel_models.html     — LLM model registry
panel_providers.html  — Provider manager (3-tier routing)
panel_trading.html    — Real-time HFT desk
panel_security.html   — Crypto status center
panel_p2p.html        — Mesh network visualizer
panel_router.html     — LLM request router
panel_ccswitch.html   — Multi-tool session switcher
panel_profile.html    — Identity and stats
panel_skills.html     — Native module catalog
panel_memory.html     — Short/long-term memory
panel_schedules.html  — Calendar and task scheduler
panel_obsidian.html   — Knowledge vault editor
panel_sessions.html   — Active connection list
panel_gateway.html    — API gateway metrics
panel_tools.html      — Tool catalog
panel_plugins.html    — Plugin registry
panel_settings.html   — 6-tab configuration
panel_terminal.html   — System console
```

---

## Test Layer (`tests/`)

### `tests/integration/test_tri_language.py`

```python
# 22 tests covering:
# - Backend detection (Python/C++/Rust)
# - UnifiedCrypto (all primitives)
# - UnifiedHFT (order book + arbitrage)
# - TriLanguageHub (status + benchmark)
# - SecureTickPayload (encryption)
```

Run: `python tests/integration/test_tri_language.py`

Expected: 22 tests, 0 failures, ~0.3s.
