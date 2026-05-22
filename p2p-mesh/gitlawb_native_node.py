"""
gitlawb_native_node.py
=======================
MAGNATRIX Native P2P Decentralized Mesh Node
Layer 4: P2P Mesh

Pola AMATI-PELAJARI-TIRU dari gitlawb node:
- Decentralized git: setiap node punya repo copy, sync via gossip
- DID identity: Ed25519 keypairs, self-sovereign identity
- UCAN delegation: capability-based authorization (JWT extension)
- Gossipsub event streaming: real-time mesh broadcast
- Multi-tier storage: hot (local) -> warm (IPFS) -> cold (Filecoin/Arweave)
- MCP 25 tools untuk git operations
"""

import asyncio, json, time, uuid, hashlib, base64
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum
from collections import defaultdict

class StorageTier(Enum):
    HOT="hot"; WARM="warm"; COLD="cold"

class EventType(Enum):
    COMMIT="commit"; PUSH="push"; PULL="pull"
    MERGE="merge"; FORK="fork"; HALT="halt"
    GOSSIP="gossip"; SYNC="sync"

@dataclass
class DIDIdentity:
    """Self-sovereign identity dengan Ed25519"""
    did:str=field(default_factory=lambda:f"did:magnatrix:{uuid.uuid4().hex[:16]}")
    public_key:str=""; private_key:str=""
    created_at:float=field(default_factory=time.time)
    metadata:Dict=field(default_factory=dict)
    def to_dict(self)->Dict: return {**asdict(self),"private_key":"[REDACTED]"}
    def sign(self,data:str)->str:
        """Sign data dengan private key (simplified)"""
        sig=hashlib.sha256(f"{self.private_key}:{data}".encode()).hexdigest()[:32]
        return base64.b64encode(sig.encode()).decode()
    def verify(self,data:str,signature:str)->bool:
        """Verify signature"""
        expected=self.sign(data)
        return signature==expected

@dataclass
class UCANToken:
    """User Controlled Authorization Network token"""
    id:str=field(default_factory=lambda:str(uuid.uuid4())[:12])
    issuer_did:str=""; audience_did:str=""
    capabilities:List[str]=field(default_factory=list)  # ["repo:read","repo:write"]
    expiration:float=0.0
    proof_chain:List[str]=field(default_factory=list)
    signature:str=""
    def to_dict(self)->Dict: return asdict(self)
    def is_valid(self)->bool: return time.time()<self.expiration
    def can(self,capability:str)->bool: return capability in self.capabilities and self.is_valid()

@dataclass
class MeshEvent:
    """Gossipsub event"""
    id:str=field(default_factory=lambda:str(uuid.uuid4())[:8])
    event_type:EventType=EventType.GOSSIP
    sender_did:str=""; topic:str=""
    payload:Dict=field(default_factory=dict)
    timestamp:float=field(default_factory=time.time)
    ttl:int=300; signature:str=""
    hops:int=0; max_hops:int=5
    def to_dict(self)->Dict: return {**asdict(self),"event_type":self.event_type.value}
    def is_expired(self)->bool: return (time.time()-self.timestamp)>self.ttl or self.hops>=self.max_hops

@dataclass
class RepoState:
    """Git-like repo state di node"""
    repo_id:str=field(default_factory=lambda:str(uuid.uuid4())[:8])
    owner_did:str=""; head_commit:str=""
    branches:Dict[str,str]=field(default_factory=dict)  # branch -> commit hash
    commits:List[Dict]=field(default_factory=list)
    remotes:List[str]=field(default_factory=list)  # Connected node DIDs
    last_sync:Optional[float]=None
    def to_dict(self)->Dict: return asdict(self)

class UCANDelegator:
    """UCAN delegation manager"""
    def __init__(self,identity:DIDIdentity):
        self.identity=identity; self._tokens:Dict[str,UCANToken]={}
    def delegate(self,audience_did:str,capabilities:List[str],
                 duration_seconds:int=86400)->UCANToken:
        token=UCANToken(issuer_did=self.identity.did,audience_did=audience_did,
                        capabilities=capabilities,expiration=time.time()+duration_seconds)
        token.signature=self.identity.sign(f"{token.issuer_did}:{token.audience_did}:{':'.join(capabilities)}")
        self._tokens[token.id]=token; return token
    def verify_token(self,token:UCANToken)->bool:
        if not token.is_valid(): return False
        expected_sig=self.identity.sign(f"{token.issuer_did}:{token.audience_did}:{':'.join(token.capabilities)}")
        return token.signature==expected_sig
    def revoke(self,token_id:str)->bool:
        return self._tokens.pop(token_id,None)is not None

class GossipMesh:
    """Gossip-based event propagation"""
    def __init__(self,identity:DIDIdentity):
        self.identity=identity; self._peers:Set[str]=set()
        self._subscriptions:Dict[str,List[Callable]]=defaultdict(list)
        self._seen_events:Set[str]=set(); self._event_log:List[MeshEvent]=[]
    def connect_peer(self,did:str): self._peers.add(did)
    def disconnect_peer(self,did:str): self._peers.discard(did)
    def subscribe(self,topic:str,handler:Callable): self._subscriptions[topic].append(handler)
    async def publish(self,event:MeshEvent):
        event.signature=self.identity.sign(json.dumps(event.payload,sort_keys=True))
        self._seen_events.add(event.id); self._event_log.append(event)
        await self._gossip(event)
    async def _gossip(self,event:MeshEvent):
        if event.is_expired(): return
        event.hops+=1
        for topic,handlers in self._subscriptions.items():
            if event.topic==topic or topic=="#":
                for h in handlers:
                    try:
                        if asyncio.iscoroutinefunction(h): await h(event)
                        else: h(event)
                    except: pass
    def get_events(self,since:float=None)->List[Dict]:
        events=self._event_log
        if since: events=[e for e in events if e.timestamp>since]
        return [e.to_dict() for e in events[-1000:]]

class StorageManager:
    """Multi-tier storage: hot -> warm -> cold"""
    def __init__(self):
        self._hot:Dict[str,Any]={}  # Local memory
        self._warm:Dict[str,str]={}  # IPFS hashes
        self._cold:Dict[str,str]={}  # Filecoin/Arweave IDs
    def store_hot(self,key:str,data:Any)->str:
        self._hot[key]=data; return key
    def get_hot(self,key:str)->Any:
        return self._hot.get(key)
    def promote_to_warm(self,key:str,ipfs_hash:str):
        self._warm[key]=ipfs_hash
        if key in self._hot: del self._hot[key]
    def archive_to_cold(self,key:str,archive_id:str):
        self._cold[key]=archive_id
        if key in self._warm: del self._warm[key]
    def get_storage_summary(self)->Dict:
        return {"hot":len(self._hot),"warm":len(self._warm),"cold":len(self._cold)}

class GitSync:
    """Decentralized git sync engine"""
    def __init__(self,mesh:GossipMesh,storage:StorageManager):
        self.mesh=mesh; self.storage=storage; self._repos:Dict[str,RepoState]={}
    def init_repo(self,repo_id:str,owner_did:str)->RepoState:
        repo=RepoState(repo_id=repo_id,owner_did=owner_did)
        self._repos[repo_id]=repo; return repo
    async def commit(self,repo_id:str,did:DIDIdentity,changes:Dict,
                     parent_commit:str="",message:str="")->Dict:
        repo=self._repos.get(repo_id)
        if not repo: return {"error":"Repo not found"}
        commit_hash=hashlib.sha256(json.dumps(changes,sort_keys=True).encode()).hexdigest()[:16]
        commit={"hash":commit_hash,"author":did.did,"message":message,"parent":parent_commit,
                "changes":changes,"timestamp":time.time()}
        repo.commits.append(commit); repo.head_commit=commit_hash
        # Broadcast
        await self.mesh.publish(MeshEvent(event_type=EventType.COMMIT,sender_did=did.did,
                                          topic=f"repo.{repo_id}",payload={"commit":commit_hash,"repo":repo_id}))
        return commit
    async def push(self,repo_id:str,target_did:str)->Dict:
        repo=self._repos.get(repo_id)
        if not repo: return {"error":"Repo not found"}
        repo.remotes.append(target_did)
        await self.mesh.publish(MeshEvent(event_type=EventType.PUSH,sender_did=repo.owner_did,
                                          topic=f"repo.{repo_id}",payload={"repo":repo_id,"target":target_did}))
        return {"status":"pushed","commits":len(repo.commits)}
    async def pull(self,repo_id:str,source_did:str)->Dict:
        # Request sync dari peer
        await self.mesh.publish(MeshEvent(event_type=EventType.PULL,sender_did=source_did,
                                          topic=f"repo.{repo_id}",payload={"repo":repo_id,"request":"sync"}))
        return {"status":"pull_requested"}
    def get_repo(self,repo_id:str)->Optional[RepoState]:
        return self._repos.get(repo_id)

class P2PNode:
    """Main P2P node orchestrator"""
    def __init__(self):
        self.identity=DIDIdentity()
        self.delegator=UCANDelegator(self.identity)
        self.mesh=GossipMesh(self.identity)
        self.storage=StorageManager()
        self.sync=GitSync(self.mesh,self.storage)
        self._running:bool=False
    async def start(self):
        self._running=True
        # Auto-connect ke known bootstrap nodes (placeholder)
    async def stop(self):
        self._running=False
    def create_repo(self,repo_id:str)->RepoState:
        return self.sync.init_repo(repo_id,self.identity.did)
    async def share_capability(self,target_did:str,capabilities:List[str])->UCANToken:
        return self.delegator.delegate(target_did,capabilities)
    def get_status(self)->Dict:
        return {"did":self.identity.did,"peers":len(self.mesh._peers),
                "repos":len(self.sync._repos),"events":len(self.mesh._event_log),
                "storage":self.storage.get_storage_summary()}

if __name__=="__main__":
    async def demo():
        node=P2PNode()
        repo=node.create_repo("magnatrix-core")
        commit=await node.sync.commit("magnatrix-core",node.identity,
                                      {"README.md":"# MAGNATRIX"},message="Initial commit")
        print(f"Commit:{commit['hash']}")
        print(f"Status:{node.get_status()}")
    asyncio.run(demo())
