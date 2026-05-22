"""
julep_native_engine.py
=======================
MAGNATRIX Native Agent Workflow & Memory Engine
Layer 0.5: COLLECTIVE BRAIN / Layer 3: Runtime

Pola AMATI-PELAJARI-TIRU dari julep-ai/julep:
- Temporal-style durable workflows, persistent memory (TimescaleDB+pgVector),
  session-based agent memory, YAML/JSON multi-step orchestration,
  built-in RAG pipeline, 100+ tool integrations, model-agnostic
- Tiru: Native Python asyncio, in-memory + SQLite hybrid store,
  MAGNATRIX mesh tool integration, constitutional memory
"""

import asyncio, json, time, uuid, hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from collections import defaultdict

class TaskStatus(Enum):
    PENDING="pending"; RUNNING="running"; PAUSED="paused"
    COMPLETED="completed"; FAILED="failed"; RETRYING="retrying"

class MemoryLevel(Enum):
    EPISODIC="episodic"; SEMANTIC="semantic"
    PROCEDURAL="procedural"; WORKING="working"

@dataclass
class AgentDefinition:
    id:str=field(default_factory=lambda:str(uuid.uuid4())[:12])
    name:str=""; description:str=""; model:str="openrouter/auto"
    system_prompt:str=""; tools:List[str]=field(default_factory=list)
    memory_enabled:bool=True
    recall_options:Dict=field(default_factory=lambda:{"mode":"hybrid","confidence":0.7,"limit":10,"embed_text":True})
    default_task_settings:Dict=field(default_factory=lambda:{"max_retries":3,"timeout_seconds":300,"parallel":False})
    tags:List[str]=field(default_factory=list)
    created_at:float=field(default_factory=time.time)
    def to_dict(self)->Dict: return asdict(self)

@dataclass
class Session:
    id:str=field(default_factory=lambda:str(uuid.uuid4())[:12])
    agent_id:str=""; situation:str=""
    messages:List[Dict]=field(default_factory=list)
    memory_enabled:bool=True; recall_mode:str="hybrid"
    created_at:float=field(default_factory=time.time)
    last_active:float=field(default_factory=time.time)
    message_count:int=0; mesh_broadcast:bool=False
    def add_message(self,role:str,content:str,metadata:Dict=None):
        msg={"id":str(uuid.uuid4())[:8],"role":role,"content":content,"timestamp":time.time(),"metadata":metadata or {}}
        self.messages.append(msg); self.message_count+=1; self.last_active=time.time()
        return msg
    def to_dict(self)->Dict:
        return {**asdict(self),"duration_seconds":time.time()-self.created_at}

@dataclass
class TaskStep:
    id:str=field(default_factory=lambda:str(uuid.uuid4())[:8])
    name:str=""; step_type:str=""; config:Dict=field(default_factory=dict)
    status:TaskStatus=TaskStatus.PENDING; result:Optional[Dict]=None
    error:Optional[str]=None; retries:int=0; max_retries:int=3
    started_at:Optional[float]=None; completed_at:Optional[float]=None
    on_success:Optional[str]=None; on_failure:Optional[str]=None
    def to_dict(self)->Dict: return {**asdict(self),"status":self.status.value}

@dataclass
class TaskWorkflow:
    id:str=field(default_factory=lambda:str(uuid.uuid4())[:12])
    name:str=""; description:str=""; agent_id:str=""
    steps:Dict[str,TaskStep]=field(default_factory=dict)
    entry_step:str=""; input_schema:Dict=field(default_factory=dict)
    output_schema:Dict=field(default_factory=dict)
    status:TaskStatus=TaskStatus.PENDING; current_step:Optional[str]=None
    variables:Dict=field(default_factory=dict)
    max_retries:int=3; timeout_seconds:int=300; parallel:bool=False
    created_at:float=field(default_factory=time.time)
    def to_dict(self)->Dict: return {**asdict(self),"status":self.status.value}

class MemoryStore:
    def __init__(self):
        self._episodic=[]; self._semantic={}; self._procedural=[]; self._vectors={}
    async def store(self,level:MemoryLevel,content:str,metadata:Dict=None,embedding:List[float]=None):
        entry={"id":str(uuid.uuid4())[:8],"content":content,"metadata":metadata or {},"timestamp":time.time(),"embedding":embedding or self._simple_embed(content)}
        if level==MemoryLevel.EPISODIC:
            self._episodic.append(entry)
            if len(self._episodic)>1000: self._episodic=self._episodic[-1000:]
        elif level==MemoryLevel.SEMANTIC:
            self._semantic[hashlib.md5(content.encode()).hexdigest()[:16]]=entry
        elif level==MemoryLevel.PROCEDURAL: self._procedural.append(entry)
        if embedding: self._vectors[entry["id"]]=embedding
    async def recall(self,query:str,mode:str="hybrid",limit:int=10,confidence:float=0.7)->List[Dict]:
        qe=self._simple_embed(query); results=[]
        all_mem=self._episodic+list(self._semantic.values())+self._procedural
        for m in all_mem:
            kw=self._kw_score(query,m["content"]); vec=self._cos_sim(qe,m.get("embedding",[]))
            score=(kw*0.4+vec*0.6) if mode=="hybrid" else (kw if mode=="keyword" else vec)
            if score>=confidence: results.append({**m,"score":score})
        results.sort(key=lambda x:x["score"],reverse=True); return results[:limit]
    def _simple_embed(self,text:str)->List[float]:
        words=text.lower().split(); emb=[0.0]*128
        for i,w in enumerate(words[:128]): emb[i]=hash(w)%100/100.0
        return emb
    def _kw_score(self,q:str,c:str)->float:
        qw=set(q.lower().split()); cw=set(c.lower().split())
        return len(qw&cw)/len(qw) if qw else 0.0
    def _cos_sim(self,a:List[float],b:List[float])->float:
        if not a or not b: return 0.0
        n=min(len(a),len(b)); dot=sum(x*y for x,y in zip(a[:n],b[:n]))
        na=sum(x*x for x in a)**0.5; nb=sum(x*x for x in b)**0.5
        return dot/(na*nb) if na and nb else 0.0

class ToolRegistry:
    def __init__(self): self._tools:Dict[str,Dict]={}; self._handlers:Dict[str,Callable]={}
    def register(self,tool_id:str,name:str,description:str,parameters:Dict,handler:Callable):
        self._tools[tool_id]={"id":tool_id,"name":name,"description":description,"parameters":parameters}
        self._handlers[tool_id]=handler
    async def execute(self,tool_id:str,params:Dict)->Dict:
        h=self._handlers.get(tool_id)
        if not h: return {"error":f"Tool {tool_id} not found"}
        try:
            if asyncio.iscoroutinefunction(h): return await h(**params)
            return h(**params)
        except Exception as e: return {"error":str(e)}
    def list_tools(self)->List[Dict]: return list(self._tools.values())

class TaskOrchestrator:
    def __init__(self,memory:MemoryStore,tools:ToolRegistry,llm_callback:Optional[Callable]=None):
        self.memory=memory; self.tools=tools; self.llm_callback=llm_callback
        self._workflows:Dict[str,TaskWorkflow]={}; self._executions:Dict[str,Dict]={}
    def create_workflow(self,name:str,agent_id:str,description:str="")->TaskWorkflow:
        wf=TaskWorkflow(name=name,agent_id=agent_id,description=description)
        self._workflows[wf.id]=wf; return wf
    def add_step(self,workflow_id:str,name:str,step_type:str,config:Dict,on_success:str=None,on_failure:str=None)->TaskStep:
        wf=self._workflows.get(workflow_id)
        if not wf: raise ValueError(f"Workflow {workflow_id} not found")
        step=TaskStep(name=name,step_type=step_type,config=config,on_success=on_success,on_failure=on_failure)
        wf.steps[step.id]=step
        if not wf.entry_step: wf.entry_step=step.id
        return step
    async def execute(self,workflow_id:str,inputs:Dict=None)->Dict:
        wf=self._workflows.get(workflow_id)
        if not wf: return {"error":"Workflow not found"}
        wf.status=TaskStatus.RUNNING; wf.variables=inputs or {}
        eid=str(uuid.uuid4())[:12]; self._executions[eid]={"workflow_id":workflow_id,"start_time":time.time()}
        current=wf.entry_step; visited=set()
        try:
            while current and current not in visited:
                visited.add(current); step=wf.steps.get(current)
                if not step: break
                step.status=TaskStatus.RUNNING; step.started_at=time.time(); wf.current_step=current
                try:
                    result=await self._exec_step(step,wf); step.result=result
                    step.status=TaskStatus.COMPLETED; step.completed_at=time.time(); current=step.on_success
                except Exception as e:
                    step.error=str(e); step.retries+=1
                    if step.retries<step.max_retries: step.status=TaskStatus.RETRYING; await asyncio.sleep(2**step.retries); continue
                    else: step.status=TaskStatus.FAILED; current=step.on_failure
            wf.status=TaskStatus.COMPLETED; self._executions[eid]["status"]="completed"; self._executions[eid]["end_time"]=time.time()
            return {"execution_id":eid,"status":"completed","variables":wf.variables,"steps_executed":len(visited)}
        except Exception as e:
            wf.status=TaskStatus.FAILED; self._executions[eid]["status"]="failed"; self._executions[eid]["error"]=str(e)
            return {"execution_id":eid,"status":"failed","error":str(e)}
    async def _exec_step(self,step:TaskStep,workflow:TaskWorkflow)->Dict:
        if step.step_type=="prompt":
            p=step.config.get("prompt","")
            if self.llm_callback: return {"response":await self.llm_callback(p)}
            return {"response":f"[LLM:{p[:50]}...]"}
        elif step.step_type=="tool":
            return await self.tools.execute(step.config.get("tool_id",""),step.config.get("parameters",{}))
        elif step.step_type=="condition":
            return {"condition_result":eval(step.config.get("condition","true"),{"vars":workflow.variables})}
        elif step.step_type=="memory":
            await self.memory.store(MemoryLevel(step.config.get("level","episodic")),step.config.get("content",""),metadata={"workflow":workflow.id})
            return {"stored":True}
        elif step.step_type=="recall":
            return {"memories":await self.memory.recall(step.config.get("query",""))}
        return {"status":"unknown"}

class JulepEngine:
    def __init__(self):
        self.agents:Dict[str,AgentDefinition]={}; self.sessions:Dict[str,Session]={}
        self.memory=MemoryStore(); self.tools=ToolRegistry()
        self.orchestrator=TaskOrchestrator(self.memory,self.tools); self._llm_callback:Optional[Callable]=None
    def set_llm_callback(self,callback:Callable): self._llm_callback=callback; self.orchestrator.llm_callback=callback
    def create_agent(self,name:str,model:str="openrouter/auto",system_prompt:str="")->AgentDefinition:
        agent=AgentDefinition(name=name,model=model,system_prompt=system_prompt); self.agents[agent.id]=agent; return agent
    def create_session(self,agent_id:str,situation:str="")->Session:
        session=Session(agent_id=agent_id,situation=situation); self.sessions[session.id]=session; return session
    async def chat(self,session_id:str,message:str,recall:bool=True,remember:bool=True)->str:
        session=self.sessions.get(session_id)
        if not session: return "Session not found"
        agent=self.agents.get(session.agent_id)
        if not agent: return "Agent not found"
        context=""
        if recall and session.memory_enabled:
            mem=await self.memory.recall(message,mode=session.recall_mode,limit=agent.recall_options.get("limit",10))
            if mem: context="Relevant context:\n"+"\n".join(f"- {m['content'][:100]}" for m in mem[:5])
        prompt=f"""{agent.system_prompt}
{context}
User:{message}
Assistant:"""
        response=await self._llm_callback(prompt) if self._llm_callback else f"[Response:{message[:50]}...]"
        session.add_message("user",message); session.add_message("assistant",response)
        if remember:
            await self.memory.store(MemoryLevel.EPISODIC,f"User:{message}\nAssistant:{response}",metadata={"session":session_id,"agent":agent.id})
        return response
    def get_status(self)->Dict:
        return {"agents":len(self.agents),"sessions":len(self.sessions),"workflows":len(self.orchestrator._workflows),
                "memory_entries":len(self.memory._episodic)+len(self.memory._semantic)+len(self.memory._procedural),"tools":len(self.tools._tools)}

if __name__=="__main__":
    async def demo():
        engine=JulepEngine()
        agent=engine.create_agent("Researcher","openrouter/auto","You are a helpful research assistant.")
        session=engine.create_session(agent.id,"Research project on AI")
        r1=await engine.chat(session.id,"What is reinforcement learning?")
        print(f"R1:{r1[:80]}...")
        r2=await engine.chat(session.id,"Tell me more about that")
        print(f"R2:{r2[:80]}...")
        print(f"Status:{engine.get_status()}")
    asyncio.run(demo())
