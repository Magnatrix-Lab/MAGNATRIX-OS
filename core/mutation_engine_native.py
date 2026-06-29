
"""
mutation_engine_native.py
MAGNATRIX-OS — Mutation Engine

Inspired by A-Evolve mutation operators: mutates real files in workspace.
Skills, prompts, memory entries, and hyperparameters.
Pure Python standard library.
"""

import random
import copy
import hashlib
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from pathlib import Path


class MutationType:
    SKILL_ADD = "skill_add"
    SKILL_REMOVE = "skill_remove"
    SKILL_MODIFY = "skill_modify"
    PROMPT_REWRITE = "prompt_rewrite"
    PROMPT_APPEND = "prompt_append"
    MEMORY_ADD = "memory_add"
    MEMORY_PRUNE = "memory_prune"
    HYPERPARAM_TWEAK = "hyperparam_tweak"
    HYPERPARAM_ADD = "hyperparam_add"
    STRUCTURE_REORDER = "structure_reorder"


class MutationEngine:
    """Genetic mutation and crossover operators for agent evolution."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        self._mutators: Dict[str, Callable] = {
            MutationType.SKILL_ADD: self._mutate_skill_add,
            MutationType.SKILL_REMOVE: self._mutate_skill_remove,
            MutationType.SKILL_MODIFY: self._mutate_skill_modify,
            MutationType.PROMPT_REWRITE: self._mutate_prompt_rewrite,
            MutationType.PROMPT_APPEND: self._mutate_prompt_append,
            MutationType.MEMORY_ADD: self._mutate_memory_add,
            MutationType.MEMORY_PRUNE: self._mutate_memory_prune,
            MutationType.HYPERPARAM_TWEAK: self._mutate_hyperparam_tweak,
            MutationType.HYPERPARAM_ADD: self._mutate_hyperparam_add,
            MutationType.STRUCTURE_REORDER: self._mutate_structure_reorder,
        }

    def mutate(self, genome, rate: float = 0.3) -> Any:
        """Apply random mutations to a genome with given probability."""
        from .agent_evolution_engine_native import AgentGenome
        child = copy.deepcopy(genome)
        child.agent_id = f"mut_{genome.agent_id}_{int(random.random() * 10000)}"
        child.generation = genome.generation + 1
        child.parent_ids = [genome.agent_id]
        child.mutation_log = list(genome.mutation_log)

        mutations_applied = []
        for mut_type, mutator in self._mutators.items():
            if random.random() < rate:
                try:
                    mutator(child)
                    mutations_applied.append(mut_type)
                except Exception:
                    pass

        if mutations_applied:
            child.mutation_log.append(f"mutated:{','.join(mutations_applied)}")
        return child

    def crossover(self, parent1, parent2) -> Any:
        """Create a child genome by combining two parents."""
        from .agent_evolution_engine_native import AgentGenome
        child = AgentGenome(
            agent_id=f"cross_{parent1.agent_id}_{parent2.agent_id}_{int(random.random() * 10000)}",
            system_prompt=parent1.system_prompt if random.random() < 0.5 else parent2.system_prompt,
            skills=self._merge_skills(parent1.skills, parent2.skills),
            memory_entries=parent1.memory_entries + parent2.memory_entries,
            hyperparams=self._merge_hyperparams(parent1.hyperparams, parent2.hyperparams),
            generation=max(parent1.generation, parent2.generation) + 1,
            parent_ids=[parent1.agent_id, parent2.agent_id],
        )
        child.mutation_log.append(f"crossover:parents={parent1.agent_id},{parent2.agent_id}")
        return child

    def _mutate_skill_add(self, genome) -> None:
        skill_templates = {
            "error-handling": "Handle common errors gracefully.",
            "retry-logic": "Retry failed operations with exponential backoff.",
            "validation": "Validate inputs before processing.",
            "logging": "Log all operations for debugging.",
            "caching": "Cache frequently accessed data.",
            "search": "Search for information before acting.",
            "iteration": "Iterate until the goal is achieved.",
            "verification": "Verify results before finalizing.",
        }
        available = set(skill_templates.keys()) - set(genome.skills.keys())
        if available:
            new_skill = random.choice(list(available))
            genome.skills[new_skill] = skill_templates[new_skill]

    def _mutate_skill_remove(self, genome) -> None:
        if len(genome.skills) > 1:
            to_remove = random.choice(list(genome.skills.keys()))
            del genome.skills[to_remove]

    def _mutate_skill_modify(self, genome) -> None:
        if genome.skills:
            skill = random.choice(list(genome.skills.keys()))
            genome.skills[skill] += "\n\n[Enhanced] " + genome.skills[skill]

    def _mutate_prompt_rewrite(self, genome) -> None:
        if genome.system_prompt:
            genome.system_prompt = f"[Evolved] {genome.system_prompt}"

    def _mutate_prompt_append(self, genome) -> None:
        additions = [
            "\n\nThink step by step before acting.",
            "\n\nVerify all outputs before returning results.",
            "\n\nUse tools when appropriate to extend capabilities.",
            "\n\nMaintain a working memory of past actions.",
        ]
        genome.system_prompt += random.choice(additions)

    def _mutate_memory_add(self, genome) -> None:
        genome.memory_entries.append({
            "type": "episodic",
            "content": f"Learned from generation {genome.generation}",
            "timestamp": None,
        })

    def _mutate_memory_prune(self, genome) -> None:
        if len(genome.memory_entries) > 3:
            genome.memory_entries = genome.memory_entries[-3:]

    def _mutate_hyperparam_tweak(self, genome) -> None:
        for k, v in list(genome.hyperparams.items()):
            if isinstance(v, (int, float)):
                genome.hyperparams[k] = v * random.uniform(0.8, 1.2)

    def _mutate_hyperparam_add(self, genome) -> None:
        new_params = {
            "temperature": random.uniform(0.0, 1.0),
            "max_tokens": random.choice([512, 1024, 2048, 4096]),
            "top_p": random.uniform(0.5, 1.0),
            "timeout": random.choice([10, 30, 60, 120]),
            "retries": random.choice([1, 2, 3, 5]),
        }
        for k, v in new_params.items():
            if k not in genome.hyperparams:
                genome.hyperparams[k] = v

    def _mutate_structure_reorder(self, genome) -> None:
        if len(genome.skills) > 2:
            keys = list(genome.skills.keys())
            random.shuffle(keys)
            genome.skills = {k: genome.skills[k] for k in keys}

    def _merge_skills(self, s1: Dict, s2: Dict) -> Dict:
        merged = {**s1}
        for k, v in s2.items():
            if k not in merged:
                merged[k] = v
            elif random.random() < 0.5:
                merged[k] = v
        return merged

    def _merge_hyperparams(self, h1: Dict, h2: Dict) -> Dict:
        merged = {**h1}
        for k, v in h2.items():
            if k not in merged:
                merged[k] = v
            elif isinstance(v, (int, float)) and isinstance(merged[k], (int, float)):
                merged[k] = (merged[k] + v) / 2
            elif random.random() < 0.5:
                merged[k] = v
        return merged


__all__ = ["MutationEngine", "MutationType"]
