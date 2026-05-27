#!/usr/bin/env python3
"""
Gitlawb Node Bridge — MAGNATRIX P2P Mesh Adapter
==================================================
Bridge to Gitlawb/node: decentralized git node with libp2p gossip,
Ed25519 identity, UCAN capabilities, and IPFS-backed storage.

Keywords: P2P mesh, decentralized git, Ed25519, libp2p gossip,
          DID identity, UCAN delegation, content-addressed storage

Repo: https://github.com/Gitlawb/node
Docs: https://gitlawb.com/architecture
"""
from __future__ import annotations

import os
import json
import asyncio
import base64
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, AsyncIterator
from pathlib import Path
from datetime import datetime

import aiohttp
import aiofiles

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GITLAWB_NODE_URL = os.getenv("GITLAWB_NODE_URL", "http://localhost:3000")
GITLAWB_DID = os.getenv("GITLAWB_DID", "")
GITLAWB_ED25519_KEY = os.getenv("GITLAWB_ED25519_KEY", "")  # base64-encoded raw key
GITLAWB_MCP_URL = os.getenv("GITLAWB_MCP_URL", "http://localhost:3000/mcp")

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class DIDIdentity:
    did: str
    public_key: str  # base64 Ed25519 public key
    verification_method: str = "Ed25519"
    trust_score: float = 0.0
    capabilities: List[str] = field(default_factory=list)

@dataclass
class UCANToken:
    issuer: str
    audience: str
    capabilities: List[Dict[str, Any]]
    expiration: Optional[str] = None
    proof: Optional[str] = None  # chained UCAN

@dataclass
class RefUpdate:
    ref: str
    old_sha: str
    new_sha: str
    signer_did: str
    signature: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

@dataclass
class RepoInfo:
    repo_did: str
    name: str
    branch_cid: str
    peers_known: int
    last_activity: str
    storage_tier: str  # hot | warm | permanent

@dataclass
class GossipEvent:
    event_type: str  # "ref-update", "peer-join", "repo-created", "pr-opened"
    payload: Dict[str, Any]
    source_peer: str
    timestamp: str

# ---------------------------------------------------------------------------
# Crypto Helpers (pure Python, no heavy deps)
# ---------------------------------------------------------------------------

def _sign_ref_update(ref: str, old_sha: str, new_sha: str, private_key_b64: str) -> str:
    """
    Produce a deterministic Ed25519-like signature over ref-update data.
    NOTE: In production, use pynacl or cryptography library for real Ed25519.
    This is a shim for the bridge interface.
    """
    msg = f"{ref}:{old_sha}:{new_sha}".encode("utf-8")
    key_bytes = base64.b64decode(private_key_b64)
    # Placeholder: real impl delegates to libsodium Ed25519
    import hashlib
    h = hashlib.blake2b(key=key_bytes, digest_size=64)
    h.update(msg)
    return base64.b64encode(h.digest()).decode("ascii")

# ---------------------------------------------------------------------------
# HTTP Client
# ---------------------------------------------------------------------------

class GitlawbHTTPClient:
    def __init__(self, base_url: str = GITLAWB_NODE_URL, did: str = GITLAWB_DID):
        self.base_url = base_url.rstrip("/")
        self.did = did
        self._session: Optional[aiohttp.ClientSession] = None

    async def _session_instance(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {"Content-Type": "application/json"}
            if self.did:
                headers["X-Gitlawb-DID"] = self.did
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        session = await self._session_instance()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with session.request(method, url, json=payload) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise RuntimeError(f"Gitlawb HTTP {resp.status}: {text[:300]}")
            return await resp.json()

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

# ---------------------------------------------------------------------------
# MCP Client (JSON-RPC over HTTP/SSE)
# ---------------------------------------------------------------------------

class GitlawbMCPClient:
    """Client for Gitlawb MCP server (25 tools)."""

    def __init__(self, mcp_url: str = GITLAWB_MCP_URL, did: str = GITLAWB_DID):
        self.mcp_url = mcp_url.rstrip("/")
        self.did = did
        self._session: Optional[aiohttp.ClientSession] = None
        self._tools: Optional[List[Dict[str, Any]]] = None

    async def _session_instance(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {"Content-Type": "application/json"}
            if self.did:
                headers["X-Gitlawb-DID"] = self.did
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def list_tools(self) -> List[Dict[str, Any]]:
        if self._tools is not None:
            return self._tools
        session = await self._session_instance()
        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        async with session.post(f"{self.mcp_url}/rpc", json=payload) as resp:
            data = await resp.json()
            self._tools = data.get("result", {}).get("tools", [])
            return self._tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        session = await self._session_instance()
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        async with session.post(f"{self.mcp_url}/rpc", json=payload) as resp:
            return await resp.json()

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

# ---------------------------------------------------------------------------
# Core Bridge
# ---------------------------------------------------------------------------

class GitlawbNodeBridge:
    """
    MAGNATRIX adapter for Gitlawb decentralized git node.

    Provides:
    - DID identity generation and resolution
    - Git operations over HTTP + libp2p
    - UCAN capability delegation
    - Ref-update certificate signing and gossip
    - MCP tool integration (25 tools)
    - Gossipsub event subscription
    - Content-addressed storage (IPFS / Filecoin / Arweave)
    """

    def __init__(
        self,
        node_url: str = GITLAWB_NODE_URL,
        mcp_url: str = GITLAWB_MCP_URL,
        did: str = GITLAWB_DID,
        ed25519_key_b64: str = GITLAWB_ED25519_KEY,
    ):
        self.http = GitlawbHTTPClient(node_url, did)
        self.mcp = GitlawbMCPClient(mcp_url, did)
        self.did = did
        self.ed25519_key = ed25519_key_b64
        self._identity: Optional[DIDIdentity] = None
        self._event_callbacks: List[Callable[[GossipEvent], None]] = []
        self._gossip_task: Optional[asyncio.Task] = None

    async def __aenter__(self) -> GitlawbNodeBridge:
        return self

    async def __aexit__(self, *_) -> None:
        await self.disconnect()

    # ---- Identity ----

    async def generate_identity(self) -> DIDIdentity:
        """Generate a new Ed25519 DID via the node."""
        resp = await self.http.request("POST", "/did/generate")
        self._identity = DIDIdentity(
            did=resp["did"],
            public_key=resp["public_key"],
            verification_method="Ed25519",
            trust_score=0.0,
            capabilities=["code-review", "ci-runner", "repo-push"],
        )
        self.did = self._identity.did
        return self._identity

    async def resolve_did(self, did: str) -> Dict[str, Any]:
        """Resolve a DID to its document."""
        return await self.http.request("GET", f"/did/resolve/{did}")

    async def get_trust_score(self, did: str) -> float:
        """Fetch on-chain trust score for a DID."""
        resp = await self.http.request("GET", f"/did/{did}/trust")
        return resp.get("trust_score", 0.0)

    # ---- Git / Repo Ops ----

    async def create_repo(self, name: str, description: str = "") -> str:
        """Create a new decentralized repo. Returns repo DID."""
        resp = await self.http.request(
            "POST",
            "/repos",
            {"name": name, "description": description, "owner_did": self.did},
        )
        return resp["repo_did"]

    async def list_repos(self) -> List[RepoInfo]:
        """List repos known to this node (federated view)."""
        resp = await self.http.request("GET", "/repos")
        items = resp.get("items", [])
        return [
            RepoInfo(
                repo_did=i["repo_did"],
                name=i["name"],
                branch_cid=i.get("branch_cid", ""),
                peers_known=i.get("peers_known", 0),
                last_activity=i.get("last_activity", ""),
                storage_tier=i.get("storage_tier", "hot"),
            )
            for i in items
        ]

    async def push_ref(
        self,
        repo_did: str,
        ref: str,
        old_sha: str,
        new_sha: str,
    ) -> RefUpdate:
        """
        Push a ref update with Ed25519 signature and gossip it.
        """
        if not self.ed25519_key:
            raise RuntimeError("ED25519_KEY not set. Cannot sign ref updates.")
        sig = _sign_ref_update(ref, old_sha, new_sha, self.ed25519_key)
        cert = {
            "type": "gitlawb/ref-update/v1",
            "ref": ref,
            "from": old_sha,
            "to": new_sha,
            "signatures": [{"signer": self.did, "sig": sig}],
        }
        await self.http.request(
            "POST",
            f"/repos/{repo_did}/refs",
            cert,
        )
        return RefUpdate(
            ref=ref,
            old_sha=old_sha,
            new_sha=new_sha,
            signer_did=self.did,
            signature=sig,
        )

    async def fetch_repo(self, repo_did: str) -> Dict[str, Any]:
        """Clone / fetch a repo by DID."""
        return await self.http.request("GET", f"/repos/{repo_did}/objects")

    async def open_pr(
        self,
        repo_did: str,
        from_branch: str,
        to_branch: str,
        title: str = "",
        reviewers: Optional[List[str]] = None,
    ) -> str:
        """Open a pull request."""
        resp = await self.http.request(
            "POST",
            f"/repos/{repo_did}/pulls",
            {
                "from": from_branch,
                "to": to_branch,
                "title": title,
                "reviewers": reviewers or [],
            },
        )
        return resp["pr_id"]

    # ---- UCAN Delegation ----

    async def delegate(
        self,
        audience_did: str,
        capabilities: List[str],
        expiration_hours: int = 24,
    ) -> UCANToken:
        """Issue a UCAN capability token."""
        resp = await self.http.request(
            "POST",
            "/ucan/delegate",
            {
                "issuer": self.did,
                "audience": audience_did,
                "capabilities": [{"can": c, "with": "*"} for c in capabilities],
                "expiration": expiration_hours,
            },
        )
        return UCANToken(
            issuer=self.did,
            audience=audience_did,
            capabilities=[{"can": c, "with": "*"} for c in capabilities],
            expiration=resp.get("expiration"),
            proof=resp.get("token"),
        )

    async def verify_ucan(self, token: str) -> Dict[str, Any]:
        """Verify a UCAN token."""
        return await self.http.request("POST", "/ucan/verify", {"token": token})

    # ---- MCP Tool Integration ----

    async def mcp_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools from the node."""
        return await self.mcp.list_tools()

    async def mcp_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool."""
        return await self.mcp.call_tool(tool_name, arguments)

    async def repo_list_federated(self) -> List[Dict[str, Any]]:
        """MCP wrapper: list repos across the federated network."""
        return (await self.mcp.call_tool("repo_list_federated", {})).get("result", {}).get("content", [])

    async def repo_create_mcp(self, name: str) -> str:
        """MCP wrapper: create repo via MCP."""
        r = await self.mcp.call_tool("repo_create", {"name": name})
        return r.get("result", {}).get("content", "")

    async def pr_create_mcp(self, repo: str, from_branch: str, to_branch: str) -> str:
        """MCP wrapper: create PR via MCP."""
        r = await self.mcp.call_tool("pr_create", {
            "repo": repo,
            "from": from_branch,
            "to": to_branch,
        })
        return r.get("result", {}).get("content", "")

    # ---- Gossipsub Events ----

    async def _gossip_loop(self, ws_url: str) -> None:
        """WebSocket listener for Gossipsub events."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        event = GossipEvent(
                            event_type=data.get("type", "unknown"),
                            payload=data.get("payload", {}),
                            source_peer=data.get("source", "unknown"),
                            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
                        )
                        for cb in self._event_callbacks:
                            try:
                                cb(event)
                            except Exception:
                                pass
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break

    async def subscribe_events(
        self,
        callback: Callable[[GossipEvent], None],
        ws_url: Optional[str] = None,
    ) -> None:
        """Subscribe to gossip events. Starts background listener."""
        self._event_callbacks.append(callback)
        url = ws_url or self.http.base_url.replace("http://", "ws://").replace("https://", "wss://") + "/events"
        if self._gossip_task is None or self._gossip_task.done():
            self._gossip_task = asyncio.create_task(self._gossip_loop(url))

    async def unsubscribe_events(self) -> None:
        if self._gossip_task and not self._gossip_task.done():
            self._gossip_task.cancel()
            try:
                await self._gossip_task
            except asyncio.CancelledError:
                pass
        self._event_callbacks.clear()

    # ---- Storage Tiers ----

    async def pin_to_ipfs(self, repo_did: str) -> str:
        """Pin repo objects to IPFS (hot storage)."""
        resp = await self.http.request("POST", f"/repos/{repo_did}/pin", {"tier": "hot"})
        return resp.get("cid", "")

    async def archive_to_filecoin(self, repo_did: str) -> str:
        """Archive repo to Filecoin (warm storage)."""
        resp = await self.http.request("POST", f"/repos/{repo_did}/archive", {"tier": "warm"})
        return resp.get("deal_id", "")

    async def anchor_to_arweave(self, repo_did: str) -> str:
        """Permanent anchor to Arweave."""
        resp = await self.http.request("POST", f"/repos/{repo_did}/anchor", {"tier": "permanent"})
        return resp.get("tx_id", "")

    # ---- Network / Mesh ----

    async def mesh_status(self) -> Dict[str, Any]:
        """Get mesh node status (peers, latency, gossip events)."""
        return await self.http.request("GET", "/mesh/status")

    async def mesh_sync(self, repo_did: str) -> Dict[str, Any]:
        """Force sync a repo across known peers."""
        return await self.http.request("POST", f"/mesh/sync/{repo_did}")

    # ---- Lifecycle ----

    async def disconnect(self) -> None:
        await self.unsubscribe_events()
        await self.http.close()
        await self.mcp.close()

# ---------------------------------------------------------------------------
# Demo Block
# ---------------------------------------------------------------------------

async def demo() -> None:
    """
    Demo: generate identity, create a repo, push a ref, delegate UCAN,
    listen to gossip, and use MCP tools.
    """
    bridge = GitlawbNodeBridge()

    # 1. Generate DID identity
    identity = await bridge.generate_identity()
    print(f"[DEMO] DID generated: {identity.did}")
    print(f"[DEMO] Capabilities: {identity.capabilities}")

    # 2. Create a decentralized repo
    repo_did = await bridge.create_repo("magnatrix-core", "MAGNATRIX OS core contracts")
    print(f"[DEMO] Repo created: {repo_did}")

    # 3. Push a signed ref update
    ref = await bridge.push_ref(
        repo_did=repo_did,
        ref="refs/heads/main",
        old_sha="0000000000000000000000000000000000000000",
        new_sha="a1b2c3d4e5f6...",
    )
    print(f"[DEMO] Ref signed + gossiped: {ref.ref} → {ref.new_sha[:16]}")

    # 4. Delegate UCAN to an agent
    agent_did = "did:gitlawb:z6MkAgent123"
    ucan = await bridge.delegate(
        audience_did=agent_did,
        capabilities=["repo-push", "pr-create"],
        expiration_hours=48,
    )
    print(f"[DEMO] UCAN issued to {ucan.audience}, exp: {ucan.expiration}")

    # 5. List MCP tools
    tools = await bridge.mcp_tools()
    print(f"[DEMO] MCP tools available: {len(tools)}")
    for t in tools[:5]:
        print(f"  - {t.get('name')}: {t.get('description', '')[:60]}")

    # 6. Call MCP tool: repo_list_federated
    repos = await bridge.repo_list_federated()
    print(f"[DEMO] Federated repos: {len(repos)}")

    # 7. Subscribe to gossip events
    def on_event(evt: GossipEvent) -> None:
        print(f"[GOSSIP] {evt.event_type} from {evt.source_peer[:20]}...")

    await bridge.subscribe_events(on_event)
    print("[DEMO] Subscribed to gossip events (5s demo)")
    await asyncio.sleep(5)

    # 8. Mesh status
    status = await bridge.mesh_status()
    print(f"[DEMO] Mesh peers: {status.get('peers_known', 0)}")

    # 9. Pin to IPFS
    cid = await bridge.pin_to_ipfs(repo_did)
    print(f"[DEMO] Pinned to IPFS: {cid}")

    await bridge.disconnect()
    print("[DEMO] Bridge disconnected.")

if __name__ == "__main__":
    print("=" * 60)
    print("Gitlawb Node Bridge Demo — MAGNATRIX P2P Mesh Adapter")
    print("=" * 60)
    print("
Requirements:")
    print("  - Gitlawb node running locally or remote")
    print("  - Set GITLAWB_NODE_URL and optionally GITLAWB_ED25519_KEY")
    print("
Uncomment asyncio.run(demo()) to run.
")
    # asyncio.run(demo())