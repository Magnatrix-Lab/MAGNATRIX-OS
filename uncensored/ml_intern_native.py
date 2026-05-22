"""
ml_intern_native.py
===================
MAGNATRIX Native Auto ML Pipeline
Layer 10: Uncensored AI

Pola AMATI-PELAJARI-TIRU dari ML-Intern concept:
- Auto ML pipeline: research papers -> dataset -> fine-tune -> evaluate -> deploy
- Context compaction guard (170k token threshold)
- Doom loop detection (repetitive ineffective patterns)
- Self-hosted training dengan PyTorch/LoRA
- Model versioning dan A/B testing
"""

import asyncio, json, time, uuid, hashlib, os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from collections import defaultdict

class PipelineStage(Enum):
    RESEARCH="research"; DATASET="dataset"; TRAIN="train"
    EVALUATE="evaluate"; DEPLOY="deploy"

class ModelStatus(Enum):
    DRAFT="draft"; TRAINING="training"; READY="ready"
    DEPLOYED="deployed"; RETIRED="retired"

@dataclass
class ResearchPaper:
    id:str=field(default_factory=lambda:str(uuid.uuid4())[:8])
    title:str=""; authors:List[str]=field(default_factory=list)
    abstract:str=""; url:str=""; year:int=0
    extracted_findings:List[str]=field(default_factory=list)
    relevance_score:float=0.0; downloaded:bool=False
    def to_dict(self)->Dict: return asdict(self)

@dataclass
class Dataset:
    id:str=field(default_factory=lambda:str(uuid.uuid4())[:8])
    name:str=""; description:str=""
    samples:List[Dict]=field(default_factory=list)
    train_split:float=0.8; val_split:float=0.1; test_split:float=0.1
    source_papers:List[str]=field(default_factory=list)
    created_at:float=field(default_factory=time.time)
    sample_count:int=0; avg_tokens_per_sample:float=0.0
    def to_dict(self)->Dict: return asdict(self)

@dataclass
class ModelVersion:
    id:str=field(default_factory=lambda:str(uuid.uuid4())[:8])
    name:str=""; base_model:str=""; status:ModelStatus=ModelStatus.DRAFT
    training_config:Dict=field(default_factory=dict)
    metrics:Dict=field(default_factory=dict)
    checkpoint_path:Optional[str]=None
    parent_version:Optional[str]=None
    created_at:float=field(default_factory=time.time)
    deployed_at:Optional[float]=None
    ab_test_group:Optional[str]=None
    def to_dict(self)->Dict: return {**asdict(self),"status":self.status.value}

class ContextCompactionGuard:
    """Guard untuk context size (tiru ML-Intern 170k threshold)"""
    def __init__(self,threshold:int=170000):
        self.threshold=threshold; self._current_size:int=0
    def check(self,text:str)->bool:
        self._current_size=len(text)
        return self._current_size<self.threshold
    def compact(self,text:str,target_ratio:float=0.5)->str:
        """Compact text dengan summarization heuristic"""
        lines=text.split("\n")
        keep=int(len(lines)*target_ratio)
        # Keep first 20%, last 30%, middle evenly sampled
        first=int(keep*0.2); last=int(keep*0.3); middle=keep-first-last
        sampled=[]
        if len(lines)>keep:
            sampled.extend(lines[:first])
            step=max(1,(len(lines)-first-last)//middle)
            sampled.extend(lines[first::step][:middle])
            sampled.extend(lines[-last:])
        else:
            sampled=lines
        return "\n".join(sampled)
    def get_size(self)->int: return self._current_size

class DoomLoopDetector:
    """Detect repetitive ineffective patterns"""
    def __init__(self,window_size:int=10,similarity_threshold:float=0.85):
        self.window_size=window_size; self.threshold=similarity_threshold
        self._history:List[str]=[]
    def record(self,action:str)->bool:
        """Record action, return True if doom loop detected"""
        self._history.append(action)
        if len(self._history)>self.window_size: self._history=self._history[-self.window_size:]
        if len(self._history)<3: return False
        # Check for repetition
        recent=self._history[-5:]
        unique=set(recent)
        if len(unique)==1: return True  # Exact same action 5 times
        # Check similarity
        for i in range(len(recent)-1):
            if self._similarity(recent[i],recent[i+1])>self.threshold:
                continue
        return len(unique)/len(recent)<0.4
    def _similarity(self,a:str,b:str)->float:
        aw=set(a.lower().split()); bw=set(b.lower().split())
        return len(aw&bw)/len(aw|bw) if aw|bw else 0.0
    def reset(self): self._history=[]

class ResearchScanner:
    """Scan dan extract dari research papers"""
    def __init__(self):
        self._papers:List[ResearchPaper]=[]
        self._arxiv_categories:List[str]=["cs.AI","cs.CL","cs.LG","cs.MA","stat.ML"]
    async def search(self,query:str,limit:int=10)->List[ResearchPaper]:
        """Search arXiv (simplified placeholder)"""
        import aiohttp
        try:
            url=f"http://export.arxiv.org/api/query?search_query=all:{query.replace(' ','+')}&max_results={limit}"
            async with aiohttp.ClientSession() as s:
                async with s.get(url,timeout=aiohttp.ClientTimeout(total=15)) as r:
                    if r.status==200:
                        text=await r.text()
                        # Parse simple (production: proper XML parsing)
                        papers=[]
                        # Placeholder: return mock
                        for i in range(min(limit,5)):
                            papers.append(ResearchPaper(title=f"Paper on {query} #{i+1}",year=2024,relevance_score=0.8-i*0.1))
                        return papers
        except: pass
        return [ResearchPaper(title=f"Mock paper: {query}",relevance_score=0.5)]
    def extract_findings(self,paper:ResearchPaper)->List[str]:
        """Extract key findings dari abstract"""
        findings=[]
        abstract=paper.abstract.lower()
        if "accuracy" in abstract: findings.append("Accuracy improvement reported")
        if "efficiency" in abstract or "speed" in abstract: findings.append("Efficiency gain reported")
        if "novel" in abstract: findings.append("Novel approach proposed")
        if not findings: findings.append("General methodology contribution")
        paper.extracted_findings=findings
        return findings

class DatasetBuilder:
    """Build dataset dari research findings"""
    def __init__(self,guard:ContextCompactionGuard):
        self.guard=guard; self._datasets:Dict[str,Dataset]={}
    async def build_from_papers(self,papers:List[ResearchPaper],task_type:str="qa")->Dataset:
        """Build dataset dari papers"""
        ds=Dataset(name=f"dataset-{task_type}-{len(papers)}papers")
        for paper in papers:
            for finding in paper.extracted_findings:
                if task_type=="qa":
                    ds.samples.append({"input":f"What is the main finding of {paper.title}?","output":finding,"source":paper.id})
                elif task_type=="summarization":
                    ds.samples.append({"input":paper.abstract[:500],"output":finding,"source":paper.id})
            ds.source_papers.append(paper.id)
        ds.sample_count=len(ds.samples)
        # Token estimation
        total_tokens=sum(len(s["input"].split())+len(s["output"].split()) for s in ds.samples)
        ds.avg_tokens_per_sample=total_tokens/max(ds.sample_count,1)
        self._datasets[ds.id]=ds
        return ds
    def split(self,dataset:Dataset)->Dict[str,List[Dict]]:
        n=len(dataset.samples)
        train=int(n*dataset.train_split)
        val=int(n*dataset.val_split)
        return {
            "train":dataset.samples[:train],
            "val":dataset.samples[train:train+val],
            "test":dataset.samples[train+val:]
        }

class Trainer:
    """Self-hosted training dengan PyTorch/LoRA concept"""
    def __init__(self):
        self._training_jobs:Dict[str,Dict]={}
    async def train(self,model_version:ModelVersion,dataset:Dataset,
                    config:Dict=None)->ModelVersion:
        """Train model (simulated - would use actual PyTorch)"""
        cfg=config or {"epochs":3,"batch_size":16,"learning_rate":2e-5,"lora_r":16}
        model_version.status=ModelStatus.TRAINING
        # Simulate training
        await asyncio.sleep(0.5)
        # Simulated metrics
        model_version.metrics={
            "loss":2.5*(0.6**cfg.get("epochs",3)),
            "accuracy":0.7+0.05*cfg.get("epochs",3),
            "perplexity":15.0*(0.8**cfg.get("epochs",3)),
            "training_duration_seconds":cfg.get("epochs",3)*300,
            "samples_processed":dataset.sample_count
        }
        model_version.status=ModelStatus.READY
        model_version.checkpoint_path=f"/models/{model_version.id}.pt"
        return model_version
    def estimate_compute(self,dataset_size:int,epochs:int=3)->Dict:
        """Estimate compute requirements"""
        return {
            "gpu_hours":dataset_size*epochs/10000,
            "memory_gb":16,
            "estimated_cost_usd":dataset_size*epochs*0.001
        }

class Evaluator:
    """Evaluate trained model"""
    def __init__(self):
        self._evaluations:Dict[str,Dict]={}
    async def evaluate(self,model_version:ModelVersion,test_data:List[Dict])->Dict:
        """Evaluate model"""
        # Simulated evaluation
        metrics={
            "accuracy":model_version.metrics.get("accuracy",0.7)+0.02,
            "f1_score":0.75,
            "latency_ms":120,
            "memory_mb":512,
            "test_samples":len(test_data)
        }
        self._evaluations[model_version.id]=metrics
        return metrics
    def compare_versions(self,versions:List[ModelVersion])->Dict:
        """Compare multiple model versions"""
        return {
            v.id:{
                "accuracy":v.metrics.get("accuracy",0),
                "status":v.status.value,
                "metrics":v.metrics
            } for v in versions
        }

class Deployer:
    """Deploy model ke serving infrastructure"""
    def __init__(self):
        self._deployments:Dict[str,Dict]={}
    async def deploy(self,model_version:ModelVersion,
                     ab_test:bool=False)->Dict:
        """Deploy model"""
        model_version.status=ModelStatus.DEPLOYED
        model_version.deployed_at=time.time()
        if ab_test:
            model_version.ab_test_group="A" if hash(model_version.id)%2==0 else "B"
        deployment={
            "model_id":model_version.id,
            "endpoint":f"/v1/models/{model_version.id}",
            "status":"live",
            "ab_test_group":model_version.ab_test_group,
            "deployed_at":model_version.deployed_at
        }
        self._deployments[model_version.id]=deployment
        return deployment
    def rollback(self,model_version:ModelVersion)->bool:
        model_version.status=ModelStatus.READY
        model_version.deployed_at=None
        self._deployments.pop(model_version.id,None)
        return True

class MLPipeline:
    """Main auto ML pipeline orchestrator"""
    def __init__(self):
        self.guard=ContextCompactionGuard()
        self.doom=DoomLoopDetector()
        self.scanner=ResearchScanner()
        self.dataset_builder=DatasetBuilder(self.guard)
        self.trainer=Trainer()
        self.evaluator=Evaluator()
        self.deployer=Deployer()
        self._models:Dict[str,ModelVersion]={}
        self._runs:List[Dict]=[]
        self._llm_callback:Optional[Callable]=None
    def set_llm_callback(self,cb:Callable): self._llm_callback=cb
    async def run(self,topic:str,base_model:str="llama-3.1-8b",task_type:str="qa")->Dict:
        """Full pipeline: research -> dataset -> train -> evaluate -> deploy"""
        run_id=str(uuid.uuid4())[:12]; start=time.time()
        try:
            # 1. Research
            if self.doom.record(f"research:{topic}"):
                return {"error":"Doom loop detected in research phase","run_id":run_id}
            papers=await self.scanner.search(topic,limit=5)
            for p in papers: self.scanner.extract_findings(p)
            # 2. Dataset
            if self.doom.record(f"dataset:{topic}"):
                return {"error":"Doom loop detected in dataset phase","run_id":run_id}
            ds=await self.dataset_builder.build_from_papers(papers,task_type)
            splits=self.dataset_builder.split(ds)
            # 3. Train
            model=ModelVersion(name=f"{topic}-model",base_model=base_model)
            self._models[model.id]=model
            if self.doom.record(f"train:{topic}"):
                return {"error":"Doom loop detected in training","run_id":run_id}
            await self.trainer.train(model,ds)
            # 4. Evaluate
            eval_result=await self.evaluator.evaluate(model,splits["test"])
            # 5. Deploy
            deployment=await self.deployer.deploy(model)
            result={"run_id":run_id,"status":"success","duration_seconds":time.time()-start,
                    "model_id":model.id,"papers":len(papers),"samples":ds.sample_count,
                    "metrics":model.metrics,"evaluation":eval_result,"deployment":deployment}
            self._runs.append(result)
            return result
        except Exception as e:
            return {"run_id":run_id,"status":"failed","error":str(e),"duration_seconds":time.time()-start}
    def get_status(self)->Dict:
        return {"models":len(self._models),"runs":len(self._runs),"deployments":len(self.deployer._deployments)}

if __name__=="__main__":
    async def demo():
        pipeline=MLPipeline()
        result=await pipeline.run("reinforcement learning trading","llama-3.1-8b","qa")
        print(json.dumps(result,indent=2,default=str))
        print(pipeline.get_status())
    asyncio.run(demo())
