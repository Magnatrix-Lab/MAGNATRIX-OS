"""
medical_qa_system_native.py
MAGNATRIX-OS — Medical QA System

Inspired by Meditron (EPFL): Medical question answering with evidence retrieval. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class MedicalQuestion:
    question_id: str
    question: str
    category: str
    options: List[str] = field(default_factory=list)
    correct_answer: str = ""
    explanation: str = ""
    evidence: List[str] = field(default_factory=list)


@dataclass
class MedicalAnswer:
    answer_id: str
    question_id: str
    selected_answer: str
    is_correct: bool
    confidence: float
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class MedicalQASystem:
    """Medical question answering with evidence retrieval and scoring."""

    def __init__(self, qa_dir: str = "./medical_qa"):
        self.qa_dir = Path(qa_dir)
        self.qa_dir.mkdir(exist_ok=True)
        self.questions: Dict[str, MedicalQuestion] = {}
        self.answers: List[MedicalAnswer] = []
        self._load()

    def _load(self) -> None:
        for fname in ["questions.json", "answers.json"]:
            f = self.qa_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "questions.json":
                            for qid, qd in data.items():
                                self.questions[qid] = MedicalQuestion(**qd)
                        else:
                            self.answers = [MedicalAnswer(**a) for a in data]
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.qa_dir / "questions.json", "w", encoding="utf-8") as f:
            json.dump({qid: asdict(q) for qid, q in self.questions.items()}, f, indent=2)
        with open(self.qa_dir / "answers.json", "w", encoding="utf-8") as f:
            json.dump([asdict(a) for a in self.answers], f, indent=2)

    def add_question(self, question_id: str, question: str, category: str, options: List[str],
                     correct_answer: str, explanation: str = "", evidence: Optional[List[str]] = None) -> MedicalQuestion:
        q = MedicalQuestion(
            question_id=question_id, question=question, category=category, options=options,
            correct_answer=correct_answer, explanation=explanation, evidence=evidence or [],
        )
        self.questions[question_id] = q
        self._save()
        return q

    def answer(self, question_id: str, selected: str, confidence: float = 0.5) -> MedicalAnswer:
        q = self.questions.get(question_id)
        is_correct = q.correct_answer == selected if q else False
        ans = MedicalAnswer(
            answer_id=f"{question_id}_{len(self.answers)}", question_id=question_id,
            selected_answer=selected, is_correct=is_correct, confidence=confidence,
        )
        self.answers.append(ans)
        self._save()
        return ans

    def get_score(self, category: Optional[str] = None) -> Dict[str, Any]:
        answers = self.answers
        if category:
            qids = [qid for qid, q in self.questions.items() if q.category == category]
            answers = [a for a in answers if a.question_id in qids]
        total = len(answers)
        correct = sum(1 for a in answers if a.is_correct)
        accuracy = correct / max(1, total)
        return {"total": total, "correct": correct, "accuracy": round(accuracy, 2)}

    def get_question(self, question_id: str) -> Optional[MedicalQuestion]:
        return self.questions.get(question_id)

    def get_stats(self) -> Dict[str, Any]:
        return {"questions": len(self.questions), "answers": len(self.answers)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MedicalQASystem", "MedicalQuestion", "MedicalAnswer"]