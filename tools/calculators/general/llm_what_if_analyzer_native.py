"""What-If Scenario Analyzer — simulation of changes, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional
from enum import Enum, auto
import copy

class ScenarioType(Enum):
    INCREASE = auto()
    DECREASE = auto()
    REPLACE = auto()
    ADD = auto()

@dataclass
class WhatIfScenario:
    scenario_id: str
    changes: Dict[str, any]
    baseline: Dict
    predicted: Dict = field(default_factory=dict)
    impact: Dict = field(default_factory=dict)

class WhatIfAnalyzer:
    def __init__(self, model: Callable[[Dict], Dict]):
        self.model = model
        self.baseline: Dict = {}
        self.scenarios: List[WhatIfScenario] = []

    def set_baseline(self, baseline: Dict):
        self.baseline = baseline

    def add_scenario(self, scenario_id: str, changes: Dict) -> WhatIfScenario:
        scenario = WhatIfScenario(scenario_id, changes, self.baseline)
        self.scenarios.append(scenario)
        return scenario

    def run(self, scenario_id: Optional[str] = None) -> List[WhatIfScenario]:
        targets = [s for s in self.scenarios if s.scenario_id == scenario_id] if scenario_id else self.scenarios
        for s in targets:
            modified = copy.deepcopy(s.baseline)
            modified.update(s.changes)
            s.predicted = self.model(modified)
            baseline_pred = self.model(s.baseline)
            s.impact = {k: s.predicted.get(k, 0) - baseline_pred.get(k, 0) for k in set(s.predicted) | set(baseline_pred)}
        return targets

    def compare(self) -> List[Dict]:
        return [{"id": s.scenario_id, "changes": s.changes, "impact": s.impact, "predicted": s.predicted} for s in self.scenarios]

    def best_scenario(self, metric: str, maximize: bool = True) -> Optional[str]:
        if not self.scenarios:
            return None
        sorted_scenarios = sorted(self.scenarios, key=lambda s: s.impact.get(metric, 0), reverse=maximize)
        return sorted_scenarios[0].scenario_id if sorted_scenarios else None

    def stats(self) -> Dict:
        return {"baseline_keys": len(self.baseline), "scenarios": len(self.scenarios), "run": len([s for s in self.scenarios if s.predicted])}

def run():
    def model(inputs):
        return {"revenue": inputs.get("price", 0) * inputs.get("volume", 0), "cost": inputs.get("cost", 0) * inputs.get("volume", 0)}
    analyzer = WhatIfAnalyzer(model)
    analyzer.set_baseline({"price": 10, "volume": 100, "cost": 5})
    analyzer.add_scenario("raise_price", {"price": 12})
    analyzer.add_scenario("increase_volume", {"volume": 150})
    analyzer.add_scenario("lower_cost", {"cost": 4})
    analyzer.run()
    for s in analyzer.compare():
        print(s["id"], s["impact"])
    print(analyzer.stats())

if __name__ == "__main__":
    run()
