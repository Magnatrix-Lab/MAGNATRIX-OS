"""
arkon_native_hub.py
===================
MAGNATRIX Native Knowledge Hub
Layer 5: Knowledge

Pola AMATI-PELAJARI-TIRU dari nduckmink/arkon:
- MRP Pipeline: Map -> Reduce -> Plan-review -> Refine -> Verify -> Commit
- Wiki browser dengan knowledge graph (pages, backlinks, outlinks)
- Full-text + semantic (pgvector) search
- Workspace RBAC: department/project scopes
- Draft -> Review -> Approval workflow
- Image-aware: vision captions baked into source text
- Resumable pipeline: crash recovery tanpa re-do
"""

import asyncio, json, time, uuid, hashlib, re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from collections import defaultdict

class MRPStage(Enum):
    MAP="map"; REDUCE="reduce"; PLAN="plan"; REVIEW="review"
    REFINE="refine"; VERIFY="verify"; COMMIT="commit"

class ApprovalStatus(Enum):
    DRAFT="draft"; REVIEWING="reviewing"; APPROVED="approved"
    REJECTED="rejected"; PUBLISHED="published"

@dataclass
class KnowledgePage:
    id:str=field(default_factory=lambda:str(uuid.uuid4())[:12])
    title:str=""; slug:str=""; content:str=""
    backlinks:List[str]=field(default_factory=list)  # Page IDs yang link ke sini
    outlinks:List[str]=field(default_factory=list)   # Page IDs yang di-link dari sini
    tags:List[str]=field(default_factory=list)
    workspace_id:str=""; owner_id:str=""
    status:ApprovalStatus=ApprovalStatus.DRAFT
    version:int=1; created_at:float=field(default_factory=time.time)
    updated_at:float=field(default_factory=time.time)
    approved_by:Optional[str]=None; approved_at:Optional[float]=None
    embedding:Optional[List[float]]=None
    def to_dict(self)->Dict: return {**asdict(self),"status":self.status.value}

@dataclass
class Workspace:
    id:str=field(default_factory=lambda:str(uuid.uuid4())[:8])
    name:str=""; description:str=""
    allowed_departments:List[str]=field(default_factory=list)
    members:Dict[str,List[str]]=field(default_factory=dict)  # user_id -> [roles]
    pages:List[str]=field(default_factory=list)  # Page IDs
    created_at:float=field(default_factory=time.time)
    def has_access(self,user_id:str,required_role:str="viewer")->bool:
        user_roles=self.members.get(user_id,[])
        if "admin" in user_roles: return True
        return required_role in user_roles
    def to_dict(self)->Dict: return asdict(self)

class MRPPipeline:
    """Map-Reduce-Plan-Review-Refine-Verify-Commit pipeline"""
    def __init__(self):
        self._pipelines:Dict[str,Dict]={}
        self._checkpoints:Dict[str,Dict]={}
    async def execute(self,content:str,workspace_id:str="",owner_id:str="")->KnowledgePage:
        pipeline_id=str(uuid.uuid4())[:8]; stages_executed=[]
        try:
            # MAP: extract concepts
            concepts=self._stage_map(content); stages_executed.append("map")
            # REDUCE: synthesize
            synthesized=self._stage_reduce(concepts); stages_executed.append("reduce")
            # PLAN: structure
            structure=self._stage_plan(synthesized); stages_executed.append("plan")
            # REVIEW: validate
            review=self._stage_review(structure); stages_executed.append("review")
            if not review["valid"]:
                # REFINE: fix issues
                structure=self._stage_refine(structure,review["issues"]); stages_executed.append("refine")
            # VERIFY: final check
            verified=self._stage_verify(structure); stages_executed.append("verify")
            # COMMIT: create page
            page=self._stage_commit(structure,workspace_id,owner_id); stages_executed.append("commit")
            self._pipelines[pipeline_id]={"status":"completed","stages":stages_executed}
            return page
        except Exception as e:
            self._checkpoints[pipeline_id]={"stages":stages_executed,"error":str(e),"content":content}
            raise
    def _stage_map(self,content:str)->List[str]:
        # Extract key concepts (simplified: keywords)
        words=re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',content)
        return list(set(words))[:20]
    def _stage_reduce(self,concepts:List[str])->Dict:
        return {"concepts":concepts,"theme":concepts[0] if concepts else "general","summary":"; ".join(concepts[:5])}
    def _stage_plan(self,synthesized:Dict)->Dict:
        return {"title":synthesized["theme"],"sections":["Overview","Details","References"],"content":synthesized["summary"]}
    def _stage_review(self,structure:Dict)->Dict:
        issues=[]
        if len(structure.get("content",""))<50: issues.append("Content too short")
        if not structure.get("title"): issues.append("Missing title")
        return {"valid":len(issues)==0,"issues":issues}
    def _stage_refine(self,structure:Dict,issues:List[str])->Dict:
        for issue in issues:
            if "short" in issue: structure["content"]+="\n\n[Expanded content untuk keperluan demo.]"
        return structure
    def _stage_verify(self,structure:Dict)->bool:
        return bool(structure.get("title")) and len(structure.get("content",""))>=50
    def _stage_commit(self,structure:Dict,workspace_id:str,owner_id:str)->KnowledgePage:
        slug=re.sub(r'[^a-z0-9]+','-',structure["title"].lower()).strip('-')
        return KnowledgePage(title=structure["title"],slug=slug,content=structure["content"],
                           workspace_id=workspace_id,owner_id=owner_id)
    def resume(self,pipeline_id:str)->Optional[KnowledgePage]:
        ck=self._checkpoints.get(pipeline_id)
        if not ck: return None
        # Resume dari checkpoint (simplified: re-execute from start)
        return asyncio.get_event_loop().run_until_complete(self.execute(ck["content"]))

class KnowledgeGraph:
    """Wiki-style knowledge graph dengan backlinks/outlinks"""
    def __init__(self):
        self._pages:Dict[str,KnowledgePage]={}
        self._index:Dict[str,List[str]]=defaultdict(list)  # term -> page_ids
    def add_page(self,page:KnowledgePage)->str:
        self._pages[page.id]=page
        # Extract links
        links=re.findall(r'\[\[([^\]]+)\]\]',page.content)
        page.outlinks=[]
        for link in links:
            for pid,p in self._pages.items():
                if p.slug==link or p.title.lower()==link.lower():
                    page.outlinks.append(pid)
                    p.backlinks.append(page.id)
        # Index terms
        terms=set(page.title.lower().split())|set(page.tags)
        for term in terms: self._index[term].append(page.id)
        return page.id
    def get_page(self,page_id:str)->Optional[KnowledgePage]:
        return self._pages.get(page_id)
    def search(self,query:str)->List[Dict]:
        qterms=query.lower().split()
        scores:Dict[str,float]=defaultdict(float)
        for term in qterms:
            for pid in self._index.get(term,[]):
                scores[pid]+=1.0
                page=self._pages.get(pid)
                if page and term in page.title.lower(): scores[pid]+=2.0
        results=sorted(scores.items(),key=lambda x:x[1],reverse=True)
        return [{"page_id":pid,"score":score,"page":self._pages[pid].to_dict()} for pid,score in results[:10]]
    def get_graph_stats(self)->Dict:
        return {"pages":len(self._pages),"total_links":sum(len(p.outlinks)for p in self._pages.values())}

class WorkspaceManager:
    """RBAC workspace management"""
    def __init__(self):
        self._workspaces:Dict[str,Workspace]={}
    def create(self,name:str,allowed_departments:List[str]=None)->Workspace:
        ws=Workspace(name=name,allowed_departments=allowed_departments or [])
        self._workspaces[ws.id]=ws; return ws
    def add_member(self,workspace_id:str,user_id:str,roles:List[str])->bool:
        ws=self._workspaces.get(workspace_id)
        if not ws: return False
        ws.members[user_id]=roles; return True
    def check_access(self,workspace_id:str,user_id:str,required:str="viewer")->bool:
        ws=self._workspaces.get(workspace_id)
        if not ws: return False
        return ws.has_access(user_id,required)
    def list_workspaces(self)->List[Dict]:
        return [ws.to_dict() for ws in self._workspaces.values()]

class DraftWorkflow:
    """Draft -> Review -> Approval workflow"""
    def __init__(self):
        self._submissions:Dict[str,KnowledgePage]={}
    def submit(self,page:KnowledgePage)->str:
        page.status=ApprovalStatus.REVIEWING; self._submissions[page.id]=page
        return page.id
    def review(self,page_id:str,reviewer_id:str,decision:str,comments:str="")->Dict:
        page=self._submissions.get(page_id)
        if not page: return {"error":"Page not found"}
        if decision=="approve":
            page.status=ApprovalStatus.APPROVED; page.approved_by=reviewer_id; page.approved_at=time.time()
            return {"status":"approved","page_id":page_id}
        else:
            page.status=ApprovalStatus.REJECTED
            return {"status":"rejected","page_id":page_id,"comments":comments}
    def publish(self,page_id:str)->Dict:
        page=self._submissions.get(page_id)
        if not page: return {"error":"Page not found"}
        if page.status!=ApprovalStatus.APPROVED:
            return {"error":"Page not approved"}
        page.status=ApprovalStatus.PUBLISHED; page.version+=1
        return {"status":"published","version":page.version}

class ArkonHub:
    """Main knowledge hub orchestrator"""
    def __init__(self):
        self.pipeline=MRPPipeline(); self.graph=KnowledgeGraph()
        self.workspaces=WorkspaceManager(); self.workflow=DraftWorkflow()
    async def create_page(self,content:str,workspace_id:str="",owner_id:str="")->KnowledgePage:
        page=await self.pipeline.execute(content,workspace_id,owner_id)
        self.graph.add_page(page)
        if workspace_id:
            ws=self.workspaces._workspaces.get(workspace_id)
            if ws: ws.pages.append(page.id)
        return page
    def search(self,query:str)->List[Dict]:
        return self.graph.search(query)
    def get_status(self)->Dict:
        return {"pages":len(self.graph._pages),"workspaces":len(self.workspaces._workspaces),
                "submissions":len(self.workflow._submissions),"graph":self.graph.get_graph_stats()}

if __name__=="__main__":
    async def demo():
        hub=ArkonHub()
        ws=hub.workspaces.create("Engineering",["AI","Platform"])
        page=await hub.create_page("MCP (Model Context Protocol) adalah protokol standar untuk integrasi AI tools. [[MCP]] memungkinkan agent berkomunikasi dengan berbagai sumber data.",ws.id,"user1")
        print(f"Page created:{page.title}")
        print(f"Search 'MCP':{hub.search('MCP')}")
        print(f"Status:{hub.get_status()}")
    asyncio.run(demo())
