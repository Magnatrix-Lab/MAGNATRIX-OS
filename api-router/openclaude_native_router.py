"""
openclaude_native_router.py
===========================
MAGNATRIX Native Multi-Provider LLM Router
Layer 1.5: API Router

Pola AMATI-PELAJARI-TIRU dari openclaude multi-provider routing:
- Multi-provider routing: cost/latency/quality/random strategy
- OpenAI-compatible streaming API
- Tool loop execution (recursive tool calling)
- Batch parallel execution untuk multiple providers
- Rate limit tracking per provider
"""

import asyncio, json, time, uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator
from enum import Enum
from collections import defaultdict

class RoutingStrategy(Enum):
    COST="cost"; LATENCY="latency"; QUALITY="quality"
    RANDOM="random"; ROUND_ROBIN="round_robin"; FAILOVER="failover"

class ProviderStatus(Enum):
    HEALTHY="healthy"; DEGRADED="degraded"; DOWN="down"

@dataclass
class Provider:
    id:str=field(default_factory=lambda:str(uuid.uuid4())[:8])
    name:str=""; base_url:str=""; api_key:str=""
    models:List[str]=field(default_factory=list)
    status:ProviderStatus=ProviderStatus.HEALTHY
    # Metrics
    avg_latency_ms:float=200.0; success_rate:float=1.0
    cost_per_1k_input:float=0.0; cost_per_1k_output:float=0.0
    quality_score:float=0.8; last_used:float=0.0
    # Limits
    rate_limit_rpm:int=60; current_rpm:int=0
    # Fallback
    fallback_provider:Optional[str]=None
    def to_dict(self)->Dict: return {**asdict(self),"status":self.status.value}

@dataclass
class LLMRequest:
    model:str=""; messages:List[Dict]=field(default_factory=list)
    temperature:float=0.7; max_tokens:int=1024
    tools:Optional[List[Dict]]=None; stream:bool=False
    strategy:RoutingStrategy=RoutingStrategy.QUALITY
    user_id:str=""; request_id:str=field(default_factory=lambda:str(uuid.uuid4())[:12])
    def to_dict(self)->Dict: return asdict(self)

@dataclass
class LLMResponse:
    content:str=""; model:str=""; provider_id:str=""
    input_tokens:int=0; output_tokens:int=0
    latency_ms:float=0.0; cost_usd:float=0.0
    tool_calls:Optional[List[Dict]]=None
    finish_reason:str="stop"; error:Optional[str]=None
    def to_dict(self)->Dict: return asdict(self)

class StreamingHandler:
    """Handle streaming responses"""
    def __init__(self):
        self._streams:Dict[str,Any]={}
    async def stream(self,request:LLMRequest,provider:Provider,
                     llm_call:Callable)->AsyncGenerator[str,None]:
        start=time.time()
        try:
            if asyncio.iscoroutinefunction(llm_call):
                async for chunk in llm_call(request,provider):
                    yield chunk
            else:
                yield llm_call(request,provider)
        except Exception as e:
            yield f"[ERROR:{e}]"
        provider.last_used=time.time()
        provider.avg_latency_ms=(provider.avg_latency_ms*0.9+(time.time()-start)*1000*0.1)

class ToolLoopExecutor:
    """Execute recursive tool calling loops"""
    def __init__(self,tool_registry:Dict[str,Callable]):
        self.tools=tool_registry; self._max_iterations:int=10
    async def execute(self,request:LLMRequest,llm_call:Callable,
                      provider:Provider)->LLMResponse:
        messages=list(request.messages)
        for i in range(self._max_iterations):
            response=await self._call_llm(messages,request,llm_call,provider)
            if not response.tool_calls:
                return response
            # Execute tools
            tool_results=[]
            for tc in response.tool_calls:
                tool_fn=self.tools.get(tc.get("function",{}).get("name",""))
                if tool_fn:
                    args=json.loads(tc.get("function",{}).get("arguments","{}"))
                    try:
                        if asyncio.iscoroutinefunction(tool_fn):
                            result=await tool_fn(**args)
                        else:
                            result=tool_fn(**args)
                        tool_results.append({"role":"tool","tool_call_id":tc.get("id",""),"content":str(result)})
                    except Exception as e:
                        tool_results.append({"role":"tool","tool_call_id":tc.get("id",""),"content":f"Error:{e}"})
            messages.append({"role":"assistant","content":response.content or "","tool_calls":response.tool_calls})
            messages.extend(tool_results)
        return response
    async def _call_llm(self,messages,request,llm_call,provider)->LLMResponse:
        req=LLMRequest(model=request.model,messages=messages,temperature=request.temperature,
                       max_tokens=request.max_tokens,stream=False)
        if asyncio.iscoroutinefunction(llm_call):
            return await llm_call(req,provider)
        return llm_call(req,provider)

class BatchExecutor:
    """Execute multiple requests in parallel across providers"""
    def __init__(self,router:'LLMRouter'):
        self.router=router
    async def execute_batch(self,requests:List[LLMRequest])->List[LLMResponse]:
        tasks=[]
        for req in requests:
            provider=self.router.select_provider(req)
            if provider:
                t=self.router.execute(req,provider)
                tasks.append(t)
        results=await asyncio.gather(*tasks,return_exceptions=True)
        valid=[]
        for r in results:
            if isinstance(r,LLMResponse): valid.append(r)
            else: valid.append(LLMResponse(error=str(r)))
        return valid

class LLMRouter:
    """Main multi-provider LLM router"""
    def __init__(self):
        self.providers:Dict[str,Provider]={}
        self._strategy=RoutingStrategy.QUALITY
        self._round_robin_idx:int=0
        self.streaming=StreamingHandler()
        self.tools:Dict[str,Callable]={}
        self.tool_loop=ToolLoopExecutor(self.tools)
        self.batch=BatchExecutor(self)
        self._usage:Dict[str,List[Dict]]=defaultdict(list)
        self._llm_call:Optional[Callable]=None
    def set_llm_call(self,call:Callable): self._llm_call=call
    def register_provider(self,provider:Provider)->str:
        self.providers[provider.id]=provider; return provider.id
    def register_tool(self,name:str,handler:Callable): self.tools[name]=handler; self.tool_loop=ToolLoopExecutor(self.tools)
    def select_provider(self,request:LLMRequest)->Optional[Provider]:
        strategy=request.strategy or self._strategy
        candidates=[p for p in self.providers.values() if p.status==ProviderStatus.HEALTHY and request.model in p.models]
        if not candidates:
            # Try any available dengan model wildcard
            candidates=[p for p in self.providers.values() if p.status!=ProviderStatus.DOWN]
        if not candidates: return None
        if strategy==RoutingStrategy.COST:
            return min(candidates,key=lambda p:p.cost_per_1k_input+p.cost_per_1k_output)
        elif strategy==RoutingStrategy.LATENCY:
            return min(candidates,key=lambda p:p.avg_latency_ms)
        elif strategy==RoutingStrategy.QUALITY:
            return max(candidates,key=lambda p:p.quality_score*p.success_rate)
        elif strategy==RoutingStrategy.RANDOM:
            import random; return random.choice(candidates)
        elif strategy==RoutingStrategy.ROUND_ROBIN:
            idx=self._round_robin_idx%len(candidates); self._round_robin_idx+=1
            return candidates[idx]
        elif strategy==RoutingStrategy.FAILOVER:
            for p in sorted(candidates,key=lambda p:p.success_rate,reverse=True):
                if p.current_rpm<p.rate_limit_rpm: return p
            return None
        return candidates[0]
    async def execute(self,request:LLMRequest,provider:Optional[Provider]=None)->LLMResponse:
        if not provider: provider=self.select_provider(request)
        if not provider: return LLMResponse(error="No available provider")
        start=time.time()
        try:
            if request.tools:
                response=await self.tool_loop.execute(request,self._llm_call,provider)
            else:
                if asyncio.iscoroutinefunction(self._llm_call):
                    response=await self._llm_call(request,provider)
                else:
                    response=self._llm_call(request,provider)
            if not isinstance(response,LLMResponse): response=LLMResponse(content=str(response))
            response.provider_id=provider.id
            response.latency_ms=(time.time()-start)*1000
            response.cost_usd=(response.input_tokens/1000*provider.cost_per_1k_input+
                             response.output_tokens/1000*provider.cost_per_1k_output)
            provider.last_used=time.time(); provider.current_rpm+=1
            self._usage[request.user_id].append({"provider":provider.id,"model":request.model,"tokens":response.input_tokens+response.output_tokens,"cost":response.cost_usd})
            return response
        except Exception as e:
            provider.success_rate*=0.95
            if provider.success_rate<0.5: provider.status=ProviderStatus.DEGRADED
            return LLMResponse(error=str(e),provider_id=provider.id)
    async def stream(self,request:LLMRequest)->AsyncGenerator[str,None]:
        provider=self.select_provider(request)
        if not provider:
            yield "[ERROR:No provider available]"; return
        async for chunk in self.streaming.stream(request,provider,self._llm_call):
            yield chunk
    def get_usage(self,user_id:str)->Dict:
        records=self._usage.get(user_id,[])
        return {"requests":len(records),"total_tokens":sum(r["tokens"]for r in records),"total_cost_usd":sum(r["cost"]for r in records)}
    def get_status(self)->Dict:
        return {"providers":len(self.providers),"healthy":sum(1 for p in self.providers.values() if p.status==ProviderStatus.HEALTHY),
                "tools":len(self.tools),"strategy":self._strategy.value}

if __name__=="__main__":
    async def demo():
        router=LLMRouter()
        router.register_provider(Provider(name="OpenAI",models=["gpt-4o","gpt-4o-mini"],cost_per_1k_input=5.0,cost_per_1k_output=15.0,quality_score=0.95))
        router.register_provider(Provider(name="Anthropic",models=["claude-3-5-sonnet"],cost_per_1k_input=3.0,cost_per_1k_output=15.0,quality_score=0.93))
        print(router.get_status())
    asyncio.run(demo())
