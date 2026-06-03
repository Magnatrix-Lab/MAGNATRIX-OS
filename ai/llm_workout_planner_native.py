"""LLM Workout Planner — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class ExerciseType(Enum):
    CARDIO = auto()
    STRENGTH = auto()
    FLEXIBILITY = auto()
    BALANCE = auto()
    HIIT = auto()

@dataclass
class Exercise:
    id: str
    name: str
    exercise_type: ExerciseType
    sets: int
    reps: int
    rest_seconds: int
    weight_kg: float = 0.0
    duration_min: float = 0.0

@dataclass
class WorkoutPlan:
    id: str
    name: str
    exercises: List[Exercise]
    total_duration_min: float
    difficulty: int
    target_muscles: List[str] = field(default_factory=list)

class WorkoutPlanner:
    def __init__(self) -> None:
        self._plans: Dict[str, WorkoutPlan] = {}
        self._exercises: Dict[str, Exercise] = {}

    def add_exercise(self, exercise: Exercise) -> None:
        self._exercises[exercise.id] = exercise

    def create_plan(self, plan_id: str, name: str, exercise_ids: List[str], difficulty: int = 1) -> WorkoutPlan:
        exercises = [self._exercises[eid] for eid in exercise_ids if eid in self._exercises]
        total = sum(e.duration_min + e.rest_seconds / 60 for e in exercises)
        plan = WorkoutPlan(plan_id, name, exercises, total, difficulty)
        self._plans[plan_id] = plan
        return plan

    def get_plan(self, plan_id: str) -> Optional[WorkoutPlan]:
        return self._plans.get(plan_id)

    def get_by_type(self, exercise_type: ExerciseType) -> List[Exercise]:
        return [e for e in self._exercises.values() if e.exercise_type == exercise_type]

    def estimate_calories(self, plan_id: str, weight_kg: float) -> float:
        plan = self._plans.get(plan_id)
        if not plan:
            return 0.0
        total = 0.0
        for e in plan.exercises:
            if e.exercise_type == ExerciseType.CARDIO:
                total += e.duration_min * weight_kg * 0.08
            elif e.exercise_type == ExerciseType.STRENGTH:
                total += e.sets * e.reps * weight_kg * 0.002
            elif e.exercise_type == ExerciseType.HIIT:
                total += e.duration_min * weight_kg * 0.12
            else:
                total += e.duration_min * weight_kg * 0.04
        return total

    def get_stats(self, plan_id: str) -> Dict[str, Any]:
        plan = self._plans.get(plan_id)
        if not plan:
            return {}
        types = {}
        for e in plan.exercises:
            types[e.exercise_type.name] = types.get(e.exercise_type.name, 0) + 1
        return {"exercises": len(plan.exercises), "duration": plan.total_duration_min, "difficulty": plan.difficulty, "by_type": types}

def run() -> None:
    print("Workout Planner test")
    e = WorkoutPlanner()
    e.add_exercise(Exercise("e1", "Push-ups", ExerciseType.STRENGTH, 3, 15, 60))
    e.add_exercise(Exercise("e2", "Running", ExerciseType.CARDIO, 1, 1, 0, 0, 30))
    e.add_exercise(Exercise("e3", "Squats", ExerciseType.STRENGTH, 4, 12, 90, 20))
    e.create_plan("p1", "Full Body", ["e1", "e2", "e3"], 2)
    print("  Plan exercises: " + str(len(e.get_plan("p1").exercises)))
    print("  Calories 70kg: " + str(e.estimate_calories("p1", 70)))
    print("  Stats: " + str(e.get_stats("p1")))
    print("Workout Planner test complete.")

if __name__ == "__main__":
    run()
