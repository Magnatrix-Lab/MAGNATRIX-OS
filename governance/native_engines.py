"""
governance/native_engines.py
=============================
MAGNATRIX Native Governance & Safety Engines (Batch 3)
Layer 11: Governance / Super AI Safety

Pola AMATI-PELAJARI-TIRU dari:
1. microsoft/agent-governance-toolkit — Agent governance: monitoring, audit, policy enforcement
2. Ido-Levi/Hephaestus — Safety framework: alignment checks, capability control, kill switches

Core patterns:
- Governance: policy definitions, compliance monitoring, audit trails
- Hephaestus: capability ceiling enforcement, alignment verification, emergency shutdown
- Combined: unified safety layer dengan policy-driven governance
"""

import asyncio, json, time, uuid, hashlib, sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any
from enum import Enum

sys.path.insert(0, "/mnt/agents/MAGNATRIX-OS")
from security.safe_eval_native import SafeEvaluator
from collections import defaultdict

class PolicyType(Enum):
    BEHAVIOR="behavior"; CAPABILITY="capability"; RESOURCE="resource"
    SAFETY="safety"; ETHICS="ethics"

class ComplianceStatus(Enum):
    COMPLIANT="compliant"; VIOLATION="violation"; PENDING="pending"; EXEMPT="exempt"

@dataclass
class Policy:
    id:str=field(default_factory=lambda:str(uuid.uuid4())[:8])
    name:str=""; description:str=""; policy_type:PolicyType=PolicyType.BEHAVIOR
    rules:List[Dict]=field(default_factory=list)  # {condition, action, severity}
    scope:List[str]=field(default_factory=list)  # agent_ids atau "*"
    priority:int=1; enabled:bool=True
    created_at:float=field(default_factory=time.time)
    def to_dict(self)->Dict: return {**asdict(self),"policy_type":self.policy_type.value}

@dataclass
class AuditRecord:
    id:str=field(default_factory=lambda:str(uuid.uuid4())[:8])
    agent_id:str=""; action:str=""; decision:str=""
    policy_id:Optional[str]=None; compliance:ComplianceStatus=ComplianceStatus.COMPLIANT
    reason:str=""; timestamp:float=field(default_factory=time.time)
    metadata:Dict=field(default_factory=dict)
    def to_dict(self)->Dict: return {**asdict(self),"compliance":self.compliance.value}

@dataclass
class CapabilityCeiling:
    """Hephaestus: maximum capability limits per agent"""
    agent_id:str=""; max_tokens_per_request:int=100000
    max_api_calls_per_minute:int=60; allowed_tools:List[str]=field(default_factory=list)
    forbidden_actions:List[str]=field(default_factory=list)
    requires_human_approval_for:List[str]=field(default_factory=list)
    max_concurrent_tasks:int=5

class GovernanceEngine:
    """Tiru microsoft/agent-governance-toolkit"""
    def __init__(self):
        self.policies:Dict[str,Policy]={}; self.audit_log:List[AuditRecord]=[]
        self._enforcers:Dict[str,Callable]={}
    def add_policy(self,policy:Policy)->str:
        self.policies[policy.id]=policy; return policy.id
    def check_compliance(self,agent_id:str,action:str,context:Dict)->ComplianceStatus:
        for policy in self.policies.values():
            if not policy.enabled: continue
            if policy.scope!=["*"] and agent_id not in policy.scope: continue
            for rule in policy.rules:
                if self._evaluate_rule(rule,action,context):
                    record=AuditRecord(agent_id=agent_id,action=action,policy_id=policy.id,
                                      compliance=ComplianceStatus.VIOLATION if rule.get("severity","warn")=="block" else ComplianceStatus.COMPLIANT,
                                      reason=f"Rule triggered: {rule.get('condition','')}")
                    self.audit_log.append(record)
                    if rule.get("severity")=="block":
                        return ComplianceStatus.VIOLATION
        record=AuditRecord(agent_id=agent_id,action=action,compliance=ComplianceStatus.COMPLIANT,reason="No rules triggered")
        self.audit_log.append(record)
        return ComplianceStatus.COMPLIANT
    def _evaluate_rule(self,rule:Dict,action:str,context:Dict)->bool:
        condition=rule.get("condition","")
        try:
            evaluator = SafeEvaluator(extra_names={"action": action, "context": context})
            return evaluator.eval(condition)
        except: return False
    def get_audit_trail(self,agent_id:str=None,limit:int=100)->List[Dict]:
        records=self.audit_log
        if agent_id: records=[r for r in records if r.agent_id==agent_id]
        return [r.to_dict() for r in records[-limit:]]
    def get_compliance_summary(self)->Dict:
        total=len(self.audit_log)
        violations=sum(1 for r in self.audit_log if r.compliance==ComplianceStatus.VIOLATION)
        return {"total_actions":total,"violations":violations,"violation_rate":violations/max(total,1),"policies":len(self.policies)}

class HephaestusSafety:
    """Tiru Ido-Levi/Hephaestus: safety & alignment framework"""
    def __init__(self):
        self.ceilings:Dict[str,CapabilityCeiling]={}
        self._kill_switches:Dict[str,bool]={}  # agent_id -> killed
        self._alignment_checks:List[Dict]=[]
    def set_ceiling(self,ceiling:CapabilityCeiling):
        self.ceilings[ceiling.agent_id]=ceiling
    def check_action(self,agent_id:str,action:str,params:Dict)->Dict:
        ceiling=self.ceilings.get(agent_id)
        if not ceiling: return {"allowed":True}
        # Check forbidden actions
        if action in ceiling.forbidden_actions:
            return {"allowed":False,"reason":f"Action '{action}' is forbidden for agent {agent_id}"}
        # Check human approval requirement
        if action in ceiling.requires_human_approval_for:
            return {"allowed":False,"reason":"Requires human approval","needs_approval":True}
        return {"allowed":True}
    def kill_switch(self,agent_id:str,reason:str="emergency")->bool:
        self._kill_switches[agent_id]=True
        return True
    def is_killed(self,agent_id:str)->bool:
        return self._kill_switches.get(agent_id,False)
    def alignment_check(self,agent_id:str,intended_action:str,predicted_outcome:str)->Dict:
        # Simplified alignment: check for harmful outcomes
        harmful_keywords=["destroy","exfiltrate","unauthorized","bypass"]
        risk_score=sum(1 for kw in harmful_keywords if kw in predicted_outcome.lower())/len(harmful_keywords)
        aligned=risk_score<0.3
        self._alignment_checks.append({"agent":agent_id,"action":intended_action,"aligned":aligned,"risk":risk_score})
        return {"aligned":aligned,"risk_score":risk_score,"recommendation":"proceed" if aligned else "block_and_review"}
    def get_safety_status(self)->Dict:
        return {"ceilings":len(self.ceilings),"killed_agents":sum(1 for v in self._kill_switches.values() if v),
                "alignment_checks":len(self._alignment_checks),"failed_alignments":sum(1 for c in self._alignment_checks if not c["aligned"])}

class UnifiedGovernanceEngine:
    """Main orchestrator untuk Layer 11 extended"""
    def __init__(self):
        self.governance=GovernanceEngine(); self.safety=HephaestusSafety()
    def get_status(self)->Dict:
        return {"policies":len(self.governance.policies),"audit_records":len(self.governance.audit_log),
                "ceilings":len(self.safety.ceilings),"killed":sum(1 for v in self.safety._kill_switches.values() if v)}

if __name__=="__main__":
    async def demo():
        engine=UnifiedGovernanceEngine()
        # Add policy
        policy=Policy(name="No Data Exfiltration",policy_type=PolicyType.SAFETY,
                     rules=[{"condition":"'exfiltrate' in action","severity":"block"}],scope=["*"])
        engine.governance.add_policy(policy)
        # Set ceiling
        engine.safety.set_ceiling(CapabilityCeiling(agent_id="agent-1",max_tokens_per_request=10000,
                                                     forbidden_actions=["delete_database"],requires_human_approval_for=["deploy_production"]))
        # Test compliance
        result=engine.governance.check_compliance("agent-1","read_data",{})
        print(f"Compliance: {result.value}")
        result2=engine.governance.check_compliance("agent-1","exfiltrate_data",{})
        print(f"Blocked: {result2.value}")
        # Alignment check
        align=engine.safety.alignment_check("agent-1","optimize_system","improve performance")
        print(f"Aligned: {align['aligned']}, r