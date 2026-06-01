#!/usr/bin/env python3
"""
workflows/node_workflow_native.py
AMATI-PELAJARI-TIRU dari Outerbridge (kidGodzilla/outerbridge → Outerbridgeio/Outerbridge)

Pattern yang diobservasi & di-native-kan:
1. Node-based Workflow Automation — DAG execution dengan drag-and-drop logic
2. Component Registry — Node + Credential system untuk Web2 & Web3
3. Execution Engine — Topological sort, data passing antar node, parallel execution
4. Credential Vault — Encrypted credential storage untuk API keys, private keys, RPC endpoints
5. Web2/Web3 Bridge — Unified adapter untuk on-chain (EVM, Solana) & off-chain (REST, WebSocket)
6. Workflow Builder — Programmatic workflow construction (low-code equivalent dalam Python)

Layer: Runtime/Skills (Layer 3 & 6)
Dependencies: stdlib + asyncio + typing (zero external deps untuk core engine)
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import secrets
import time
import uuid
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Tuple, Union


# ────────────────────────────────────────────────
# Core Types & Enums
# ────────────────────────────────────────────────

class NodeType(Enum):
    """Kategori node dalam workflow."""
    TRIGGER = auto()       # Event-driven start (webhook, cron, block)
    ACTION = auto()       # Execute operation (API call, tx, compute)
    CONDITION = auto()    # Branching logic (if/else, switch)
    LOOP = auto()         # Iteration (for-each, while)
    MERGE = auto()        # Join multiple branches
    WEB3 = auto()         # Blockchain-specific (read, write, event)
    WEB2 = auto()         # Off-chain integration (HTTP, DB, queue)


class ExecutionStatus(Enum):
    """Status eksekusi node atau workflow."""
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    SKIPPED = auto()
    TIMEOUT = auto()


@dataclass
class Port:
    """Input/output port untuk node."""
    name: str
    type_hint: str = "Any"
    required: bool = True
    default: Any = None
    description: str = ""


@dataclass
class NodeSpec:
    """Spesifikasi sebuah node component."""
    id: str
    name: str
    node_type: NodeType
    category: str = "General"
    description: str = ""
    inputs: List[Port] = field(default_factory=list)
    outputs: List[Port] = field(default_factory=list)
    credentials: List[str] = field(default_factory=list)  # required credential types
    config_schema: Dict[str, Any] = field(default_factory=dict)
    execute_fn: Optional[Callable[..., Any]] = None


@dataclass
class NodeInstance:
    """Instansiasi NodeSpec dalam workflow."""
    instance_id: str
    spec_id: str
    config: Dict[str, Any] = field(default_factory=dict)
    position: Tuple[int, int] = (0, 0)  # canvas x,y (metadata untuk GUI)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """Koneksi antar node instance dalam workflow DAG."""
    source_id: str          # instance_id node sumber
    source_port: str        # nama output port
    target_id: str          # instance_id node target
    target_port: str        # nama input port
    condition: Optional[str] = None  # optional conditional expression


@dataclass
class ExecutionResult:
    """Hasil eksekusi satu node."""
    node_id: str
    status: ExecutionStatus
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: float = 0.0
    finished_at: float = 0.0
    logs: List[str] = field(default_factory=list)


@dataclass
class WorkflowRun:
    """Satu run lengkap dari workflow."""
    run_id: str
    workflow_id: str
    status: ExecutionStatus
    trigger_data: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, ExecutionResult] = field(default_factory=dict)
    started_at: float = 0.0
    finished_at: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)  # shared run context


# ────────────────────────────────────────────────
# Credential Vault (Encrypted Credential Storage)
# ────────────────────────────────────────────────

class CredentialVault:
    """
    Vault terenkripsi untuk menyimpan credential (API keys, private keys, RPC URLs).
    Sederhana: XOR + SHA-256 envelope dengan master key hash.
    Untuk produksi, ganti dengan libsodium/ChaCha20-Poly1305 dari Rust bridge.
    """

    def __init__(self, master_key: Optional[str] = None):
        self._master_key = master_key or secrets.token_hex(32)
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def _derive_key(self, salt: str) -> bytes:
        """Derive 32-byte key dari master_key + salt."""
        return hashlib.sha256((self._master_key + salt).encode()).digest()

    def _encrypt(self, plaintext: str, salt: str) -> str:
        """XOR envelope encryption."""
        key = self._derive_key(salt)
        data = plaintext.encode()
        encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
        return f"enc:{salt}:{encrypted.hex()}"

    def _decrypt(self, ciphertext: str) -> str:
        """XOR envelope decryption."""
        if not ciphertext.startswith("enc:"):
            return ciphertext
        _, salt, hexdata = ciphertext.split(":", 2)
        key = self._derive_key(salt)
        data = bytes.fromhex(hexdata)
        decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
        return decrypted.decode()

    async def store(self, credential_id: str, data: Dict[str, Any], overwrite: bool = False) -> None:
        async with self._lock:
            if credential_id in self._store and not overwrite:
                raise ValueError(f"Credential {credential_id} already exists")
            salt = secrets.token_hex(8)
            encrypted = {}
            for k, v in data.items():
                if isinstance(v, str) and k in ("api_key", "private_key", "secret", "password", "rpc_url"):
                    encrypted[k] = self._encrypt(v, salt)
                else:
                    encrypted[k] = v
            self._store[credential_id] = encrypted

    async def retrieve(self, credential_id: str) -> Dict[str, Any]:
        async with self._lock:
            if credential_id not in self._store:
                raise KeyError(f"Credential {credential_id} not found")
            record = self._store[credential_id].copy()
            for k, v in record.items():
                if isinstance(v, str) and v.startswith("enc:"):
                    record[k] = self._decrypt(v)
            return record

    async def delete(self, credential_id: str) -> None:
        async with self._lock:
            self._store.pop(credential_id, None)

    async def list_ids(self) -> List[str]:
        async with self._lock:
            return list(self._store.keys())

    def to_dict(self) -> Dict[str, Any]:
        return {"store_keys": list(self._store.keys()), "count": len(self._store)}


# ────────────────────────────────────────────
# Web2 & Web3 Bridge Adapters
# ────────────────────────────────────────────

class Web2Adapter(ABC):
    """Base adapter untuk off-chain integrations."""

    @abstractmethod
    async def call(self, method: str, url: str, payload: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def stream(self, method: str, url: str, payload: Optional[Dict] = None) -> Any:
        ...


class Web3Adapter(ABC):
    """Base adapter untuk on-chain integrations."""

    @abstractmethod
    async def read_contract(self, address: str, abi: List[Dict], function: str, args: List[Any]) -> Any:
        ...

    @abstractmethod
    async def write_contract(self, address: str, abi: List[Dict], function: str, args: List[Any], private_key: str) -> str:
        ...

    @abstractmethod
    async def get_balance(self, address: str, token: Optional[str] = None) -> Union[int, float]:
        ...

    @abstractmethod
    async def listen_events(self, address: str, event_signature: str, from_block: int) -> List[Dict[str, Any]]:
        ...


class StubWeb2Adapter(Web2Adapter):
    """Stub adapter untuk testing tanpa network."""

    async def call(self, method: str, url: str, payload: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        await asyncio.sleep(0.01)
        return {"status": 200, "method": method, "url": url, "data": payload, "stub": True}

    async def stream(self, method: str, url: str, payload: Optional[Dict] = None) -> Any:
        yield {"chunk": "stub", "url": url}


class StubWeb3Adapter(Web3Adapter):
    """Stub Web3 adapter untuk testing tanpa RPC."""

    async def read_contract(self, address: str, abi: List[Dict], function: str, args: List[Any]) -> Any:
        await asyncio.sleep(0.01)
        return {"address": address, "function": function, "args": args, "result": 42, "stub": True}

    async def write_contract(self, address: str, abi: List[Dict], function: str, args: List[Any], private_key: str) -> str:
        await asyncio.sleep(0.01)
        return "0x" + hashlib.sha256(f"{address}{function}{time.time()}".encode()).hexdigest()

    async def get_balance(self, address: str, token: Optional[str] = None) -> Union[int, float]:
        return 1.337

    async def listen_events(self, address: str, event_signature: str, from_block: int) -> List[Dict[str, Any]]:
        return [{"event": event_signature, "block": from_block + 1, "data": "stub"}]


# ────────────────────────────────────────────
# Node Registry
# ────────────────────────────────────────────

class NodeRegistry:
    """
    Registry untuk semua node components yang tersedia.
    Setiap node punya spec, execute function, dan metadata.
    """

    def __init__(self):
        self._specs: Dict[str, NodeSpec] = {}
        self._categories: Set[str] = set()

    def register(self, spec: NodeSpec) -> None:
        if spec.id in self._specs:
            raise ValueError(f"NodeSpec {spec.id} already registered")
        self._specs[spec.id] = spec
        self._categories.add(spec.category)

    def unregister(self, spec_id: str) -> None:
        self._specs.pop(spec_id, None)

    def get(self, spec_id: str) -> NodeSpec:
        if spec_id not in self._specs:
            raise KeyError(f"NodeSpec {spec_id} not found")
        return self._specs[spec_id]

    def list_specs(self, category: Optional[str] = None) -> List[NodeSpec]:
        specs = list(self._specs.values())
        if category:
            specs = [s for s in specs if s.category == category]
        return specs

    def list_categories(self) -> List[str]:
        return sorted(self._categories)

    def count(self) -> int:
        return len(self._specs)


# ────────────────────────────────────────────
# Workflow Definition & DAG
# ────────────────────────────────────────────

class WorkflowDefinition:
    """
    Definisi workflow lengkap: nodes, edges, dan metadata.
    Bisa diserialisasi ke JSON untuk storage / sharing.
    """

    def __init__(self, workflow_id: str, name: str, description: str = ""):
        self.workflow_id = workflow_id
        self.name = name
        self.description = description
        self.nodes: Dict[str, NodeInstance] = {}
        self.edges: List[Edge] = []
        self.triggers: List[str] = []  # instance_ids yang merupakan trigger nodes
        self.metadata: Dict[str, Any] = {}

    def add_node(self, instance: NodeInstance, is_trigger: bool = False) -> None:
        self.nodes[instance.instance_id] = instance
        if is_trigger:
            self.triggers.append(instance.instance_id)

    def remove_node(self, instance_id: str) -> None:
        self.nodes.pop(instance_id, None)
        self.triggers = [t for t in self.triggers if t != instance_id]
        self.edges = [e for e in self.edges if e.source_id != instance_id and e.target_id != instance_id]

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def remove_edge(self, source_id: str, target_id: str) -> None:
        self.edges = [e for e in self.edges if not (e.source_id == source_id and e.target_id == target_id)]

    def get_upstream(self, instance_id: str) -> List[Edge]:
        return [e for e in self.edges if e.target_id == instance_id]

    def get_downstream(self, instance_id: str) -> List[Edge]:
        return [e for e in self.edges if e.source_id == instance_id]

    def topological_sort(self) -> List[str]:
        """Topological sort untuk determin execution order."""
        in_degree = {nid: 0 for nid in self.nodes}
        adj = {nid: [] for nid in self.nodes}
        for e in self.edges:
            adj[e.source_id].append(e.target_id)
            in_degree[e.target_id] += 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        order = []
        while queue:
            nid = queue.popleft()
            order.append(nid)
            for neighbor in adj[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self.nodes):
            raise ValueError("Workflow contains a cycle — cannot topologically sort")
        return order

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "nodes": {k: asdict(v) for k, v in self.nodes.items()},
            "edges": [asdict(e) for e in self.edges],
            "triggers": self.triggers,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowDefinition:
        wf = cls(data["workflow_id"], data["name"], data.get("description", ""))
        for nid, nd in data.get("nodes", {}).items():
            wf.nodes[nid] = NodeInstance(**nd)
        for e in data.get("edges", []):
            wf.edges.append(Edge(**e))
        wf.triggers = data.get("triggers", [])
        wf.metadata = data.get("metadata", {})
        return wf


# ────────────────────────────────────────────
# Execution Engine
# ────────────────────────────────────────────

class ExecutionEngine:
    """
    Engine untuk mengeksekusi WorkflowDefinition.
    Supports: sequential, parallel branches, conditional edges, loops, retries.
    """

    def __init__(
        self,
        registry: NodeRegistry,
        vault: CredentialVault,
        web2: Optional[Web2Adapter] = None,
        web3: Optional[Web3Adapter] = None,
        max_concurrent: int = 10,
        default_timeout: float = 30.0,
    ):
        self.registry = registry
        self.vault = vault
        self.web2 = web2 or StubWeb2Adapter()
        self.web3 = web3 or StubWeb3Adapter()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.default_timeout = default_timeout

    async def run(self, workflow: WorkflowDefinition, trigger_data: Optional[Dict[str, Any]] = None) -> WorkflowRun:
        run_id = str(uuid.uuid4())
        run = WorkflowRun(
            run_id=run_id,
            workflow_id=workflow.workflow_id,
            status=ExecutionStatus.RUNNING,
            trigger_data=trigger_data or {},
            started_at=time.time(),
        )

        try:
            order = workflow.topological_sort()
        except ValueError as exc:
            run.status = ExecutionStatus.FAILED
            run.finished_at = time.time()
            return run

        # Build data flow map: node_id -> {port_name -> value}
        data_map: Dict[str, Dict[str, Any]] = {}
        # Initialize trigger nodes with trigger_data
        for tid in workflow.triggers:
            data_map[tid] = {"trigger": run.trigger_data}

        # Track which edges are active (condition evaluated true)
        active_edges: Set[Tuple[str, str]] = set()
        skipped_nodes: Set[str] = set()

        # Execute in topological order with parallel branch support
        executed: Set[str] = set()
        pending = set(order)

        while pending:
            ready = []
            for nid in list(pending):
                upstream = workflow.get_upstream(nid)
                if not upstream:
                    # Trigger node (no upstream edges)
                    ready.append(nid)
                    continue

                # Count active edges vs skipped edges
                active_count = 0
                skipped_count = 0
                blocked = False
                for e in upstream:
                    if e.source_id in skipped_nodes:
                        skipped_count += 1
                    elif e.source_id in executed:
                        if (e.source_id, e.target_id) in active_edges:
                            active_count += 1
                        else:
                            # Edge inactive (condition evaluated false) — counts as skipped
                            skipped_count += 1
                    else:
                        blocked = True
                        break

                if blocked:
                    continue
                if active_count > 0:
                    ready.append(nid)
                elif skipped_count > 0 and skipped_count == len(upstream):
                    # All upstreams skipped — mark this node as skipped too
                    run.results[nid] = ExecutionResult(
                        node_id=nid,
                        status=ExecutionStatus.SKIPPED,
                        started_at=time.time(),
                        finished_at=time.time(),
                    )
                    skipped_nodes.add(nid)
                    pending.discard(nid)

            if not ready and pending:
                # Deadlock — should not happen if DAG valid
                run.status = ExecutionStatus.FAILED
                run.finished_at = time.time()
                return run

            # Execute ready nodes in parallel (up to semaphore limit)
            tasks = [self._execute_node(nid, workflow, data_map, run) for nid in ready]
            await asyncio.gather(*tasks, return_exceptions=True)

            for nid in ready:
                if run.results.get(nid, ExecutionResult(nid, ExecutionStatus.PENDING)).status == ExecutionStatus.SKIPPED:
                    skipped_nodes.add(nid)
                else:
                    executed.add(nid)
                pending.discard(nid)
                # Evaluate downstream edge conditions
                for e in workflow.get_downstream(nid):
                    if e.condition is None:
                        active_edges.add((e.source_id, e.target_id))
                    else:
                        # Evaluate condition against source node outputs
                        source_outputs = data_map.get(nid, {})
                        safe_globals = {"__builtins__": {}}
                        safe_locals = dict(source_outputs)
                        try:
                            cond_result = eval(e.condition, safe_globals, safe_locals)
                            if cond_result:
                                active_edges.add((e.source_id, e.target_id))
                        except Exception:
                            pass  # Condition error = edge inactive

        run.status = ExecutionStatus.SUCCESS
        run.finished_at = time.time()
        return run

    async def _execute_node(
        self,
        node_id: str,
        workflow: WorkflowDefinition,
        data_map: Dict[str, Dict[str, Any]],
        run: WorkflowRun,
    ) -> None:
        instance = workflow.nodes[node_id]
        spec = self.registry.get(instance.spec_id)

        result = ExecutionResult(
            node_id=node_id,
            status=ExecutionStatus.RUNNING,
            started_at=time.time(),
        )

        async with self.semaphore:
            try:
                # Collect inputs from upstream edges
                inputs = self._resolve_inputs(node_id, workflow, data_map, instance.config)

                # Resolve credentials
                creds = {}
                for cred_type in spec.credentials:
                    creds[cred_type] = await self.vault.retrieve(cred_type)

                # Build execution context
                ctx = ExecutionContext(
                    web2=self.web2,
                    web3=self.web3,
                    credentials=creds,
                    run_context=run.context,
                    node_config=instance.config,
                )

                # Execute with timeout
                if spec.execute_fn is None:
                    raise RuntimeError(f"Node {spec.id} has no execute function")

                raw_fn = spec.execute_fn
                if inspect.iscoroutinefunction(raw_fn):
                    outputs = await asyncio.wait_for(raw_fn(inputs, ctx), timeout=self.default_timeout)
                else:
                    outputs = raw_fn(inputs, ctx)

                result.outputs = outputs if isinstance(outputs, dict) else {"result": outputs}
                result.status = ExecutionStatus.SUCCESS
                data_map[node_id] = result.outputs

            except asyncio.TimeoutError:
                result.status = ExecutionStatus.TIMEOUT
                result.error = f"Timeout after {self.default_timeout}s"
            except Exception as exc:
                result.status = ExecutionStatus.FAILED
                result.error = str(exc)
                result.logs.append(f"Exception: {exc}")

            result.finished_at = time.time()
            run.results[node_id] = result

    def _resolve_inputs(
        self,
        node_id: str,
        workflow: WorkflowDefinition,
        data_map: Dict[str, Dict[str, Any]],
        node_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resolve input values dari upstream edges + config defaults."""
        inputs = {}
        spec = self.registry.get(workflow.nodes[node_id].spec_id)

        # Start dengan config values
        for port in spec.inputs:
            if port.name in node_config:
                inputs[port.name] = node_config[port.name]
            elif port.default is not None:
                inputs[port.name] = port.default

        # Override dengan upstream edge data
        for edge in workflow.get_upstream(node_id):
            if edge.source_id in data_map and edge.source_port in data_map[edge.source_id]:
                inputs[edge.target_port] = data_map[edge.source_id][edge.source_port]
        return inputs


@dataclass
class ExecutionContext:
    """Context yang dipass ke setiap node execute function."""
    web2: Web2Adapter
    web3: Web3Adapter
    credentials: Dict[str, Dict[str, Any]]
    run_context: Dict[str, Any]  # shared mutable context antar node
    node_config: Dict[str, Any]


# ────────────────────────────────────────────
# Workflow Builder (Programmatic Construction)
# ────────────────────────────────────────────

class WorkflowBuilder:
    """
    Fluent builder untuk membuat WorkflowDefinition secara programmatic.
    Equivalent drag-and-drop UI dalam kode Python.
    """

    def __init__(self, workflow_id: str, name: str, description: str = ""):
        self._wf = WorkflowDefinition(workflow_id, name, description)
        self._node_counter = 0

    def _next_id(self, spec_id: str) -> str:
        self._node_counter += 1
        return f"{spec_id}_{self._node_counter}"

    def add(self, spec_id: str, config: Optional[Dict[str, Any]] = None, is_trigger: bool = False) -> NodeInstance:
        nid = self._next_id(spec_id)
        instance = NodeInstance(
            instance_id=nid,
            spec_id=spec_id,
            config=config or {},
        )
        self._wf.add_node(instance, is_trigger=is_trigger)
        return instance

    def connect(
        self,
        source: Union[str, NodeInstance],
        source_port: str,
        target: Union[str, NodeInstance],
        target_port: str,
        condition: Optional[str] = None,
    ) -> WorkflowBuilder:
        sid = source.instance_id if isinstance(source, NodeInstance) else source
        tid = target.instance_id if isinstance(target, NodeInstance) else target
        self._wf.add_edge(Edge(sid, source_port, tid, target_port, condition))
        return self

    def build(self) -> WorkflowDefinition:
        return self._wf


# ────────────────────────────────────────────
# Built-in Node Library (Outerbridge-equivalent nodes)
# ────────────────────────────────────────────

class BuiltinNodes:
    """Factory untuk built-in nodes yang sering dipakai."""

    @staticmethod
    def http_request_node() -> NodeSpec:
        async def execute(inputs: Dict[str, Any], ctx: ExecutionContext) -> Dict[str, Any]:
            method = inputs.get("method", "GET")
            url = inputs.get("url", "")
            payload = inputs.get("payload")
            headers = inputs.get("headers", {})
            resp = await ctx.web2.call(method, url, payload, headers)
            return {"response": resp, "status": resp.get("status", 200)}

        return NodeSpec(
            id="http_request",
            name="HTTP Request",
            node_type=NodeType.WEB2,
            category="Web2",
            description="Make HTTP request to off-chain API",
            inputs=[
                Port("method", "str", True, "GET"),
                Port("url", "str", True),
                Port("payload", "dict", False, {}),
                Port("headers", "dict", False, {}),
            ],
            outputs=[Port("response", "dict"), Port("status", "int")],
            execute_fn=execute,
        )

    @staticmethod
    def web3_read_node() -> NodeSpec:
        async def execute(inputs: Dict[str, Any], ctx: ExecutionContext) -> Dict[str, Any]:
            address = inputs.get("contract_address", "")
            function = inputs.get("function", "")
            args = inputs.get("args", [])
            abi = inputs.get("abi", [])
            result = await ctx.web3.read_contract(address, abi, function, args)
            return {"result": result}

        return NodeSpec(
            id="web3_read",
            name="Web3 Read Contract",
            node_type=NodeType.WEB3,
            category="Web3",
            description="Read data from smart contract",
            inputs=[
                Port("contract_address", "str", True),
                Port("function", "str", True),
                Port("args", "list", False, []),
                Port("abi", "list", False, []),
            ],
            outputs=[Port("result", "Any")],
            execute_fn=execute,
        )

    @staticmethod
    def web3_write_node() -> NodeSpec:
        async def execute(inputs: Dict[str, Any], ctx: ExecutionContext) -> Dict[str, Any]:
            address = inputs.get("contract_address", "")
            function = inputs.get("function", "")
            args = inputs.get("args", [])
            abi = inputs.get("abi", [])
            creds = ctx.credentials.get("evm_wallet", {})
            pk = creds.get("private_key", "")
            tx_hash = await ctx.web3.write_contract(address, abi, function, args, pk)
            return {"tx_hash": tx_hash}

        return NodeSpec(
            id="web3_write",
            name="Web3 Write Contract",
            node_type=NodeType.WEB3,
            category="Web3",
            description="Write transaction to smart contract",
            inputs=[
                Port("contract_address", "str", True),
                Port("function", "str", True),
                Port("args", "list", False, []),
                Port("abi", "list", False, []),
            ],
            outputs=[Port("tx_hash", "str")],
            credentials=["evm_wallet"],
            execute_fn=execute,
        )

    @staticmethod
    def condition_node() -> NodeSpec:
        def execute(inputs: Dict[str, Any], ctx: ExecutionContext) -> Dict[str, Any]:
            expression = inputs.get("expression", "true")
            # Simplified: eval dengan restricted globals
            safe_globals = {"__builtins__": {}}
            safe_locals = {k: v for k, v in inputs.items() if k != "expression"}
            safe_locals.update(ctx.run_context)
            try:
                result = eval(expression, safe_globals, safe_locals)
            except Exception as exc:
                result = False
            return {"result": bool(result), "true": bool(result), "false": not bool(result)}

        return NodeSpec(
            id="condition",
            name="Condition",
            node_type=NodeType.CONDITION,
            category="Logic",
            description="Evaluate boolean expression and branch",
            inputs=[
                Port("expression", "str", True, "true"),
            ],
            outputs=[Port("result", "bool"), Port("true", "bool"), Port("false", "bool")],
            execute_fn=execute,
        )

    @staticmethod
    def transform_node() -> NodeSpec:
        def execute(inputs: Dict[str, Any], ctx: ExecutionContext) -> Dict[str, Any]:
            code = inputs.get("code", "output = input_data")
            input_data = inputs.get("input_data")
            local_vars = {"input_data": input_data, "ctx": ctx.run_context}
            safe_globals = {"__builtins__": {}}
            exec(compile(code, "<transform>", "exec"), safe_globals, local_vars)
            return {"output": local_vars.get("output", input_data)}

        return NodeSpec(
            id="transform",
            name="Transform",
            node_type=NodeType.ACTION,
            category="Utility",
            description="Transform data using Python snippet",
            inputs=[
                Port("input_data", "Any", True),
                Port("code", "str", True, "output = input_data"),
            ],
            outputs=[Port("output", "Any")],
            execute_fn=execute,
        )

    @staticmethod
    def delay_node() -> NodeSpec:
        async def execute(inputs: Dict[str, Any], ctx: ExecutionContext) -> Dict[str, Any]:
            seconds = float(inputs.get("seconds", 1))
            await asyncio.sleep(seconds)
            return {"done": True, "waited_seconds": seconds}

        return NodeSpec(
            id="delay",
            name="Delay",
            node_type=NodeType.ACTION,
            category="Utility",
            description="Wait for specified seconds",
            inputs=[Port("seconds", "float", True, 1.0)],
            outputs=[Port("done", "bool"), Port("waited_seconds", "float")],
            execute_fn=execute,
        )

    @staticmethod
    def merge_node() -> NodeSpec:
        def execute(inputs: Dict[str, Any], ctx: ExecutionContext) -> Dict[str, Any]:
            merged = {}
            for k, v in inputs.items():
                if isinstance(v, dict):
                    merged.update(v)
                else:
                    merged[k] = v
            return {"merged": merged}

        return NodeSpec(
            id="merge",
            name="Merge",
            node_type=NodeType.MERGE,
            category="Logic",
            description="Merge multiple input dictionaries",
            inputs=[Port("input_a", "Any", False), Port("input_b", "Any", False)],
            outputs=[Port("merged", "dict")],
            execute_fn=execute,
        )

    @staticmethod
    def log_node() -> NodeSpec:
        def execute(inputs: Dict[str, Any], ctx: ExecutionContext) -> Dict[str, Any]:
            message = inputs.get("message", "")
            level = inputs.get("level", "INFO")
            print(f"[{level}] {message}")
            return {"logged": True, "message": message}

        return NodeSpec(
            id="log",
            name="Log",
            node_type=NodeType.ACTION,
            category="Utility",
            description="Log message to console",
            inputs=[Port("message", "str", True), Port("level", "str", False, "INFO")],
            outputs=[Port("logged", "bool"), Port("message", "str")],
            execute_fn=execute,
        )

    @staticmethod
    def register_all(registry: NodeRegistry) -> None:
        registry.register(BuiltinNodes.http_request_node())
        registry.register(BuiltinNodes.web3_read_node())
        registry.register(BuiltinNodes.web3_write_node())
        registry.register(BuiltinNodes.condition_node())
        registry.register(BuiltinNodes.transform_node())
        registry.register(BuiltinNodes.delay_node())
        registry.register(BuiltinNodes.merge_node())
        registry.register(BuiltinNodes.log_node())


# ────────────────────────────────────────────
# Persistence Layer (MongoDB-compatible stub)
# ────────────────────────────────────────────

class WorkflowStore:
    """In-memory store untuk WorkflowDefinition & WorkflowRun."""

    def __init__(self):
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._runs: Dict[str, List[WorkflowRun]] = {}

    def save_workflow(self, wf: WorkflowDefinition) -> None:
        self._workflows[wf.workflow_id] = wf

    def load_workflow(self, workflow_id: str) -> WorkflowDefinition:
        if workflow_id not in self._workflows:
            raise KeyError(f"Workflow {workflow_id} not found")
        return self._workflows[workflow_id]

    def delete_workflow(self, workflow_id: str) -> None:
        self._workflows.pop(workflow_id, None)

    def list_workflows(self) -> List[str]:
        return list(self._workflows.keys())

    def save_run(self, run: WorkflowRun) -> None:
        self._runs.setdefault(run.workflow_id, []).append(run)

    def load_runs(self, workflow_id: str) -> List[WorkflowRun]:
        return self._runs.get(workflow_id, [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflows": len(self._workflows),
            "runs": sum(len(v) for v in self._runs.values()),
        }


# ────────────────────────────────────────────
# OuterbridgeKernel (Magnatrix Bridge)
# ────────────────────────────────────────────

class OuterbridgeKernel:
    """
    Entry point untuk menggunakan workflow engine dalam MAGNATRIX-OS.
    Menggabungkan registry, vault, engine, dan store dalam satu API.
    """

    def __init__(self):
        self.registry = NodeRegistry()
        self.vault = CredentialVault()
        self.store = WorkflowStore()
        self.engine = ExecutionEngine(self.registry, self.vault)
        BuiltinNodes.register_all(self.registry)

    def set_adapters(self, web2: Optional[Web2Adapter] = None, web3: Optional[Web3Adapter] = None) -> None:
        self.engine = ExecutionEngine(self.registry, self.vault, web2, web3)

    def create_builder(self, workflow_id: str, name: str, description: str = "") -> WorkflowBuilder:
        return WorkflowBuilder(workflow_id, name, description)

    async def run_workflow(self, workflow: WorkflowDefinition, trigger_data: Optional[Dict[str, Any]] = None) -> WorkflowRun:
        run = await self.engine.run(workflow, trigger_data)
        self.store.save_run(run)
        return run

    def save(self, workflow: WorkflowDefinition) -> None:
        self.store.save_workflow(workflow)

    def load(self, workflow_id: str) -> WorkflowDefinition:
        return self.store.load_workflow(workflow_id)

    def status(self) -> Dict[str, Any]:
        return {
            "registered_nodes": self.registry.count(),
            "categories": self.registry.list_categories(),
            "workflows": self.store.to_dict(),
            "vault_credentials": self.vault.to_dict(),
        }


# ────────────────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────────────────

def _demo() -> Dict[str, Any]:
    """Run a demo workflow to verify the engine."""
    kernel = OuterbridgeKernel()

    # Build a simple workflow: trigger → transform → condition → (log A / log B)
    builder = kernel.create_builder("demo_001", "Demo Web2/Web3 Bridge")

    trigger = builder.add("http_request", config={"method": "GET", "url": "https://api.example.com/price"}, is_trigger=True)
    transform = builder.add("transform", config={"code": "output = {'price': 100, 'threshold': 50}"})
    condition = builder.add("condition", config={"expression": "input_data['price'] > input_data['threshold']"})
    msg_high = builder.add("transform", config={"code": "output = 'Price is HIGH'"})
    msg_low = builder.add("transform", config={"code": "output = 'Price is LOW'"})
    log_high = builder.add("log", config={"level": "INFO"})
    log_low = builder.add("log", config={"level": "WARN"})

    builder.connect(trigger, "response", transform, "input_data")
    builder.connect(transform, "output", condition, "input_data")
    builder.connect(condition, "true", msg_high, "input_data", condition="true")
    builder.connect(condition, "false", msg_low, "input_data", condition="false")
    builder.connect(msg_high, "output", log_high, "message")
    builder.connect(msg_low, "output", log_low, "message")

    wf = builder.build()
    kernel.save(wf)

    # Run with async
    async def _run():
        run = await kernel.run_workflow(wf, trigger_data={"event": "price_check"})
        return {
            "run_id": run.run_id,
            "status": run.status.name,
            "results": {nid: {"status": r.status.name, "outputs": r.outputs, "error": r.error}
                        for nid, r in run.results.items()},
            "elapsed": run.finished_at - run.started_at,
        }

    return asyncio.run(_run())


if __name__ == "__main__":
    result = _demo()
    print(json.dumps(result, indent=2, default=str))
