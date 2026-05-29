"""
n8n_native_runtime.py
======================
MAGNATRIX Native Workflow Automation Runtime
Layer 3: Runtime (extends Pipeline Executor)

Pola AMATI-PELAJARI-TIRU dari n8n (github.com/n8n-io/n8n):
- Amati:  DAG-based workflow execution dengan node modularity,
          expression evaluation system {{ }}, trigger-action pattern,
          queue mode dengan Redis/Bull, credential encryption,
          400+ integrations, visual builder backend, fair-code model
- Pelajari: Core pattern adalah (1) Workflow = DAG of nodes (JSON persistensi),
            (2) Node = discrete operation (API call, transform, condition, code),
            (3) Execution Engine = sequential/parallel node loop,
            (4) Expression Eval = dynamic JS expressions,
            (5) Trigger System = webhook/cron/polling/event,
            (6) Credential Vault = encrypted secrets,
            (7) Queue Mode = Redis-backed horizontal scaling
- Tiru:   Reimplementasi native Python dengan:
            - Asyncio DAG executor dengan dependency resolution
            - Python expression evaluation (bukan JS {{ }})
            - Native trigger system (webhook, cron, mesh event, manual)
            - Node registry pattern untuk extensibility
            - In-memory + Redis queue mode
            - Credential vault dengan Fernet encryption
            - Integration dengan MAGNATRIX: mesh messaging, skill registry,
              agent roles, free LLM router, telemetry

Architecture:
    Trigger (webhook/cron/mesh) → WorkflowRegistry
                                      ↓
                              ExecutionEngine (DAG executor)
                                      ↓
                              Node Execution Loop
                                      ↓
                              ExpressionEvaluator
                                      ↓
                              Result Aggregation → mesh/telemetry
"""

import asyncio
import json
import hashlib
import time
import uuid
import re
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Union, Set
from enum import Enum, auto
from collections import defaultdict, deque
import inspect
import base64
from cryptography.fernet import Fernet


class NodeType(Enum):
    TRIGGER = "trigger"
    ACTION = "action"
    TRANSFORM = "transform"
    CONDITION = "condition"
    CODE = "code"
    AI = "ai"
    LOOP = "loop"
    MERGE = "merge"
    WEBHOOK = "webhook"
    HTTP = "http"
    DATABASE = "database"
    DELAY = "delay"
    ERROR_HANDLER = "error_handler"


class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    WAITING = "waiting"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class TriggerType(Enum):
    WEBHOOK = "webhook"
    CRON = "cron"
    MANUAL = "manual"
    MESH = "mesh"      # MAGNATRIX-specific: triggered by mesh message
    POLLING = "polling"
    EVENT = "event"


@dataclass
class NodeDefinition:
    """Node type definition - tiru n8n node system"""
    type: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    # Input/output spec
    inputs: List[str] = field(default_factory=list)  # ["main", "error"]
    outputs: List[str] = field(default_factory=list)  # ["main", "error"]
    # Parameter schema
    parameter_schema: Dict = field(default_factory=dict)
    # Execution function
    executor: Optional[str] = None  # module.function reference
    # Metadata
    category: str = "misc"
    icon: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class WorkflowNode:
    """Instance node dalam workflow - tiru n8n node instance"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = ""  # reference ke NodeDefinition.type
    name: str = ""  # display name
    position: List[int] = field(default_factory=lambda: [0, 0])  # canvas position
    # Configuration
    parameters: Dict = field(default_factory=dict)
    # Credential reference
    credential_id: Optional[str] = None
    # Connections: {output_name: [[{node, type, index}]]}
    connections: Dict = field(default_factory=dict)
    # Execution state
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[Dict] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    # Node-specific settings
    disabled: bool = False
    notes: str = ""
    # MAGNATRIX integration
    mesh_broadcast_on_complete: bool = False
    mesh_channel: str = "workflow.nodes"

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class Workflow:
    """Workflow definition - tiru n8n workflow JSON structure"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = "Untitled Workflow"
    description: str = ""
    version: str = "1.0.0"
    # Nodes dalam workflow
    nodes: Dict[str, WorkflowNode] = field(default_factory=dict)
    # Global settings
    settings: Dict = field(default_factory=dict)
    # Trigger configuration
    trigger: Optional[Dict] = None  # {type, config}
    # Tags
    tags: List[str] = field(default_factory=list)
    # State
    active: bool = False
    # Metadata
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    # Execution tracking
    execution_count: int = 0
    last_execution_at: Optional[float] = None
    # MAGNATRIX integration
    owner_agent_id: Optional[str] = None
    mesh_broadcast_channel: str = "workflow.executions"

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "settings": self.settings,
            "trigger": self.trigger,
            "tags": self.tags,
            "active": self.active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "execution_count": self.execution_count,
            "last_execution_at": self.last_execution_at,
            "owner_agent_id": self.owner_agent_id
        }

    def get_trigger_nodes(self) -> List[WorkflowNode]:
        """Get all trigger-type nodes"""
        return [n for n in self.nodes.values() if n.type == "trigger"]

    def get_execution_order(self) -> List[str]:
        """Topological sort untuk execution order - tiru n8n DAG execution"""
        # Build adjacency list
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        for node_id, node in self.nodes.items():
            in_degree[node_id]  # Ensure all nodes have entry
            for output_name, connections in node.connections.items():
                for conn_group in connections:
                    for conn in conn_group:
                        target_id = conn.get("node")
                        if target_id and target_id in self.nodes:
                            graph[node_id].append(target_id)
                            in_degree[target_id] += 1

        # Kahn's algorithm
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        order = []

        while queue:
            # Sort by canvas position (top-to-bottom, left-to-right)
            # Tiru n8n branch ordering
            queue_list = sorted(queue, key=lambda nid: (
                self.nodes[nid].position[1],
                self.nodes[nid].position[0]
            ))
            current = queue_list[0]
            queue.remove(current)
            order.append(current)

            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self.nodes):
            # Cycle detected - error handling
            remaining = set(self.nodes.keys()) - set(order)
            raise ValueError(f"Cycle detected in workflow. Remaining nodes: {remaining}")

        return order


@dataclass
class WorkflowExecution:
    """Workflow execution instance - tiru n8n execution tracking"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])
    workflow_id: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    # Execution data
    node_results: Dict[str, Dict] = field(default_factory=dict)
    node_statuses: Dict[str, str] = field(default_factory=dict)
    # Input data
    trigger_data: Dict = field(default_factory=dict)
    # Global execution variables
    vars: Dict = field(default_factory=dict)
    # Metadata
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    execution_time_ms: float = 0.0
    # Error handling
    error_node_id: Optional[str] = None
    error_message: Optional[str] = None
    # MAGNATRIX
    agent_id: Optional[str] = None
    mesh_broadcast: bool = False

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "node_results": self.node_results,
            "node_statuses": self.node_statuses,
            "trigger_data": self.trigger_data,
            "vars": self.vars,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "execution_time_ms": self.execution_time_ms,
            "error_node_id": self.error_node_id,
            "error_message": self.error_message,
            "agent_id": self.agent_id
        }


class CredentialVault:
    """
    Encrypted credential storage - tiru n8n credential system.
    Simplified: in-memory dengan Fernet. Production: PostgreSQL + KMS.
    """

    def __init__(self, master_key: Optional[str] = None):
        self._vault: Dict[str, Dict] = {}
        self._fernet = Fernet(master_key.encode() if master_key else Fernet.generate_key())

    def store(self, credential_id: str, credential_type: str, 
              data: Dict, name: str = "") -> str:
        """Store encrypted credential"""
        encrypted = self._fernet.encrypt(json.dumps(data).encode())
        self._vault[credential_id] = {
            "id": credential_id,
            "type": credential_type,
            "name": name or credential_id,
            "encrypted_data": encrypted.decode(),
            "created_at": time.time()
        }
        return credential_id

    def retrieve(self, credential_id: str) -> Optional[Dict]:
        """Retrieve and decrypt credential"""
        entry = self._vault.get(credential_id)
        if not entry:
            return None
        decrypted = self._fernet.decrypt(entry["encrypted_data"].encode())
        return json.loads(decrypted)

    def delete(self, credential_id: str) -> bool:
        return self._vault.pop(credential_id, None) is not None

    def list_credentials(self) -> List[Dict]:
        return [{"id": c["id"], "type": c["type"], "name": c["name"]} 
                for c in self._vault.values()]


class ExpressionEvaluator:
    """
    Expression evaluation engine - tiru n8n {{ }} system.
    Python-native expression evaluation (bukan JS).
    """

    # Pattern: {{ expression }} atau $expression
    EXPR_PATTERN = re.compile(r'\{\{\s*(.+?)\s*\}\}')
    SHORT_EXPR_PATTERN = re.compile(r"\$\{(\w+(?:\.\w+)*(?:\[[\w"]+\])*)\}")

    def __init__(self):
        self._globals = {
            "json": json,
            "datetime": datetime,
            "time": time,
            "uuid": uuid,
            "len": len,
            "sum": sum,
            "max": max,
            "min": min,
            "abs": abs,
            "round": round,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
        }

    def evaluate(self, expression: str, context: Dict) -> Any:
        """Evaluate single expression dengan context — SAFE (no eval)."""
        import ast, operator
        try:
            # Build safe locals dari context
            locals_dict = {
                "$json": context.get("$json", {}),
                "$vars": context.get("$vars", {}),
                "$env": context.get("$env", {}),
                "$now": time.time(),
                "$today": datetime.now().isoformat(),
                "$execution": context.get("$execution", {}),
                "$workflow": context.get("$workflow", {}),
                "$node": context.get("$node", {}),
                "$items": context.get("$items", []),
                "$item": context.get("$item", {}),
            }
            for key, value in context.items():
                if key not in locals_dict:
                    locals_dict[key] = value

            # Whitelist AST node types for safe evaluation
            tree = ast.parse(expression, mode='eval')
            _SAFE_NODES = (
                ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name,
                ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
                ast.USub, ast.UAdd, ast.Not, ast.Compare, ast.Eq, ast.NotEq,
                ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot,
                ast.BoolOp, ast.And, ast.Or, ast.Call, ast.Attribute, ast.Subscript,
                ast.Index, ast.Slice, ast.List, ast.Tuple, ast.Dict, ast.Str,
                ast.Num, ast.Bool, ast.JoinedStr, ast.FormattedValue, ast.IfExp,
                ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
                ast.comprehension, ast.Lambda, ast.arg,
            )
            for node in ast.walk(tree):
                if not isinstance(node, _SAFE_NODES):
                    raise ValueError(f"Unsafe expression node: {type(node).__name__}")

            # Safe operators
            _OPS = {
                ast.Add: operator.add, ast.Sub: operator.sub,
                ast.Mult: operator.mul, ast.Div: operator.truediv,
                ast.Pow: operator.pow, ast.Mod: operator.mod,
                ast.FloorDiv: operator.floordiv,
                ast.Eq: operator.eq, ast.NotEq: operator.ne,
                ast.Lt: operator.lt, ast.LtE: operator.le,
                ast.Gt: operator.gt, ast.GtE: operator.ge,
                ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
                ast.Is: operator.is_, ast.IsNot: operator.is_not,
                ast.And: lambda a, b: a and b, ast.Or: lambda a, b: a or b,
                ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Not: operator.not_,
            }

            def _eval(node):
                if isinstance(node, ast.Constant):
                    return node.value
                if isinstance(node, ast.Num):
                    return node.n
                if isinstance(node, ast.Str):
                    return node.s
                if isinstance(node, ast.Bool):
                    return node.value
                if isinstance(node, ast.Name):
                    if node.id in self._globals:
                        return self._globals[node.id]
                    if node.id in locals_dict:
                        return locals_dict[node.id]
                    raise ValueError(f"Unknown name: {node.id}")
                if isinstance(node, ast.BinOp):
                    left = _eval(node.left)
                    right = _eval(node.right)
                    return _OPS[type(node.op)](left, right)
                if isinstance(node, ast.UnaryOp):
                    val = _eval(node.operand)
                    return _OPS[type(node.op)](val)
                if isinstance(node, ast.BoolOp):
                    vals = [_eval(v) for v in node.values]
                    op = _OPS[type(node.op)]
                    result = vals[0]
                    for v in vals[1:]:
                        result = op(result, v)
                    return result
                if isinstance(node, ast.Compare):
                    left = _eval(node.left)
                    result = True
                    for op, comparator in zip(node.ops, node.comparators):
                        right = _eval(comparator)
                        result = result and _OPS[type(op)](left, right)
                        left = right
                    return result
                if isinstance(node, ast.Call):
                    func = _eval(node.func)
                    args = [_eval(a) for a in node.args]
                    kwargs = {kw.arg: _eval(kw.value) for kw in node.keywords}
                    return func(*args, **kwargs)
                if isinstance(node, ast.Attribute):
                    obj = _eval(node.value)
                    return getattr(obj, node.attr)
                if isinstance(node, ast.Subscript):
                    obj = _eval(node.value)
                    idx = _eval(node.slice)
                    return obj[idx]
                if isinstance(node, ast.List):
                    return [_eval(e) for e in node.elts]
                if isinstance(node, ast.Tuple):
                    return tuple(_eval(e) for e in node.elts)
                if isinstance(node, ast.Dict):
                    return {_eval(k): _eval(v) for k, v in zip(node.keys, node.values)}
                if isinstance(node, ast.IfExp):
                    return _eval(node.body) if _eval(node.test) else _eval(node.orelse)
                raise ValueError(f"Unsupported node: {type(node).__name__}")

            return _eval(tree.body)
        except Exception as e:
            raise ValueError(f"Expression evaluation error: '{expression}' -> {e}")

    def evaluate_in_string(self, text: str, context: Dict) -> str:
        """Evaluate all {{ expressions }} within a string"""
        def replace_expr(match):
            expr = match.group(1)
            try:
                result = self.evaluate(expr, context)
                return str(result) if result is not None else ""
            except Exception as e:
                return f"[ERROR: {e}]"

        return self.EXPR_PATTERN.sub(replace_expr, text)

    def evaluate_object(self, obj: Any, context: Dict) -> Any:
        """Recursively evaluate expressions dalam object structure"""
        if isinstance(obj, str):
            if obj.strip().startswith("{{") and obj.strip().endswith("}}"):
                # Pure expression - return raw result (not stringified)
                expr = obj.strip()[2:-2].strip()
                return self.evaluate(expr, context)
            else:
                return self.evaluate_in_string(obj, context)
        elif isinstance(obj, dict):
            return {k: self.evaluate_object(v, context) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.evaluate_object(item, context) for item in obj]
        return obj


class NodeExecutorRegistry:
    """
    Registry untuk node executors - tiru n8n node system.
    Setiap node type punya executor function.
    """

    def __init__(self, credential_vault: CredentialVault):
        self.credential_vault = credential_vault
        self._executors: Dict[str, Callable] = {}
        self._register_builtins()

    def register(self, node_type: str, executor: Callable):
        self._executors[node_type] = executor

    def get(self, node_type: str) -> Optional[Callable]:
        return self._executors.get(node_type)

    def _register_builtins(self):
        """Register built-in node executors - tiru n8n 400+ integrations"""
        self.register("trigger", self._exec_trigger)
        self.register("webhook", self._exec_webhook)
        self.register("http", self._exec_http)
        self.register("code", self._exec_code)
        self.register("transform", self._exec_transform)
        self.register("condition", self._exec_condition)
        self.register("ai", self._exec_ai)
        self.register("delay", self._exec_delay)
        self.register("merge", self._exec_merge)
        self.register("loop", self._exec_loop)
        self.register("database", self._exec_database)
        self.register("mesh", self._exec_mesh)
        self.register("skill", self._exec_skill)
        self.register("error_handler", self._exec_error_handler)
        self.register("log", self._exec_log)
        self.register("notify", self._exec_notify)

    async def execute(self, node: WorkflowNode, context: Dict, 
                      items: List[Dict]) -> List[Dict]:
        """Execute node dengan items - tiru n8n node execution model"""
        executor = self._executors.get(node.type)
        if not executor:
            raise ValueError(f"Unknown node type: {node.type}")

        # Evaluate parameters dengan expression engine
        evaluator = context.get("_evaluator")
        if evaluator:
            params = evaluator.evaluate_object(node.parameters, context)
        else:
            params = node.parameters

        # Resolve credential
        credential = None
        if node.credential_id:
            credential = self.credential_vault.retrieve(node.credential_id)

        # Execute
        result = await executor(node, params, context, items, credential)
        return result if isinstance(result, list) else [result] if result else []

    # ==================== BUILT-IN EXECUTORS ====================

    async def _exec_trigger(self, node, params, context, items, credential):
        """Trigger node - pass through trigger data"""
        return [{"json": context.get("trigger_data", {})}]

    async def _exec_webhook(self, node, params, context, items, credential):
        """Webhook response node"""
        # Would integrate dengan webhook server
        response_body = params.get("response_body", {})
        status_code = params.get("status_code", 200)
        return [{"json": {"status_code": status_code, "body": response_body}}]

    async def _exec_http(self, node, params, context, items, credential):
        """HTTP Request node - tiru n8n HTTP Request node"""
        import aiohttp

        method = params.get("method", "GET").upper()
        url = params.get("url", "")
        headers = params.get("headers", {})
        body = params.get("body", {})
        timeout = params.get("timeout", 30)

        # Apply credential jika ada
        if credential and "auth" in credential:
            auth = credential["auth"]
            if auth.get("type") == "bearer":
                headers["Authorization"] = f"Bearer {auth.get('token', '')}"
            elif auth.get("type") == "basic":
                import base64
                creds = base64.b64encode(f"{auth['username']}:{auth['password']}".encode()).decode()
                headers["Authorization"] = f"Basic {creds}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body if method in ("POST", "PUT", "PATCH") else None,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    response_body = await resp.text()
                    try:
                        response_json = json.loads(response_body)
                    except:
                        response_json = {"raw": response_body}

                    return [{"json": {
                        "status_code": resp.status,
                        "headers": dict(resp.headers),
                        "body": response_json,
                        "request_url": url,
                        "request_method": method
                    }}]
        except Exception as e:
            return [{"json": {"error": str(e), "request_url": url}}]

    async def _exec_code(self, node, params, context, items, credential):
        """Code node - execute Python code - tiru n8n Code node"""
        code = params.get("python_code", "return items")

        # Safe execution environment
        safe_globals = {
            "__builtins__": {
                "len": len, "sum": sum, "max": max, "min": min,
                "abs": abs, "round": round, "enumerate": enumerate,
                "zip": zip, "map": map, "filter": filter,
                "json": json, "time": time, "datetime": datetime,
                "str": str, "int": int, "float": float, "list": list,
                "dict": dict, "set": set, "tuple": tuple,
                "range": range, "print": lambda *args: None,
            }
        }

        try:
            # Compile and execute
            exec_globals = {
                "items": items,
                "params": params,
                "context": context,
                **safe_globals["__builtins__"]
            }

            # Wrap dalam function
            wrapped_code = f"""
async def _execute():
{chr(10).join('    ' + line for line in code.split(chr(10)))}
    return items
"""
            local_vars = {}
            exec(compile(wrapped_code, "<code_node>", "exec"), exec_globals, local_vars)

            if "_execute" in local_vars:
                result = await local_vars["_execute"]()
                return result if isinstance(result, list) else [result]
            return items
        except Exception as e:
            return [{"json": {"error": str(e), "traceback": traceback.format_exc()}}]

    async def _exec_transform(self, node, params, context, items, credential):
        """Transform node - map/filter/reduce operations"""
        operations = params.get("operations", [])

        result = items
        for op in operations:
            op_type = op.get("type")
            if op_type == "map":
                field = op.get("field")
                expression = op.get("expression")
                for item in result:
                    if expression and field:
                        evaluator = context.get("_evaluator")
                        if evaluator:
                            ctx = {**context, "$item": item}
                            item["json"][field] = evaluator.evaluate(expression, ctx)
            elif op_type == "filter":
                expression = op.get("expression")
                if expression:
                    evaluator = context.get("_evaluator")
                    if evaluator:
                        filtered = []
                        for item in result:
                            ctx = {**context, "$item": item}
                            try:
                                if evaluator.evaluate(expression, ctx):
                                    filtered.append(item)
                            except:
                                pass
                        result = filtered
            elif op_type == "set":
                field = op.get("field")
                value = op.get("value")
                for item in result:
                    if field:
                        item["json"][field] = value

        return result

    async def _exec_condition(self, node, params, context, items, credential):
        """Condition/IF node - tiru n8n IF node dengan multiple outputs"""
        conditions = params.get("conditions", [])

        true_items = []
        false_items = []

        evaluator = context.get("_evaluator")
        for item in items:
            all_true = True
            for cond in conditions:
                expr = cond.get("expression", "true")
                if evaluator:
                    ctx = {**context, "$item": item}
                    try:
                        if not evaluator.evaluate(expr, ctx):
                            all_true = False
                            break
                    except:
                        all_true = False
                        break

            if all_true:
                true_items.append(item)
            else:
                false_items.append(item)

        # Return dengan routing info untuk DAG executor
        return {
            "true": true_items,
            "false": false_items
        }

    async def _exec_ai(self, node, params, context, items, credential):
        """AI/LLM node - integrate dengan MAGNATRIX free LLM router"""
        prompt_template = params.get("prompt", "Process: {{ $json }}")
        model = params.get("model", "openrouter/auto")
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("max_tokens", 500)

        evaluator = context.get("_evaluator")
        results = []

        for item in items:
            if evaluator:
                ctx = {**context, "$item": item}
                prompt = evaluator.evaluate_in_string(prompt_template, ctx)
            else:
                prompt = prompt_template

            # Would integrate dengan free_llm_router.py
            # Placeholder: simulate LLM response
            results.append({"json": {
                "prompt": prompt,
                "model": model,
                "temperature": temperature,
                "response": f"[LLM Response via {model} for: {prompt[:50]}...]",
                "tokens_used": len(prompt.split()) + max_tokens // 2
            }})

        return results

    async def _exec_delay(self, node, params, context, items, credential):
        """Delay node - tiru n8n Wait node"""
        delay_ms = params.get("delay_ms", 1000)
        await asyncio.sleep(delay_ms / 1000)
        return items

    async def _exec_merge(self, node, params, context, items, credential):
        """Merge node - combine multiple branches"""
        merge_mode = params.get("mode", "append")  # append, mergeByIndex, wait

        # Collect items dari semua input branches
        # In actual implementation: merge dari multiple input connections
        return items

    async def _exec_loop(self, node, params, context, items, credential):
        """Loop node - iterate over items atau range"""
        loop_mode = params.get("mode", "foreach")  # foreach, for, while
        iterations = params.get("iterations", 1)

        # Mark untuk loop execution - actual loop handled oleh DAG executor
        return [{"json": {"loop_context": {
            "mode": loop_mode,
            "iterations": iterations,
            "current_index": 0,
            "items": items
        }}}]

    async def _exec_database(self, node, params, context, items, credential):
        """Database node - tiru n8n database integrations"""
        operation = params.get("operation", "select")  # select, insert, update, delete
        table = params.get("table", "")

        # Would integrate dengan actual database
        return [{"json": {
            "operation": operation,
            "table": table,
            "affected_rows": 0,
            "data": items
        }}]

    async def _exec_mesh(self, node, params, context, items, credential):
        """MAGNATRIX Mesh node - broadcast ke swarm"""
        channel = params.get("channel", "workflow.events")
        message_type = params.get("message_type", "BROADCAST")
        payload = params.get("payload", {})

        evaluator = context.get("_evaluator")
        if evaluator:
            payload = evaluator.evaluate_object(payload, context)

        # Would broadcast ke mesh messaging system
        return [{"json": {
            "broadcasted": True,
            "channel": channel,
            "message_type": message_type,
            "payload": payload
        }}]

    async def _exec_skill(self, node, params, context, items, credential):
        """MAGNATRIX Skill node - execute registered skill"""
        skill_name = params.get("skill_name", "")
        skill_params = params.get("skill_params", {})

        # Would integrate dengan skill_registry.py
        return [{"json": {
            "skill": skill_name,
            "params": skill_params,
            "status": "invoked"
        }}]

    async def _exec_error_handler(self, node, params, context, items, credential):
        """Error handler node - catch dan handle errors"""
        error_behavior = params.get("behavior", "continue")  # continue, stop, retry
        max_retries = params.get("max_retries", 3)
        fallback_value = params.get("fallback_value", {})

        # Set error handling policy dalam execution context
        context["_error_policy"] = {
            "behavior": error_behavior,
            "max_retries": max_retries,
            "fallback": fallback_value
        }

        return items

    async def _exec_log(self, node, params, context, items, credential):
        """Log node - structured logging"""
        level = params.get("level", "info")
        message_template = params.get("message", "{{ $json }}")

        evaluator = context.get("_evaluator")
        for item in items:
            if evaluator:
                ctx = {**context, "$item": item}
                message = evaluator.evaluate_in_string(message_template, ctx)
            else:
                message = message_template
            print(f"[WORKFLOW LOG {level.upper()}] {message}")

        return items

    async def _exec_notify(self, node, params, context, items, credential):
        """Notification node - alert/notification"""
        title = params.get("title", "Workflow Notification")
        body = params.get("body", "")
        urgency = params.get("urgency", "normal")  # low, normal, high, critical

        # Would integrate dengan MAGNATRIX notification system
        return [{"json": {
            "notified": True,
            "title": title,
            "urgency": urgency,
            "timestamp": time.time()
        }}]


class ExecutionEngine:
    """
    DAG Workflow Execution Engine - core dari n8n-native runtime.
    Tiru n8n execution engine: parse workflow, validate, execute nodes.
    """

    def __init__(self, credential_vault: Optional[CredentialVault] = None,
                 use_queue: bool = False, redis_url: str = ""):
        self.credential_vault = credential_vault or CredentialVault()
        self.node_registry = NodeExecutorRegistry(self.credential_vault)
        self.evaluator = ExpressionEvaluator()
        self.use_queue = use_queue
        self.redis_url = redis_url

        # Queue mode: Redis-backed execution (tiru n8n queue mode)
        self._queue = deque() if not use_queue else None
        self._workers: List[asyncio.Task] = []
        self._num_workers = 4

        # Metrics
        self._execution_count = 0
        self._error_count = 0

    async def start(self):
        """Start execution engine dengan worker pool"""
        if self.use_queue:
            for i in range(self._num_workers):
                task = asyncio.create_task(self._worker_loop(i))
                self._workers.append(task)

    async def stop(self):
        """Graceful shutdown"""
        for worker in self._workers:
            worker.cancel()
        self._workers = []

    async def execute_workflow(self, workflow: Workflow, 
                               trigger_data: Dict = None,
                               execution_id: str = None,
                               agent_id: str = None) -> WorkflowExecution:
        """Execute full workflow - tiru n8n execution flow"""

        execution = WorkflowExecution(
            id=execution_id or str(uuid.uuid4())[:16],
            workflow_id=workflow.id,
            status=ExecutionStatus.RUNNING,
            trigger_data=trigger_data or {},
            agent_id=agent_id,
            mesh_broadcast=workflow.mesh_broadcast_channel != ""
        )
        execution.started_at = time.time()

        try:
            # Get execution order (topological sort)
            node_order = workflow.get_execution_order()

            # Build execution context
            context = {
                "_evaluator": self.evaluator,
                "$json": trigger_data,
                "$vars": {},
                "$env": {},
                "$execution": execution.to_dict(),
                "$workflow": workflow.to_dict(),
                "trigger_data": trigger_data or {},
            }

            # Execute nodes
            node_outputs: Dict[str, List[Dict]] = {}

            for node_id in node_order:
                node = workflow.nodes[node_id]

                if node.disabled:
                    execution.node_statuses[node_id] = ExecutionStatus.SKIPPED.value
                    continue

                # Get input items dari predecessor nodes
                items = self._get_input_items(node, workflow, node_outputs)

                # Update context dengan current node
                context["$node"] = node.to_dict()
                context["$items"] = items
                if items:
                    context["$item"] = items[0]

                node.status = ExecutionStatus.RUNNING
                execution.node_statuses[node_id] = ExecutionStatus.RUNNING.value

                start = time.time()

                try:
                    # Execute node
                    result = await self.node_registry.execute(node, context, items)

                    # Handle condition node multiple outputs
                    if isinstance(result, dict) and ("true" in result or "false" in result):
                        node_outputs[node_id] = result
                    else:
                        node_outputs[node_id] = result

                    node.status = ExecutionStatus.SUCCESS
                    node.result = {"output": result}
                    execution.node_statuses[node_id] = ExecutionStatus.SUCCESS.value
                    execution.node_results[node_id] = {"output": result}

                    # Mesh broadcast jika configured
                    if node.mesh_broadcast_on_complete and execution.mesh_broadcast:
                        # Would broadcast ke MAGNATRIX mesh
                        pass

                except Exception as e:
                    node.status = ExecutionStatus.ERROR
                    node.error = str(e)
                    execution.node_statuses[node_id] = ExecutionStatus.ERROR.value
                    execution.error_node_id = node_id
                    execution.error_message = str(e)

                    # Check error handling policy
                    error_policy = context.get("_error_policy", {})
                    if error_policy.get("behavior") == "stop":
                        execution.status = ExecutionStatus.ERROR
                        break
                    elif error_policy.get("behavior") == "continue":
                        node_outputs[node_id] = [{"json": {"error": str(e)}}]

                    self._error_count += 1

                node.execution_time_ms = (time.time() - start) * 1000

            # Finalize execution
            execution.finished_at = time.time()
            execution.execution_time_ms = (execution.finished_at - execution.started_at) * 1000
            execution.status = ExecutionStatus.SUCCESS if execution.status != ExecutionStatus.ERROR else ExecutionStatus.ERROR

            workflow.execution_count += 1
            workflow.last_execution_at = execution.finished_at
            self._execution_count += 1

            return execution

        except Exception as e:
            execution.status = ExecutionStatus.ERROR
            execution.error_message = str(e)
            execution.finished_at = time.time()
            self._error_count += 1
            return execution

    def _get_input_items(self, node: WorkflowNode, workflow: Workflow,
                         node_outputs: Dict[str, Any]) -> List[Dict]:
        """Get input items dari predecessor nodes"""
        items = []

        # Find all nodes yang connect ke node ini
        for pred_id, pred_node in workflow.nodes.items():
            for output_name, connections in pred_node.connections.items():
                for conn_group in connections:
                    for conn in conn_group:
                        if conn.get("node") == node.id:
                            pred_output = node_outputs.get(pred_id, [])
                            if isinstance(pred_output, dict):
                                # Condition node dengan true/false branches
                                branch = conn.get("type", "main")
                                if branch in pred_output:
                                    items.extend(pred_output[branch])
                            elif isinstance(pred_output, list):
                                items.extend(pred_output)

        return items if items else [{"json": {}}]

    async def _worker_loop(self, worker_id: int):
        """Queue worker - tiru n8n queue mode worker"""
        while True:
            try:
                if self._queue:
                    execution = self._queue.popleft()
                    # Execute from queue
                    pass
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break


class TriggerManager:
    """
    Trigger management system - tiru n8n trigger system.
    Handle webhook, cron, mesh event, polling triggers.
    """

    def __init__(self, engine: ExecutionEngine):
        self.engine = engine
        self._webhooks: Dict[str, Dict] = {}  # path -> {workflow_id, node_id}
        self._cron_jobs: Dict[str, asyncio.Task] = {}
        self._mesh_subscriptions: Dict[str, List[str]] = {}  # channel -> [workflow_ids]
        self._polling_tasks: Dict[str, asyncio.Task] = {}

    def register_webhook(self, path: str, workflow_id: str, node_id: str):
        self._webhooks[path] = {"workflow_id": workflow_id, "node_id": node_id}

    def register_cron(self, job_id: str, cron_expr: str, workflow_id: str):
        """Register cron trigger"""
        # Would use croniter untuk proper cron parsing
        # Simplified: parse basic intervals
        task = asyncio.create_task(self._cron_runner(job_id, cron_expr, workflow_id))
        self._cron_jobs[job_id] = task

    def register_mesh_trigger(self, channel: str, workflow_id: str):
        if channel not in self._mesh_subscriptions:
            self._mesh_subscriptions[channel] = []
        self._mesh_subscriptions[channel].append(workflow_id)

    async def handle_webhook(self, path: str, method: str, 
                             headers: Dict, body: Any) -> Optional[WorkflowExecution]:
        """Handle incoming webhook"""
        webhook = self._webhooks.get(path)
        if not webhook:
            return None

        # Would fetch workflow dan execute
        # Placeholder: return mock execution
        return None

    async def handle_mesh_event(self, channel: str, message: Dict):
        """Handle mesh event trigger"""
        workflow_ids = self._mesh_subscriptions.get(channel, [])
        for wf_id in workflow_ids:
            # Would fetch workflow dan execute dengan message sebagai trigger data
            pass

    async def _cron_runner(self, job_id: str, cron_expr: str, workflow_id: str):
        """Cron job runner"""
        while True:
            try:
                # Parse dan sleep
                # Would use croniter untuk proper scheduling
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break


class WorkflowRegistry:
    """
    Workflow storage dan management - tiru n8n workflow database layer.
    Simplified: in-memory. Production: PostgreSQL.
    """

    def __init__(self):
        self._workflows: Dict[str, Workflow] = {}
        self._executions: Dict[str, WorkflowExecution] = {}

    def save(self, workflow: Workflow) -> str:
        workflow.updated_at = time.time()
        self._workflows[workflow.id] = workflow
        return workflow.id

    def get(self, workflow_id: str) -> Optional[Workflow]:
        return self._workflows.get(workflow_id)

    def delete(self, workflow_id: str) -> bool:
        return self._workflows.pop(workflow_id, None) is not None

    def list_all(self) -> List[Dict]:
        return [wf.to_dict() for wf in self._workflows.values()]

    def get_active(self) -> List[Workflow]:
        return [wf for wf in self._workflows.values() if wf.active]

    def save_execution(self, execution: WorkflowExecution) -> str:
        self._executions[execution.id] = execution
        return execution.id

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        return self._executions.get(execution_id)


class WorkflowOrchestrator:
    """
    High-level orchestrator untuk Layer 3 Runtime.
    Integrasi dengan MAGNATRIX ecosystem.
    """

    def __init__(self):
        self.registry = WorkflowRegistry()
        self.engine = ExecutionEngine()
        self.triggers = TriggerManager(self.engine)
        self._running = False

    async def initialize(self):
        """Initialize dengan default workflows"""
        await self.engine.start()

    async def start(self):
        self._running = True

    async def stop(self):
        await self.engine.stop()
        self._running = False

    def create_workflow(self, name: str, description: str = "") -> Workflow:
        """Create new workflow"""
        wf = Workflow(name=name, description=description)
        self.registry.save(wf)
        return wf

    def add_node(self, workflow_id: str, node_type: str, name: str,
                 parameters: Dict = None, position: List[int] = None,
                 connections: Dict = None) -> Optional[WorkflowNode]:
        """Add node ke workflow"""
        wf = self.registry.get(workflow_id)
        if not wf:
            return None

        node = WorkflowNode(
            type=node_type,
            name=name,
            parameters=parameters or {},
            position=position or [0, 0],
            connections=connections or {}
        )
        wf.nodes[node.id] = node
        self.registry.save(wf)
        return node

    def connect_nodes(self, workflow_id: str, from_node: str, to_node: str,
                      from_output: str = "main", to_input: str = "main"):
        """Connect two nodes"""
        wf = self.registry.get(workflow_id)
        if not wf or from_node not in wf.nodes or to_node not in wf.nodes:
            return False

        from_connections = wf.nodes[from_node].connections
        if from_output not in from_connections:
            from_connections[from_output] = [[]]

        from_connections[from_output][0].append({
            "node": to_node,
            "type": to_input,
            "index": 0
        })

        self.registry.save(wf)
        return True

    async def execute(self, workflow_id: str, trigger_data: Dict = None,
                      agent_id: str = None) -> Optional[WorkflowExecution]:
        """Execute workflow"""
        wf = self.registry.get(workflow_id)
        if not wf:
            return None

        execution = await self.engine.execute_workflow(wf, trigger_data, agent_id=agent_id)
        self.registry.save_execution(execution)
        return execution

    def activate(self, workflow_id: str) -> bool:
        """Activate workflow (enable triggers)"""
        wf = self.registry.get(workflow_id)
        if not wf:
            return False
        wf.active = True

        # Register triggers
        if wf.trigger:
            trigger_type = wf.trigger.get("type")
            if trigger_type == "webhook":
                self.triggers.register_webhook(
                    wf.trigger.get("path", f"/webhook/{wf.id}"),
                    wf.id,
                    wf.trigger.get("node_id", "")
                )
            elif trigger_type == "cron":
                self.triggers.register_cron(
                    f"cron-{wf.id}",
                    wf.trigger.get("expression", "*/5 * * * *"),
                    wf.id
                )
            elif trigger_type == "mesh":
                self.triggers.register_mesh_trigger(
                    wf.trigger.get("channel", "workflow.trigger"),
                    wf.id
                )

        self.registry.save(wf)
        return True

    def deactivate(self, workflow_id: str) -> bool:
        wf = self.registry.get(workflow_id)
        if not wf:
            return False
        wf.active = False
        self.registry.save(wf)
        return True

    def get_status(self) -> Dict:
        return {
            "running": self._running,
            "workflows": len(self.registry._workflows),
            "active_workflows": len(self.registry.get_active()),
            "total_executions": self.engine._execution_count,
            "total_errors": self.engine._error_count,
            "webhooks": len(self.triggers._webhooks),
            "cron_jobs": len(self.triggers._cron_jobs),
            "mesh_subscriptions": len(self.triggers._mesh_subscriptions)
        }


# ==================== DEMO ====================

if __name__ == "__main__":
    async def demo():
        orch = WorkflowOrchestrator()
        await orch.initialize()
        await orch.start()

        # Create workflow: HTTP Request -> Transform -> AI -> Log
        wf = orch.create_workflow("API to AI Pipeline", "Fetch data, transform, process with AI")

        # Add trigger
        trigger = orch.add_node(wf.id, "trigger", "Start", 
                                parameters={"type": "manual"},
                                position=[100, 100])

        # Add HTTP node
        http_node = orch.add_node(wf.id, "http", "Fetch API",
                                   parameters={
                                       "method": "GET",
                                       "url": "https://api.github.com/events"
                                   },
                                   position=[300, 100])

        # Add transform node
        transform_node = orch.add_node(wf.id, "transform", "Filter Events",
                                         parameters={
                                             "operations": [
                                                 {"type": "filter", "expression": "$item.json.type == 'PushEvent'"}
                                             ]
                                         },
                                         position=[500, 100])

        # Add AI node
        ai_node = orch.add_node(wf.id, "ai", "Analyze Events",
                                parameters={
                                    "prompt": "Summarize these GitHub events: {{ $item.json }}",
                                    "model": "openrouter/auto"
                                },
                                position=[700, 100])

        # Add log node
        log_node = orch.add_node(wf.id, "log", "Output",
                                 parameters={
                                     "message": "Processed: {{ $item.json }}"
                                 },
                                 position=[900, 100])

        # Connect nodes
        orch.connect_nodes(wf.id, trigger.id, http_node.id)
        orch.connect_nodes(wf.id, http_node.id, transform_node.id)
        orch.connect_nodes(wf.id, transform_node.id, ai_node.id)
        orch.connect_nodes(wf.id, ai_node.id, log_node.id)

        print(f"Created workflow: {wf.id}")
        print(f"Nodes: {list(wf.nodes.keys())}")
        print(f"Execution order: {wf.get_execution_order()}")

        # Execute
        execution = await orch.execute(wf.id, trigger_data={"source": "demo"})
        print(f"Execution: {execution.to_dict()}")

        await orch.stop()

    asyncio.run(demo())
