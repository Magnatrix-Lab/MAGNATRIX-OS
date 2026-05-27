# Architecture Documentation

## C4 Model

### Level 1: System Context

```
┌─────────────────────────────────────────────────────────────┐
│                         YOU (User)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP / WebSocket
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   MAGNATRIX-OS (System)                     │
│                                                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │  AI Layer  │  │  Runtime   │  │  Security  │           │
│  │  (Agents)  │  │  (Swarm)   │  │  (Crypto)  │           │
│  └────────────┘  └────────────┘  └────────────┘           │
│                                                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │  Trading   │  │   P2P      │  │   GUI      │           │
│  │  (HFT)     │  │   (DHT)    │  │ Dashboard  │           │
│  └────────────┘  └────────────┘  └────────────┘           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Level 2: Container Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    MAGNATRIX-OS                              │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   AI Layer   │  │   Runtime    │  │   Security   │     │
│  │              │  │              │  │              │     │
│  │ • MetaAgent  │  │ • Swarm      │  │ • Rust Crypto│     │
│  │ • Theorem    │  │ • JIT Comp   │  │ • PyO3 Bind  │     │
│  │ • RAG        │  │ • State Mgmt │  │ • Fallback   │     │
│  │ • Autonomous │  │ • Bridge     │  │              │     │
│  │ • Local LLM  │  │              │  │              │     │
│  │ • Document   │  │              │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Trading    │  │   P2P Mesh   │  │   GUI        │     │
│  │              │  │              │  │              │     │
│  │ • C++ HFT    │  │ • Kademlia   │  │ • Dashboard  │     │
│  │ • pybind11   │  │ • NAT Traversal│ │ • 20 Panels │     │
│  │ • Fallback   │  │ • Bootstrap  │  │ • iframe     │     │
│  │              │  │ • Gossip     │  │ • Real-time  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Tri-Language Bridge (Python/C++/Rust)      │  │
│  │   Auto-detect native → fallback → pure Python        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Level 3: AI Layer Component

```
┌────────────────────────────────────────┐
│            AI Layer                      │
│                                         │
│  ┌─────────────┐    ┌─────────────┐    │
│  │ Meta Agent  │◄──►│   Local     │    │
│  │ Framework   │    │   LLM Agent │    │
│  └──────┬──────┘    └─────────────┘    │
│         │                               │
│  ┌──────┴──────┐    ┌─────────────┐    │
│  │  Theorem    │    │ Autonomous  │    │
│  │  Prover     │    │ Agent       │    │
│  │ (DSP+)      │    │ (AutoGPT)   │    │
│  └─────────────┘    └─────────────┘    │
│                                         │
│  ┌─────────────┐    ┌─────────────┐    │
│  │ Agentic RAG │    │ Document    │    │
│  │ (LangGraph) │    │ Agent       │    │
│  │             │    │ (LlamaIdx)  │    │
│  └─────────────┘    └─────────────┘    │
│                                         │
│  Shared: MockLLM (swappable → real API)│
└────────────────────────────────────────┘
```

### Level 4: Swarm Runtime Sequence

```
User          Orchestrator    Registry    Delegator    Agent     MessageBus
 │                 │              │            │           │           │
 │─submit_task()──►│              │            │           │           │
 │                 │─find_agent──►│            │           │           │
 │                 │◄────────────│            │           │           │
 │                 │─────────────►assign()───►│           │           │
 │                 │              │            │─send_msg──►│          │
 │                 │              │            │           │─recv()───►│
 │                 │              │            │           │◄───────────│
 │                 │              │            │◄─report───│           │
 │                 │◄─────────────│            │           │           │
 │◄─result─────────│              │            │           │           │
```

---

## Data Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │────►│   GUI       │────►│  Gateway    │
│  Request    │     │ Dashboard   │     │  Router     │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                  │
                    ┌─────────────────────────────┼─────────────────────┐
                    │                             │                     │
                    ▼                             ▼                     ▼
             ┌─────────────┐             ┌─────────────┐       ┌─────────────┐
             │  AI Layer   │             │   Swarm     │       │   State     │
             │  (Agents)   │◄───────────►│  Engine     │◄─────►│  Backend    │
             └─────────────┘             └─────────────┘       └─────────────┘
                                                  │
                    ┌─────────────────────────────┼─────────────────────┐
                    │                             │                     │
                    ▼                             ▼                     ▼
             ┌─────────────┐             ┌─────────────┐       ┌─────────────┐
             │   C++ HFT   │             │ Rust Crypto │       │   P2P Mesh  │
             │   Engine    │             │   Engine    │       │   (DHT)     │
             └─────────────┘             └─────────────┘       └─────────────┘
```

---

## Layer Architecture (15 Layers)

```
Layer 13.5  ┌─────────────────────────────────────┐
Auto Repo   │ Auto Repo Hunter                    │
Hunter      │ Discover repos → AMATI pattern      │
            └─────────────────────────────────────┘
Layer 13    ┌─────────────────────────────────────┐
Offensive   │ Security Research Tools             │
Security    │ Penetration testing, fuzzing        │
            └─────────────────────────────────────┘
Layer 12    ┌─────────────────────────────────────┐
IDE         │ Code Editor + Agentic Programming   │
            │ Inline suggestions, auto-refactor   │
            └─────────────────────────────────────┘
Layer 11    ┌─────────────────────────────────────┐
Governance  │ Constitutional AI, Voting DAO       │
            │ Rule enforcement, audit trail         │
            └─────────────────────────────────────┘
Layer 10    ┌─────────────────────────────────────┐
Uncensored  │ Uncensored AI Interface             │
AI          │ No guardrails, raw reasoning        │
            └─────────────────────────────────────┘
Layer 9     ┌─────────────────────────────────────┐
Security    │ Rust Crypto Engine                  │
            │ Ed25519, AES-GCM, ChaCha20, Argon2  │
            └─────────────────────────────────────┘
Layer 8     ┌─────────────────────────────────────┐
HFT Trading │ C++ Order Book + Arbitrage        │
            │ Fixed-point, lock-based, pybind11   │
            └─────────────────────────────────────┘
Layer 7     ┌─────────────────────────────────────┐
Browser     │ Agentic Web Browser                 │
            │ Headless, JavaScript execution      │
            └─────────────────────────────────────┘
Layer 6     ┌─────────────────────────────────────┐
Skills      │ Skill Registry + Discovery          │
            │ Auto-install, version management    │
            └─────────────────────────────────────┘
Layer 5     ┌─────────────────────────────────────┐
Knowledge   │ RAG + Vector DB + Graph DB        │
            │ Agentic RAG, Document Agents      │
            └─────────────────────────────────────┘
Layer 4     ┌─────────────────────────────────────┐
P2P Mesh    │ Kademlia DHT + NAT Traversal      │
            │ 160-bit XOR, k-buckets, gossip    │
            └─────────────────────────────────────┘
Layer 3     ┌─────────────────────────────────────┐
Runtime     │ Swarm Engine + JIT Compiler       │
            │ Task delegation, consensus, state   │
            └─────────────────────────────────────┘
Layer 2     ┌─────────────────────────────────────┐
Identity    │ Ed25519 Keypairs + X.509          │
            │ Agent authentication, attestation   │
            └─────────────────────────────────────┘
Layer 1.5   ┌─────────────────────────────────────┐
API Router  │ 3-Tier LLM Routing                  │
            │ Local → Cloud → Free fallback     │
            └─────────────────────────────────────┘
Layer 1     ┌─────────────────────────────────────┐
Protocol    │ Message Bus + MCP Protocol          │
            │ Agent-to-agent communication      │
            └─────────────────────────────────────┘
Layer 0     ┌─────────────────────────────────────┐
Kernel      │ Python Event Loop + Threads         │
            │ Process isolation, resource limits  │
            └─────────────────────────────────────┘
```

---

## Collaboration Patterns

### Pattern 1: CrewAI Sequential

```
┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
│Research│───►│ Write  │───►│ Critic │───►│ Review │
│   er   │    │   r    │    │        │    │   er   │
└────────┘    └────────┘    └────────┘    └────────┘
```

### Pattern 2: AutoGen Group Chat

```
     ┌─────────┐
     │  Alice  │
     └────┬────┘
          │ msg
    ┌─────┴─────┐
    │           │
┌───▼───┐   ┌───▼───┐
│  Bob  │◄─►│ Carol │
└───┬───┘   └───┬───┘
    │           │
    └─────┬─────┘
          ▼
     ┌─────────┐
     │Consensus│
     └─────────┘
```

### Pattern 3: LangGraph State Machine

```
     ┌──────┐
     │ start│
     └──┬───┘
        │
        ▼
   ┌────────┐
   │research│
   └───┬────┘
       │ data_found?
   yes /  \ no
      ▼    ▼
 ┌──────┐  ┌────┐
 │ write│  │ end│
 └──┬───┘  └────┘
    │
    ▼
 ┌──────┐
 │review│
 └──┬───┘
    │
    ▼
 ┌────┐
 │end │
 └────┘
```

### Pattern 4: Hierarchical Manager-Workers

```
        ┌─────────┐
        │ Manager │
        └────┬────┘
             │ decompose
    ┌────────┼────────┐
    ▼        ▼        ▼
┌───────┐┌───────┐┌───────┐
│Worker1││Worker2││Worker3│
└───┬───┘└───┬───┘└───┬───┘
    │        │        │
    └────────┼────────┘
             ▼
        ┌─────────┐
        │Synthesis│
        └─────────┘
```

---

## Module Dependency Graph

```
                         ┌─────────────────┐
                         │  dashboard.html   │
                         │   (20 panels)     │
                         └────────┬────────┘
                                  │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│  ai/ (7)     │         │  runtime/ (5) │         │  knowledge/ (2)│
│  agents       │◄───────►│  swarm        │◄───────►│  RAG, docs     │
└───────────────┘         └───────┬───────┘         └───────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
            ┌──────────┐  ┌──────────┐  ┌──────────┐
            │ trading/ │  │ security/│  │  tests/  │
            │ C++ HFT  │  │ Rust Crypto│  │  22 int  │
            └──────────┘  └──────────┘  └──────────┘
```

---

## Communication Protocol

### Agent Message Format

```python
@dataclass
class AgentMessage:
    msg_id: str          # UUID
    sender_id: str       # Agent ID or "system"
    recipient_id: str    # Agent ID or "broadcast"
    msg_type: str        # task_request | task_result | critique | vote | heartbeat | chat
    payload: dict        # Message-specific data
    timestamp: float     # Unix timestamp
    priority: int        # 1=highest, 10=lowest
```

### MCP Tool Call Format

```json
{
  "tool": "web_search",
  "args": {
    "query": "Python asyncio",
    "max_results": 5
  },
  "caller": "agent_001",
  "call_id": "call_a1b2c3"
}
```

---

## State Management Architecture

```
┌─────────────────────────────────────────────────┐
│              StateManager (Unified)             │
│                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │  RedisLike  │  │   Vector    │  │  Graph   │ │
│  │  Store      │  │     DB      │  │    DB    │ │
│  │             │  │             │  │          │ │
│  │ • Strings   │  │ • Cosine    │  │ • Nodes  │ │
│  │ • Lists     │  │   similarity│  │ • Edges  │ │
│  │ • Hashes    │  │ • Metadata  │  │ • Paths  │ │
│  │ • Sets      │  │   filter    │  │ • Query  │ │
│  │ • ZSets     │  │             │  │          │ │
│  │ • Pub/Sub   │  │             │  │          │ │
│  │ • Streams   │  │             │  │          │ │
│  └─────────────┘  └─────────────┘  └──────────┘ │
│                                                 │
│  ┌─────────────────────────────────────────────┐│
│  │         TemporalStore                         ││
│  │  • Event log  • Audit trail  • Checkpoints   ││
│  └─────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
```
