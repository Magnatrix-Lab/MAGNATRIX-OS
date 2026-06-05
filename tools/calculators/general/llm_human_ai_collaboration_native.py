"""Human-AI Collaboration Framework — feedback loops, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum, auto
import time
import uuid

class FeedbackType(Enum):
    CORRECT = auto()
    INCORRECT = auto()
    PARTIAL = auto()
    SKIP = auto()

@dataclass
class CollaborationTurn:
    turn_id: str
    human_input: Dict
    ai_output: Dict
    feedback: Optional[FeedbackType] = None
    human_correction: Optional[Dict] = None
    timestamp: float = field(default_factory=time.time)

class HumanAICollaboration:
    def __init__(self, domain: str = "general"):
        self.domain = domain
        self.turns: List[CollaborationTurn] = []
        self.corrections_applied: int = 0
        self.feedback_counts: Dict[str, int] = {}

    def ai_turn(self, human_input: Dict) -> Dict:
        return {"prediction": self._baseline_predict(human_input), "confidence": 0.8}

    def _baseline_predict(self, inputs: Dict) -> Any:
        return sum(inputs.values()) if isinstance(inputs, dict) else inputs

    def record_feedback(self, turn_id: str, feedback: FeedbackType, correction: Optional[Dict] = None):
        for turn in self.turns:
            if turn.turn_id == turn_id:
                turn.feedback = feedback
                turn.human_correction = correction
                self.feedback_counts[feedback.name] = self.feedback_counts.get(feedback.name, 0) + 1
                if feedback == FeedbackType.INCORRECT and correction:
                    self.corrections_applied += 1
                return True
        return False

    def interact(self, human_input: Dict) -> CollaborationTurn:
        turn_id = str(uuid.uuid4())[:8]
        ai_out = self.ai_turn(human_input)
        turn = CollaborationTurn(turn_id, human_input, ai_out)
        self.turns.append(turn)
        return turn

    def accuracy_trend(self) -> List[float]:
        window = []
        trends = []
        for turn in self.turns:
            if turn.feedback == FeedbackType.CORRECT:
                window.append(1)
            elif turn.feedback == FeedbackType.INCORRECT:
                window.append(0)
            if len(window) >= 5:
                trends.append(sum(window[-5:]) / 5)
        return trends

    def stats(self) -> Dict:
        return {"domain": self.domain, "turns": len(self.turns), "corrections": self.corrections_applied, "feedback": self.feedback_counts, "trend": self.accuracy_trend()}

def run():
    collab = HumanAICollaboration(domain="medical")
    for i in range(6):
        turn = collab.interact({"symptom_a": i, "symptom_b": i * 2})
        if i % 3 == 0:
            collab.record_feedback(turn.turn_id, FeedbackType.CORRECT)
        elif i % 3 == 1:
            collab.record_feedback(turn.turn_id, FeedbackType.INCORRECT, {"correct": 42})
        else:
            collab.record_feedback(turn.turn_id, FeedbackType.PARTIAL)
    print(collab.stats())

if __name__ == "__main__":
    run()
