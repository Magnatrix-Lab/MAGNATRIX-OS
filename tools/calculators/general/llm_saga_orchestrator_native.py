"""Saga Orchestrator — distributed transaction compensation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Any, Optional
from enum import Enum, auto

class SagaStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    COMPENSATING = auto()
    FAILED = auto()

@dataclass
class SagaStep:
    step_id: str
    action: Callable[[], bool]
    compensation: Callable[[], bool]
    status: SagaStatus = SagaStatus.PENDING

class SagaOrchestrator:
    def __init__(self, saga_id: str):
        self.saga_id = saga_id
        self.steps: List[SagaStep] = []
        self.status = SagaStatus.PENDING
        self.completed_steps: List[str] = []
        self.failed_step: Optional[str] = None

    def add_step(self, step_id: str, action: Callable[[], bool], compensation: Callable[[], bool]):
        self.steps.append(SagaStep(step_id, action, compensation))

    def execute(self) -> bool:
        self.status = SagaStatus.RUNNING
        for step in self.steps:
            step.status = SagaStatus.RUNNING
            try:
                success = step.action()
            except:
                success = False
            if success:
                step.status = SagaStatus.COMPLETED
                self.completed_steps.append(step.step_id)
            else:
                step.status = SagaStatus.FAILED
                self.failed_step = step.step_id
                self._compensate()
                return False
        self.status = SagaStatus.COMPLETED
        return True

    def _compensate(self):
        self.status = SagaStatus.COMPENSATING
        for step_id in reversed(self.completed_steps):
            step = next((s for s in self.steps if s.step_id == step_id), None)
            if step:
                try:
                    step.compensation()
                except:
                    pass
        self.status = SagaStatus.FAILED

    def stats(self) -> Dict:
        return {"saga_id": self.saga_id, "status": self.status.name, "steps": len(self.steps), "completed": len(self.completed_steps), "failed_step": self.failed_step}

def run():
    saga = SagaOrchestrator("order_saga")
    results = {"inventory": False, "payment": False}
    def reserve_inventory():
        results["inventory"] = True
        return True
    def release_inventory():
        results["inventory"] = False
        return True
    def process_payment():
        return False
    def refund_payment():
        return True
    saga.add_step("reserve_inventory", reserve_inventory, release_inventory)
    saga.add_step("process_payment", process_payment, refund_payment)
    success = saga.execute()
    print("Success:", success, "Results:", results)
    print(saga.stats())

if __name__ == "__main__":
    run()
