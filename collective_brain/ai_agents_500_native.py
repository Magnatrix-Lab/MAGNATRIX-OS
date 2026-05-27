"""
MAGNATRIX — 500 AI Agents Architecture Patterns
Native Python implementation of 24+ agent architecture patterns.
Observed from: ashishpatel26/500-AI-Agents-Projects and canonical agent papers.

Pattern: AMATI-PELAJARI-TIRU — observe core patterns, reimplement as consolidated module.
"""
from __future__ import annotations

import asyncio
import json
import math
import random
import re
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Protocol, Set, Tuple, Union


# ═══════════════════════════════════════════════════════════════════════════════
# BASE CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class AgentStatus(Enum):
    IDLE = auto()
    THINKING = auto()
    ACTING = auto()
    WAITING = auto()
    DONE = auto()


@dataclass
class BaseTask:
    id: str = field(default_factory=lambda: f"t_{uuid.uuid4().hex[:6]}")
    description: str = ""
    status: str = "pending"
    result: Any = None
    priority: int = 5
    created_at: float = field(default_factory=time.time)


@dataclass
class MemoryEntry:
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    importance: float = 1.0
    tags: List[str] = field(default_factory=list)


class BaseMemory:
    """Memory stream untuk agents (Generative Agents-style)."""

    def __init__(self, capacity: int = 100) -> None:
        self.short_term: deque[MemoryEntry] = deque(maxlen=capacity)
        self.long_term: List[MemoryEntry] = []
        self.reflections: List[str] = []

    def add(self, content: str, importance: float = 1.0, tags: Optional[List[str]] = None) -> None:
        entry = MemoryEntry(content, time.time(), importance, tags or [])
        self.short_term.append(entry)
        if importance >= 7.0:
            self.long_term.append(entry)

    def recall(self, query: str, k: int = 5) -> List[MemoryEntry]:
        all_mem = list(self.short_term) + self.long_term
        scored = [(m, self._relevance(m, query)) for m in all_mem]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored[:k]]

    def _relevance(self, mem: MemoryEntry, query: str) -> float:
        query_words = set(query.lower().split())
        mem_words = set(mem.content.lower().split())
        overlap = len(query_words & mem_words)
        return overlap * mem.importance

    def reflect(self) -> str:
        """Generate reflection dari recent memories."""
        recent = list(self.short_term)[-10:]
        if not recent:
            return "No memories to reflect on."
        topics = set()
        for mem in recent:
            topics.update(mem.content.lower().split()[:3])
        reflection = f"Reflection on {len(recent)} recent events: themes include {', '.join(list(topics)[:5])}."
        self.reflections.append(reflection)
        return reflection

    def __repr__(self) -> str:
        return f"BaseMemory(short={len(self.short_term)}, long={len(self.long_term)}, reflections={len(self.reflections)})"


class BaseTool:
    """Tool yang bisa dipanggil agent."""

    def __init__(self, name: str, func: Callable[..., Any], description: str = "") -> None:
        self.name = name
        self.func = func
        self.description = description

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)

    def __repr__(self) -> str:
        return f"BaseTool({self.name})"


class ToolRegistry:
    """Registry untuk tools."""

    def __init__(self) -> None:
        self.tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self.tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        return self.tools[name]

    def list_tools(self) -> List[str]:
        return list(self.tools.keys())

    def __repr__(self) -> str:
        return f"ToolRegistry({list(self.tools.keys())})"


class BaseAgent:
    """Base agent class."""

    def __init__(self, name: str, role: str = "agent") -> None:
        self.name = name
        self.role = role
        self.memory = BaseMemory()
        self.status = AgentStatus.IDLE
        self.tools = ToolRegistry()
        self.task_history: List[BaseTask] = []

    def add_tool(self, tool: BaseTool) -> None:
        self.tools.register(tool)

    async def think(self, context: str) -> str:
        self.status = AgentStatus.THINKING
        await asyncio.sleep(0.01)
        return f"[{self.name}] Thought about: {context[:50]}"

    async def act(self, action: str) -> str:
        self.status = AgentStatus.ACTING
        await asyncio.sleep(0.01)
        return f"[{self.name}] Action: {action[:50]}"

    def __repr__(self) -> str:
        return f"BaseAgent({self.name}, {self.role}, {self.status.name})"


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 1: ReAct — Reasoning + Acting
# ═══════════════════════════════════════════════════════════════════════════════

class ReActAgent(BaseAgent):
    """
    ReAct: Synergizing Reasoning and Acting in Language Models (Yao et al., 2022)
    Loop: Thought → Action → Observation → ... → Answer
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "react")
        self.max_steps = 10

    async def run(self, query: str) -> Dict[str, Any]:
        trajectory: List[Dict[str, str]] = []
        for step in range(self.max_steps):
            thought = await self.think(query + " | Step " + str(step))
            trajectory.append({"type": "thought", "content": thought})

            # Decide action
            action = self._choose_action(thought)
            trajectory.append({"type": "action", "content": action})

            # Execute
            obs = await self._execute_action(action)
            trajectory.append({"type": "observation", "content": obs})

            if self._is_answer(action):
                return {"answer": action, "trajectory": trajectory, "steps": step + 1}

        return {"answer": "No answer found", "trajectory": trajectory, "steps": self.max_steps}

    def _choose_action(self, thought: str) -> str:
        tools = self.tools.list_tools()
        if tools and "search" in thought.lower():
            return f"search[{thought[20:40]}]"
        return f"finish[{thought}]"

    async def _execute_action(self, action: str) -> str:
        if action.startswith("search"):
            tool = self.tools.get("search")
            return str(tool.execute(action[7:-1]))
        return "Action completed."

    def _is_answer(self, action: str) -> bool:
        return action.startswith("finish")


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 2: Plan-and-Execute
# ═══════════════════════════════════════════════════════════════════════════════

class PlanExecuteAgent(BaseAgent):
    """
    Plan-and-Execute: Plan first, then execute step by step.
    Components: Planner → Executor → Verifier
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "plan_execute")

    async def run(self, goal: str) -> Dict[str, Any]:
        plan = await self._plan(goal)
        results = []
        for step in plan:
            result = await self._execute_step(step)
            results.append({"step": step, "result": result})
            if not await self._verify(result):
                # Replan
                plan = await self._replan(goal, step, result)
        return {"goal": goal, "plan": plan, "results": results}

    async def _plan(self, goal: str) -> List[str]:
        await asyncio.sleep(0.02)
        return [f"Analyze {goal}", f"Gather data for {goal}", f"Synthesize {goal}", f"Deliver {goal}"]

    async def _execute_step(self, step: str) -> str:
        return await self.act(step)

    async def _verify(self, result: str) -> bool:
        await asyncio.sleep(0.01)
        return "error" not in result.lower()

    async def _replan(self, goal: str, failed_step: str, error: str) -> List[str]:
        return [f"Fix {failed_step}", f"Retry {goal}"]


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 3: Multi-Agent Debate
# ═══════════════════════════════════════════════════════════════════════════════

class DebateAgent(BaseAgent):
    """Agent yang berpartisipasi dalam debate."""

    def __init__(self, name: str, stance: str) -> None:
        super().__init__(name, "debater")
        self.stance = stance

    async def debate(self, topic: str, rounds: int = 3) -> List[Dict[str, str]]:
        arguments = []
        for r in range(rounds):
            arg = await self._generate_argument(topic, r)
            arguments.append({"round": r, "agent": self.name, "stance": self.stance, "argument": arg})
        return arguments

    async def _generate_argument(self, topic: str, round_num: int) -> str:
        await asyncio.sleep(0.01)
        return f"{self.stance.upper()}: Argument {round_num + 1} about {topic[:30]}"


class MultiAgentDebate:
    """Orchestrator untuk multi-agent debate."""

    def __init__(self, agents: List[DebateAgent]) -> None:
        self.agents = agents

    async def run(self, topic: str, rounds: int = 3) -> Dict[str, Any]:
        all_arguments = []
        for r in range(rounds):
            round_args = []
            for agent in self.agents:
                args = await agent.debate(topic, 1)
                round_args.extend(args)
            all_arguments.extend(round_args)

        # Consensus (simplified voting)
        votes = self._vote(all_arguments)
        return {"topic": topic, "arguments": all_arguments, "consensus": votes}

    def _vote(self, arguments: List[Dict[str, str]]) -> str:
        stances = [a["stance"] for a in arguments]
        from collections import Counter
        counts = Counter(stances)
        return counts.most_common(1)[0][0] if counts else "undecided"


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 4: Tool Use / Function Calling
# ═══════════════════════════════════════════════════════════════════════════════

class ToolUseAgent(BaseAgent):
    """
    Tool Use: Agent dengan function calling capability.
    Detects tool need, generates parameters, executes, interprets result.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "tool_user")
        self.tool_schemas: Dict[str, Dict[str, Any]] = {}

    def register_tool_with_schema(self, name: str, schema: Dict[str, Any], func: Callable[..., Any]) -> None:
        self.tools.register(BaseTool(name, func))
        self.tool_schemas[name] = schema

    async def run(self, query: str) -> Dict[str, Any]:
        tool_calls = self._detect_tools(query)
        results = []
        for tool_name, params in tool_calls:
            tool = self.tools.get(tool_name)
            result = tool.execute(**params)
            results.append({"tool": tool_name, "params": params, "result": result})
        return {"query": query, "tool_calls": results}

    def _detect_tools(self, query: str) -> List[Tuple[str, Dict[str, Any]]]:
        detected = []
        for tool_name in self.tools.list_tools():
            if tool_name.lower() in query.lower():
                detected.append((tool_name, {"query": query}))
        return detected


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 5: RAG — Retrieval-Augmented Generation
# ═══════════════════════════════════════════════════════════════════════════════

class SimpleVectorStore:
    """Mock vector store dengan cosine similarity."""

    def __init__(self) -> None:
        self.documents: Dict[str, List[float]] = {}
        self.texts: Dict[str, str] = {}

    def add(self, doc_id: str, text: str, embedding: List[float]) -> None:
        self.documents[doc_id] = embedding
        self.texts[doc_id] = text

    def search(self, query_embedding: List[float], k: int = 3) -> List[Tuple[str, float]]:
        scores = []
        for doc_id, emb in self.documents.items():
            score = self._cosine_sim(query_embedding, emb)
            scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]

    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

    def __repr__(self) -> str:
        return f"SimpleVectorStore(docs={len(self.documents)})"


class RAGAgent(BaseAgent):
    """
    RAG: Retrieval-Augmented Generation.
    Retrieve relevant docs → augment prompt → generate answer.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "rag")
        self.vector_store = SimpleVectorStore()
        self.embedding_dim = 10

    def add_document(self, doc_id: str, text: str) -> None:
        emb = self._mock_embed(text)
        self.vector_store.add(doc_id, text, emb)

    def _mock_embed(self, text: str) -> List[float]:
        random.seed(hash(text) % 10000)
        return [random.uniform(-1, 1) for _ in range(self.embedding_dim)]

    async def answer(self, query: str) -> Dict[str, Any]:
        query_emb = self._mock_embed(query)
        retrieved = self.vector_store.search(query_emb, k=3)
        context = "\n".join([self.vector_store.texts[doc_id] for doc_id, _ in retrieved])
        answer = await self._generate(query, context)
        return {"query": query, "retrieved": retrieved, "context": context[:200], "answer": answer}

    async def _generate(self, query: str, context: str) -> str:
        await asyncio.sleep(0.02)
        return f"Based on {len(context)} chars of context: Answer to '{query[:40]}'"


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 6: Reflexion — Self-Reflection
# ═══════════════════════════════════════════════════════════════════════════════

class ReflexionAgent(BaseAgent):
    """
    Reflexion: Self-Reflective Agents (Shinn et al., 2023)
    After failure: reflect → update memory → retry with lesson learned.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "reflexion")
        self.reflections: List[str] = []
        self.success_history: List[bool] = []

    async def run(self, task: str, max_retries: int = 3) -> Dict[str, Any]:
        for attempt in range(max_retries):
            result = await self._attempt(task)
            success = self._evaluate(result)
            self.success_history.append(success)

            if success:
                return {"task": task, "result": result, "attempts": attempt + 1, "success": True}

            reflection = await self._reflect(task, result)
            self.reflections.append(reflection)
            self.memory.add(f"Reflection: {reflection}", importance=8.0)

        return {"task": task, "result": result, "attempts": max_retries, "success": False, "reflections": self.reflections}

    async def _attempt(self, task: str) -> str:
        return await self.act(task)

    def _evaluate(self, result: str) -> bool:
        return "error" not in result.lower() and "fail" not in result.lower()

    async def _reflect(self, task: str, result: str) -> str:
        await asyncio.sleep(0.01)
        return f"Failed on '{task[:30]}' because result contained issues. Next time, validate output before returning."


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 7: Voyager — Skill Library + Curriculum Learning
# ═══════════════════════════════════════════════════════════════════════════════

class SkillLibrary:
    """Library of learned skills (Voyager-style)."""

    def __init__(self) -> None:
        self.skills: Dict[str, Dict[str, Any]] = {}

    def add_skill(self, name: str, code: str, description: str) -> None:
        self.skills[name] = {"code": code, "description": description, "used": 0}

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        skill = self.skills.get(name)
        if skill:
            skill["used"] += 1
        return skill

    def search(self, query: str) -> List[str]:
        return [name for name, skill in self.skills.items() if query.lower() in skill["description"].lower()]

    def __repr__(self) -> str:
        return f"SkillLibrary({len(self.skills)} skills)"


class VoyagerAgent(BaseAgent):
    """
    Voyager: An Open-Ended Embodied Agent with Large Language Models (Wang et al., 2023)
    Automatic curriculum + skill library + iterative prompting.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "voyager")
        self.skill_library = SkillLibrary()
        self.curriculum_level = 0

    async def explore(self, environment_state: str) -> Dict[str, Any]:
        # Curriculum proposes next task
        task = self._propose_task(environment_state)
        # Attempt task
        result = await self._attempt_task(task)
        # If success, add to skill library
        if result["success"]:
            self.skill_library.add_skill(
                f"skill_{len(self.skill_library.skills)}",
                result["code"],
                task,
            )
            self.curriculum_level += 1
        return {"task": task, "result": result, "level": self.curriculum_level}

    def _propose_task(self, state: str) -> str:
        return f"Level {self.curriculum_level} task based on: {state[:40]}"

    async def _attempt_task(self, task: str) -> Dict[str, Any]:
        await asyncio.sleep(0.02)
        return {"success": random.random() > 0.3, "code": f"# Code for {task[:20]}", "output": "done"}


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 8: Generative Agents (Park et al.)
# ═══════════════════════════════════════════════════════════════════════════════

class GenerativeAgent(BaseAgent):
    """
    Generative Agents: Interactive Simulacra of Human Behavior (Park et al., 2023)
    Memory stream → Reflection → Planning → Action
    """

    def __init__(self, name: str, persona: str) -> None:
        super().__init__(name, "generative")
        self.persona = persona
        self.daily_plan: List[str] = []
        self.current_plan_idx = 0

    async def perceive(self, observation: str) -> None:
        self.memory.add(observation, importance=5.0)

    async def reflect(self) -> str:
        return self.memory.reflect()

    async def plan(self) -> List[str]:
        await asyncio.sleep(0.02)
        self.daily_plan = [
            f"Wake up and reflect on goals",
            f"Work on priority task",
            f"Interact with other agents",
            f"Review and plan tomorrow",
        ]
        return self.daily_plan

    async def execute_plan_step(self) -> str:
        if self.current_plan_idx < len(self.daily_plan):
            step = self.daily_plan[self.current_plan_idx]
            self.current_plan_idx += 1
            return await self.act(step)
        return "Plan complete."

    async def run_day(self) -> Dict[str, Any]:
        plan = await self.plan()
        actions = []
        for _ in plan:
            action = await self.execute_plan_step()
            actions.append(action)
        reflection = await self.reflect()
        return {"plan": plan, "actions": actions, "reflection": reflection}


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 9: AutoGPT — Goal-Oriented Autonomous Loop
# ═══════════════════════════════════════════════════════════════════════════════

class AutoGPTAgent(BaseAgent):
    """
    AutoGPT: Autonomous GPT-4 agent with goal decomposition.
    Continuous loop: think → act → observe → evaluate → repeat.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "autogpt")
        self.goals: List[str] = []
        self.subtasks: List[BaseTask] = []

    def set_goal(self, goal: str) -> None:
        self.goals.append(goal)

    async def run(self, max_iterations: int = 10) -> Dict[str, Any]:
        for i in range(max_iterations):
            # Think about current state
            thought = await self.think(f"Goal: {self.goals[0] if self.goals else 'none'}")

            # Generate subtasks if needed
            if not self.subtasks:
                self.subtasks = self._decompose_goal(self.goals[0])

            # Execute next subtask
            if self.subtasks:
                task = self.subtasks[0]
                result = await self.act(task.description)
                task.result = result
                task.status = "done"
                self.subtasks.pop(0)
                self.task_history.append(task)

            if not self.subtasks:
                return {"goal": self.goals[0], "completed": True, "iterations": i + 1}

        return {"goal": self.goals[0], "completed": False, "iterations": max_iterations}

    def _decompose_goal(self, goal: str) -> List[BaseTask]:
        return [
            BaseTask(description=f"Research {goal}"),
            BaseTask(description=f"Analyze {goal}"),
            BaseTask(description=f"Execute {goal}"),
            BaseTask(description=f"Verify {goal}"),
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 10: BabyAGI — Task Creation + Prioritization
# ═══════════════════════════════════════════════════════════════════════════════

class BabyAGIAgent(BaseAgent):
    """
    BabyAGI: Task-driven autonomous agent.
    Loop: (1) Complete task → (2) Generate new tasks → (3) Prioritize → repeat.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "babyagi")
        self.task_list: List[BaseTask] = []
        self.objective: str = ""

    def set_objective(self, objective: str) -> None:
        self.objective = objective
        self.task_list = [BaseTask(description=f"Initial research on {objective}", priority=1)]

    async def run(self, max_iterations: int = 5) -> Dict[str, Any]:
        completed = []
        for i in range(max_iterations):
            if not self.task_list:
                break

            # Pop highest priority task
            self.task_list.sort(key=lambda t: t.priority)
            current = self.task_list.pop(0)

            # Execute
            result = await self.act(current.description)
            current.result = result
            current.status = "completed"
            completed.append(current)

            # Generate new tasks based on result
            new_tasks = self._generate_tasks(current, result)
            self.task_list.extend(new_tasks)

        return {"objective": self.objective, "completed": len(completed), "pending": len(self.task_list)}

    def _generate_tasks(self, completed_task: BaseTask, result: str) -> List[BaseTask]:
        return [
            BaseTask(description=f"Follow-up on {completed_task.description}", priority=completed_task.priority + 1),
            BaseTask(description=f"Validate result of {completed_task.description}", priority=completed_task.priority + 2),
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 11: CrewAI — Role-Based Multi-Agent Crew
# ═══════════════════════════════════════════════════════════════════════════════

class CrewAIAgent(BaseAgent):
    """Agent dengan role untuk CrewAI-style collaboration."""

    def __init__(self, name: str, role: str, goal: str, backstory: str = "") -> None:
        super().__init__(name, f"crew_{role}")
        self.role = role
        self.goal = goal
        self.backstory = backstory

    async def perform_task(self, task: BaseTask) -> str:
        return await self.act(f"As {self.role}: {task.description}")


class Crew:
    """CrewAI-style crew dengan manager dan workers."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.agents: List[CrewAIAgent] = []
        self.tasks: List[BaseTask] = []

    def add_agent(self, agent: CrewAIAgent) -> None:
        self.agents.append(agent)

    def add_task(self, task: BaseTask) -> None:
        self.tasks.append(task)

    async def run(self, process: str = "sequential") -> Dict[str, Any]:
        results = []
        if process == "sequential":
            for task in self.tasks:
                agent = self._assign_agent(task)
                result = await agent.perform_task(task)
                results.append({"task": task.id, "agent": agent.name, "result": result})
        elif process == "parallel":
            for task in self.tasks:
                agent = self._assign_agent(task)
                result = await agent.perform_task(task)
                results.append({"task": task.id, "agent": agent.name, "result": result})
        return {"crew": self.name, "process": process, "results": results}

    def _assign_agent(self, task: BaseTask) -> CrewAIAgent:
        return self.agents[len(self.agents) % len(self.agents)] if self.agents else CrewAIAgent("default", "worker", "")


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 12: AutoGen — Conversational Programming
# ═══════════════════════════════════════════════════════════════════════════════

class AutoGenAgent(BaseAgent):
    """
    AutoGen: Multi-agent conversation framework.
    Agents chat dengan each other untuk solve problems.
    """

    def __init__(self, name: str, system_message: str = "") -> None:
        super().__init__(name, "autogen")
        self.system_message = system_message
        self.chat_history: List[Dict[str, str]] = []

    async def send_message(self, recipient: AutoGenAgent, message: str) -> str:
        self.chat_history.append({"to": recipient.name, "content": message})
        response = await recipient.receive_message(self.name, message)
        return response

    async def receive_message(self, sender: str, message: str) -> str:
        self.chat_history.append({"from": sender, "content": message})
        await asyncio.sleep(0.01)
        return f"[{self.name}] Response to: {message[:40]}"

    async def group_chat(self, participants: List[AutoGenAgent], topic: str, rounds: int = 3) -> List[Dict[str, str]]:
        messages = []
        for r in range(rounds):
            for agent in participants:
                msg = await agent._generate_group_message(topic, r)
                messages.append({"round": r, "agent": agent.name, "message": msg})
        return messages

    async def _generate_group_message(self, topic: str, round_num: int) -> str:
        return f"[{self.name}] Round {round_num}: My take on {topic[:30]}"


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 13: LangGraph — State Machine Graph
# ═══════════════════════════════════════════════════════════════════════════════

class GraphState:
    """State dalam LangGraph workflow."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data = data
        self.history: List[str] = []

    def update(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.history.append(f"Updated {key}")


class LangGraphNode:
    """Node dalam graph."""

    def __init__(self, name: str, func: Callable[[GraphState], GraphState]) -> None:
        self.name = name
        self.func = func
        self.edges: List[str] = []

    def add_edge(self, target: str) -> None:
        self.edges.append(target)

    def execute(self, state: GraphState) -> GraphState:
        return self.func(state)


class LangGraph:
    """State machine graph untuk agent workflows."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.nodes: Dict[str, LangGraphNode] = {}
        self.entry_point: str = ""

    def add_node(self, node: LangGraphNode) -> None:
        self.nodes[node.name] = node

    def set_entry_point(self, name: str) -> None:
        self.entry_point = name

    def add_edge(self, from_node: str, to_node: str) -> None:
        if from_node in self.nodes:
            self.nodes[from_node].add_edge(to_node)

    def run(self, initial_state: GraphState) -> GraphState:
        current = self.entry_point
        state = initial_state
        visited = set()

        while current and current not in visited:
            visited.add(current)
            node = self.nodes.get(current)
            if not node:
                break
            state = node.execute(state)
            # Follow first edge (deterministic)
            current = node.edges[0] if node.edges else None

        return state


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 14: Agno — Lightweight Agent
# ═══════════════════════════════════════════════════════════════════════════════

class AgnoAgent(BaseAgent):
    """
    Agno: Lightweight, fast agent framework.
    Minimal overhead, direct tool calling.
    """

    def __init__(self, name: str, model: str = "mock") -> None:
        super().__init__(name, "agno")
        self.model = model
        self.knowledge_base: List[str] = []

    def add_knowledge(self, text: str) -> None:
        self.knowledge_base.append(text)

    async def run(self, query: str) -> str:
        # Search knowledge base
        relevant = [k for k in self.knowledge_base if any(w in k.lower() for w in query.lower().split())]
        context = "\n".join(relevant[:3])
        await asyncio.sleep(0.01)
        return f"[Agno/{self.model}] Using {len(relevant)} knowledge items: {query[:40]}"


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 15: MetaGPT — Multi-Agent Software Dev
# ═══════════════════════════════════════════════════════════════════════════════

class MetaGPTAgent(BaseAgent):
    """
    MetaGPT: Multi-agent software development.
    Roles: Product Manager, Architect, Project Manager, Engineer, QA.
    """

    def __init__(self, name: str, role: str) -> None:
        super().__init__(name, f"metagpt_{role}")
        self.dev_role = role

    async def develop(self, requirement: str) -> Dict[str, Any]:
        if self.dev_role == "pm":
            return {"prd": f"PRD for {requirement}"}
        elif self.dev_role == "architect":
            return {"design": f"System design for {requirement}"}
        elif self.dev_role == "engineer":
            return {"code": f"Code for {requirement}"}
        elif self.dev_role == "qa":
            return {"tests": f"Tests for {requirement}"}
        return {"output": f"{self.dev_role} work on {requirement}"}


class MetaGPTTeam:
    """Team of MetaGPT agents."""

    def __init__(self) -> None:
        self.roles = ["pm", "architect", "engineer", "qa"]
        self.agents = {role: MetaGPTAgent(f"meta_{role}", role) for role in self.roles}

    async def develop_project(self, requirement: str) -> Dict[str, Any]:
        results = {}
        for role, agent in self.agents.items():
            results[role] = await agent.develop(requirement)
        return {"requirement": requirement, "artifacts": results}


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 16: CAMEL — Communicative Agents
# ═══════════════════════════════════════════════════════════════════════════════

class CAMELAgent(BaseAgent):
    """
    CAMEL: Communicative Agents for "Mind" Exploration of Large Language Models.
    Role-playing conversation antara AI assistant dan AI user.
    """

    def __init__(self, name: str, role: str, task_prompt: str) -> None:
        super().__init__(name, f"camel_{role}")
        self.camel_role = role
        self.task_prompt = task_prompt

    async def chat_turn(self, other_agent: CAMELAgent, message: str) -> str:
        response = f"[{self.camel_role}] Regarding '{message[:30]}': {self.task_prompt[:40]}"
        self.memory.add(response, importance=6.0)
        return response

    async def role_play_session(self, other: CAMELAgent, turns: int = 5) -> List[Dict[str, str]]:
        conversation = []
        msg = f"Start task: {self.task_prompt}"
        for i in range(turns):
            response = await self.chat_turn(other, msg)
            conversation.append({"turn": i, "from": self.name, "msg": response})
            # Swap roles
            msg = await other.chat_turn(self, response)
            conversation.append({"turn": i, "from": other.name, "msg": msg})
        return conversation


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 17: AgentVerse — Multi-Agent Coordination
# ═══════════════════════════════════════════════════════════════════════════════

class AgentVerse:
    """
    AgentVerse: Facilitating Multi-Agent Collaboration.
    Environment dengan multiple agents yang berinteraksi.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.agents: List[BaseAgent] = []
        self.environment_state: Dict[str, Any] = {}

    def add_agent(self, agent: BaseAgent) -> None:
        self.agents.append(agent)

    async def step(self) -> Dict[str, Any]:
        actions = []
        for agent in self.agents:
            action = await agent.act(f"Observe {self.environment_state}")
            actions.append({"agent": agent.name, "action": action})
        return {"step": len(actions), "actions": actions}

    async def run(self, steps: int = 10) -> List[Dict[str, Any]]:
        history = []
        for _ in range(steps):
            result = await self.step()
            history.append(result)
        return history


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 18: DSPy — Programmatic LLM Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

class DSPyModule:
    """
    DSPy: Programming with Foundation Models.
    Declarative modules dengan compile-time optimization.
    """

    def __init__(self, name: str, signature: str) -> None:
        self.name = name
        self.signature = signature
        self.demos: List[Dict[str, Any]] = []

    def add_demo(self, input_data: str, output_data: str) -> None:
        self.demos.append({"input": input_data, "output": output_data})

    async def forward(self, input_data: str) -> str:
        # Mock: retrieve similar demo
        if self.demos:
            best = self.demos[0]
            return f"[DSPy/{self.name}] Based on demo: {best['output'][:50]}"
        return f"[DSPy/{self.name}] Processed: {input_data[:40]}"

    def compile(self, metric: str = "accuracy") -> None:
        # Mock compilation
        pass


class DSPyPipeline:
    """Pipeline of DSPy modules."""

    def __init__(self) -> None:
        self.modules: List[DSPyModule] = []

    def add_module(self, module: DSPyModule) -> None:
        self.modules.append(module)

    async def run(self, input_data: str) -> str:
        result = input_data
        for module in self.modules:
            result = await module.forward(result)
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 19: Chain-of-Thought (CoT)
# ═══════════════════════════════════════════════════════════════════════════════

class CoTAgent(BaseAgent):
    """
    Chain-of-Thought: Prompting untuk step-by-step reasoning.
    Wei et al., 2022
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "cot")

    async def solve(self, problem: str) -> Dict[str, Any]:
        steps = self._decompose(problem)
        reasoning = []
        for step in steps:
            thought = await self.think(step)
            reasoning.append(thought)
        answer = f"Answer derived from {len(reasoning)} reasoning steps."
        return {"problem": problem, "reasoning": reasoning, "answer": answer}

    def _decompose(self, problem: str) -> List[str]:
        return [
            f"Understand: {problem[:30]}",
            "Identify relevant information",
            "Apply logical steps",
            "Verify conclusion",
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 20: Tree of Thoughts (ToT)
# ═══════════════════════════════════════════════════════════════════════════════

class ThoughtNode:
    """Node dalam Tree of Thoughts."""

    def __init__(self, content: str, parent: Optional[ThoughtNode] = None) -> None:
        self.content = content
        self.parent = parent
        self.children: List[ThoughtNode] = []
        self.score = 0.0

    def add_child(self, child: ThoughtNode) -> None:
        self.children.append(child)


class ToTAgent(BaseAgent):
    """
    Tree of Thoughts: Deliberate problem solving with search.
    Yao et al., 2023
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "tot")
        self.root: Optional[ThoughtNode] = None

    async def solve(self, problem: str, breadth: int = 3, depth: int = 3) -> Dict[str, Any]:
        self.root = ThoughtNode(problem)
        current_level = [self.root]

        for d in range(depth):
            next_level = []
            for node in current_level:
                for _ in range(breadth):
                    thought = await self.think(f"Expand: {node.content[:30]}")
                    child = ThoughtNode(thought, node)
                    child.score = random.random()
                    node.add_child(child)
                    next_level.append(child)
            current_level = next_level

        # Find best path
        best = self._find_best(self.root)
        return {"problem": problem, "best_path": best, "explored_nodes": len(current_level)}

    def _find_best(self, node: ThoughtNode) -> List[str]:
        if not node.children:
            return [node.content]
        best_child = max(node.children, key=lambda c: c.score)
        return [node.content] + self._find_best(best_child)


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 21: Self-Consistency
# ═══════════════════════════════════════════════════════════════════════════════

class SelfConsistencyAgent(BaseAgent):
    """
    Self-Consistency: Sample multiple reasoning paths, vote on answer.
    Wang et al., 2022
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "self_consistency")

    async def solve(self, problem: str, samples: int = 5) -> Dict[str, Any]:
        answers = []
        for _ in range(samples):
            cot = CoTAgent(f"{self.name}_sample")
            result = await cot.solve(problem)
            answers.append(result["answer"])

        # Vote
        from collections import Counter
        votes = Counter(answers)
        best = votes.most_common(1)[0]
        return {"problem": problem, "samples": samples, "votes": dict(votes), "best_answer": best[0], "confidence": best[1] / samples}


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 22: Hierarchical Agent — Manager + Worker
# ═══════════════════════════════════════════════════════════════════════════════

class WorkerAgent(BaseAgent):
    """Worker yang menerima task dari manager."""

    def __init__(self, name: str, specialty: str) -> None:
        super().__init__(name, f"worker_{specialty}")
        self.specialty = specialty

    async def execute(self, task: BaseTask) -> str:
        return await self.act(f"[{self.specialty}] {task.description}")


class ManagerAgent(BaseAgent):
    """Manager yang delegate tasks ke workers."""

    def __init__(self, name: str) -> None:
        super().__init__(name, "manager")
        self.workers: List[WorkerAgent] = []

    def add_worker(self, worker: WorkerAgent) -> None:
        self.workers.append(worker)

    async def delegate(self, tasks: List[BaseTask]) -> Dict[str, Any]:
        results = []
        for i, task in enumerate(tasks):
            worker = self.workers[i % len(self.workers)]
            result = await worker.execute(task)
            results.append({"task": task.id, "worker": worker.name, "result": result})
        return {"manager": self.name, "delegated": len(results), "results": results}


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 23: Adaptive Agent — Learning dari Environment
# ═══════════════════════════════════════════════════════════════════════════════

class AdaptiveAgent(BaseAgent):
    """
    Adaptive Agent: Belajar dari environment feedback.
    Update strategy berdasarkan reward/signal.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "adaptive")
        self.strategy_weights: Dict[str, float] = {"explore": 0.5, "exploit": 0.5}
        self.learning_rate = 0.1

    async def act_with_feedback(self, context: str, feedback: float) -> Dict[str, Any]:
        # Update weights based on feedback
        if feedback > 0.5:
            self.strategy_weights["exploit"] += self.learning_rate
        else:
            self.strategy_weights["explore"] += self.learning_rate

        # Normalize
        total = sum(self.strategy_weights.values())
        for k in self.strategy_weights:
            self.strategy_weights[k] /= total

        action = "explore" if random.random() < self.strategy_weights["explore"] else "exploit"
        result = await self.act(f"{action}: {context}")
        return {"action": action, "result": result, "weights": self.strategy_weights.copy()}


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 24: Code Generation Agent
# ═══════════════════════════════════════════════════════════════════════════════

class CodeGenAgent(BaseAgent):
    """
    Code Generation Agent: Write → Execute → Debug loop.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "codegen")
        self.code_history: List[str] = []

    async def generate_code(self, requirement: str) -> str:
        code = f"# Generated for: {requirement[:40]}\nprint('Hello World')"
        self.code_history.append(code)
        return code

    async def execute_code(self, code: str) -> Dict[str, Any]:
        # Mock execution
        output = f"Output: {len(code)} chars executed"
        error = None if "error" not in code.lower() else "Syntax error"
        return {"code": code, "output": output, "error": error}

    async def debug(self, code: str, error: str) -> str:
        fixed = code.replace("error", "fixed")
        return f"# Fixed: {error[:20]}\n{fixed}"

    async def run(self, requirement: str, max_attempts: int = 3) -> Dict[str, Any]:
        for attempt in range(max_attempts):
            code = await self.generate_code(requirement)
            result = await self.execute_code(code)
            if not result["error"]:
                return {"success": True, "code": code, "output": result["output"], "attempts": attempt + 1}
            code = await self.debug(code, result["error"])
        return {"success": False, "attempts": max_attempts}


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 25: Multi-Agent Collaboration (Group Chat)
# ═══════════════════════════════════════════════════════════════════════════════

class GroupChat:
    """Group chat untuk multi-agent collaboration."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.agents: List[BaseAgent] = []
        self.messages: List[Dict[str, str]] = []

    def add_agent(self, agent: BaseAgent) -> None:
        self.agents.append(agent)

    async def broadcast(self, sender: BaseAgent, message: str) -> None:
        self.messages.append({"from": sender.name, "content": message})
        for agent in self.agents:
            if agent.name != sender.name:
                agent.memory.add(f"Group chat: {message}", importance=4.0)

    async def run_discussion(self, topic: str, rounds: int = 3) -> List[Dict[str, str]]:
        for r in range(rounds):
            for agent in self.agents:
                msg = f"[{agent.name}] Round {r}: My view on {topic[:30]}"
                await self.broadcast(agent, msg)
        return self.messages


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 26: Nested Chat (AutoGen-style)
# ═══════════════════════════════════════════════════════════════════════════════

class NestedChat:
    """Nested conversation untuk complex task decomposition."""

    def __init__(self, parent_agent: BaseAgent) -> None:
        self.parent = parent_agent
        self.sub_chats: List[Dict[str, Any]] = []

    async def create_sub_chat(self, sub_task: str, agents: List[BaseAgent]) -> Dict[str, Any]:
        chat = GroupChat(f"sub_{sub_task[:20]}")
        for agent in agents:
            chat.add_agent(agent)
        messages = await chat.run_discussion(sub_task, rounds=2)
        self.sub_chats.append({"task": sub_task, "messages": messages})
        return {"task": sub_task, "summary": f"Completed with {len(messages)} messages"}


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 27: Agent Swarm — Decentralized Coordination
# ═══════════════════════════════════════════════════════════════════════════════

class AgentSwarm:
    """
    Agent Swarm: Decentralized multi-agent system.
    Agents coordinate tanpa central controller.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.agents: List[BaseAgent] = []
        self.shared_state: Dict[str, Any] = {}

    def add_agent(self, agent: BaseAgent) -> None:
        self.agents.append(agent)

    async def run(self, iterations: int = 5) -> Dict[str, Any]:
        for _ in range(iterations):
            for agent in self.agents:
                # Agent reads shared state, contributes, updates
                observation = f"State: {self.shared_state}"
                action = await agent.act(observation)
                self.shared_state[agent.name] = action
        return {"swarm": self.name, "final_state": self.shared_state}


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 28: Conversational Memory Agent
# ═══════════════════════════════════════════════════════════════════════════════

class ConversationalMemoryAgent(BaseAgent):
    """Agent dengan long-term conversational memory."""

    def __init__(self, name: str) -> None:
        super().__init__(name, "conversational_memory")
        self.conversations: Dict[str, List[Dict[str, str]]] = {}

    async def chat(self, user_id: str, message: str) -> str:
        # Retrieve conversation history
        history = self.conversations.get(user_id, [])
        context = "\n".join([h["content"] for h in history[-5:]])

        # Generate response
        response = f"[MemoryAgent] Considering {len(history)} past messages: {message[:40]}"

        # Store
        history.append({"role": "user", "content": message})
        history.append({"role": "agent", "content": response})
        self.conversations[user_id] = history

        return response


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 29: Research Agent — Iterative Deep Dive
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchAgent(BaseAgent):
    """
    Research Agent: Iterative search and synthesis.
    DeepKnowledge / Perplexity-style.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "research")
        self.search_results: List[Dict[str, Any]] = []

    async def research(self, query: str, depth: int = 3) -> Dict[str, Any]:
        for d in range(depth):
            results = await self._search(query)
            self.search_results.extend(results)
            # Generate follow-up questions
            query = await self._generate_followup(query, results)

        synthesis = await self._synthesize(self.search_results)
        return {"query": query, "sources": len(self.search_results), "synthesis": synthesis}

    async def _search(self, query: str) -> List[Dict[str, str]]:
        await asyncio.sleep(0.02)
        return [{"title": f"Result for {query[:20]}", "snippet": "Relevant information found."}]

    async def _generate_followup(self, query: str, results: List[Dict[str, str]]) -> str:
        return f"Follow-up: {query[:30]}?"

    async def _synthesize(self, results: List[Dict[str, Any]]) -> str:
        return f"Synthesized {len(results)} sources into comprehensive answer."


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN 30: Guardrails Agent — Safety + Validation
# ═══════════════════════════════════════════════════════════════════════════════

class GuardrailsAgent(BaseAgent):
    """
    Guardrails Agent: Safety checks dan output validation.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "guardrails")
        self.policies: List[str] = ["no_harm", "factual", "ethical"]

    async def validate(self, output: str, context: str) -> Dict[str, Any]:
        checks = {}
        for policy in self.policies:
            checks[policy] = self._check_policy(output, policy)

        passed = all(checks.values())
        return {"output": output[:100], "checks": checks, "passed": passed}

    def _check_policy(self, output: str, policy: str) -> bool:
        if policy == "no_harm":
            return "harm" not in output.lower()
        elif policy == "factual":
            return "maybe" not in output.lower()
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION LAYER: AgentOrchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class AgentOrchestrator:
    """
    Orchestrator untuk compose multiple patterns.
    MAGNATRIX integration layer.
    """

    def __init__(self) -> None:
        self.agents: Dict[str, BaseAgent] = {}
        self.patterns: Dict[str, Any] = {}

    def register_agent(self, name: str, agent: BaseAgent) -> None:
        self.agents[name] = agent

    def compose_react_rag(self, name: str) -> RAGAgent:
        """Compose ReAct + RAG untuk complex Q&A."""
        agent = RAGAgent(name)
        # Add ReAct-style reasoning
        agent.memory.add("Composed with ReAct reasoning", importance=8.0)
        return agent

    async def run_multi_pattern(
        self,
        patterns: List[str],
        input_data: str,
    ) -> Dict[str, Any]:
        """Run multiple patterns sequentially."""
        results = {}
        for pattern_name in patterns:
            if pattern_name == "react":
                agent = ReActAgent("react_runner")
                results["react"] = await agent.run(input_data)
            elif pattern_name == "rag":
                agent = RAGAgent("rag_runner")
                agent.add_document("doc1", "Sample knowledge")
                results["rag"] = await agent.answer(input_data)
            elif pattern_name == "debate":
                agents = [DebateAgent("a", "pro"), DebateAgent("b", "con")]
                debate = MultiAgentDebate(agents)
                results["debate"] = await debate.run(input_data)
            elif pattern_name == "cot":
                agent = CoTAgent("cot_runner")
                results["cot"] = await agent.solve(input_data)
            elif pattern_name == "tot":
                agent = ToTAgent("tot_runner")
                results["tot"] = await agent.solve(input_data)
        return {"input": input_data, "patterns": patterns, "results": results}

    def list_patterns(self) -> List[str]:
        return [
            "react", "plan_execute", "debate", "tool_use", "rag",
            "reflexion", "voyager", "generative", "autogpt", "babyagi",
            "crewai", "autogen", "langgraph", "agno", "metagpt",
            "camel", "agentverse", "dspy", "cot", "tot",
            "self_consistency", "hierarchical", "adaptive", "codegen",
            "group_chat", "nested_chat", "swarm", "conversational_memory",
            "research", "guardrails",
        ]

    def __repr__(self) -> str:
        return f"AgentOrchestrator(agents={len(self.agents)}, patterns={len(self.list_patterns())})"


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO / __main__
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    async def demo() -> None:
        print("=" * 70)
        print("MAGNATRIX — 500 AI Agents Architecture Patterns Demo")
        print("=" * 70)

        # 1. ReAct
        print("\n1. ReAct Agent")
        react = ReActAgent("ReAct")
        react.add_tool(BaseTool("search", lambda q: f"Results for {q}", "Search tool"))
        result = await react.run("What is the capital of France?")
        print(f"   Answer: {result['answer'][:60]}")
        print(f"   Steps: {result['steps']}")

        # 2. Plan-and-Execute
        print("\n2. Plan-and-Execute")
        plan_exec = PlanExecuteAgent("Planner")
        result = await plan_exec.run("Build a website")
        print(f"   Goal: {result['goal']}")
        print(f"   Plan steps: {len(result['results'])}")

        # 3. Multi-Agent Debate
        print("\n3. Multi-Agent Debate")
        debate = MultiAgentDebate([DebateAgent("A", "pro"), DebateAgent("B", "con")])
        result = await debate.run("AI should regulate itself", rounds=2)
        print(f"   Topic: {result['topic']}")
        print(f"   Consensus: {result['consensus']}")

        # 4. RAG
        print("\n4. RAG Agent")
        rag = RAGAgent("RAG")
        rag.add_document("doc1", "Paris is the capital of France.")
        rag.add_document("doc2", "Berlin is the capital of Germany.")
        result = await rag.answer("What is the capital of France?")
        print(f"   Retrieved: {len(result['retrieved'])} docs")
        print(f"   Answer: {result['answer'][:60]}")

        # 5. Reflexion
        print("\n5. Reflexion Agent")
        reflex = ReflexionAgent("Reflexion")
        result = await reflex.run("Solve complex equation", max_retries=2)
        print(f"   Success: {result['success']}, Attempts: {result['attempts']}")

        # 6. Voyager
        print("\n6. Voyager Agent")
        voyager = VoyagerAgent("Voyager")
        result = await voyager.explore("Minecraft forest biome")
        print(f"   Task: {result['task']}")
        print(f"   Level: {result['level']}")

        # 7. Generative Agent
        print("\n7. Generative Agent")
        gen = GenerativeAgent("Alice", "Software engineer")
        await gen.perceive("Morning standup meeting")
        await gen.perceive("Code review request")
        result = await gen.run_day()
        print(f"   Plan: {result['plan']}")
        print(f"   Actions: {len(result['actions'])}")
        print(f"   Reflection: {result['reflection'][:60]}")

        # 8. AutoGPT
        print("\n8. AutoGPT")
        autogpt = AutoGPTAgent("AutoGPT")
        autogpt.set_goal("Research quantum computing")
        result = await autogpt.run(max_iterations=5)
        print(f"   Goal: {result['goal']}")
        print(f"   Completed: {result['completed']}")

        # 9. BabyAGI
        print("\n9. BabyAGI")
        baby = BabyAGIAgent("BabyAGI")
        baby.set_objective("Learn Python async")
        result = await baby.run(max_iterations=4)
        print(f"   Objective: {result['objective']}")
        print(f"   Completed: {result['completed']}, Pending: {result['pending']}")

        # 10. CrewAI
        print("\n10. CrewAI")
        crew = Crew("DevTeam")
        crew.add_agent(CrewAIAgent("Alice", "researcher", "Find info"))
        crew.add_agent(CrewAIAgent("Bob", "writer", "Write docs"))
        crew.add_task(BaseTask(description="Research AI trends"))
        crew.add_task(BaseTask(description="Write report"))
        result = await crew.run("sequential")
        print(f"   Crew: {result['crew']}, Results: {len(result['results'])}")

        # 11. AutoGen
        print("\n11. AutoGen")
        ag1 = AutoGenAgent("Assistant", "Helpful AI")
        ag2 = AutoGenAgent("User", "Human user")
        msg = await ag1.send_message(ag2, "Help me code")
        print(f"   Message flow: {msg[:60]}")

        # 12. LangGraph
        print("\n12. LangGraph")
        graph = LangGraph("Workflow")
        def step1(state): state.update("x", 1); return state
        def step2(state): state.update("y", 2); return state
        n1 = LangGraphNode("start", step1)
        n2 = LangGraphNode("end", step2)
        graph.add_node(n1)
        graph.add_node(n2)
        graph.set_entry_point("start")
        graph.add_edge("start", "end")
        result = graph.run(GraphState({}))
        print(f"   Final state: {result.data}")

        # 13. MetaGPT
        print("\n13. MetaGPT")
        team = MetaGPTTeam()
        result = await team.develop_project("Build a chatbot")
        print(f"   Requirement: {result['requirement']}")
        print(f"   Artifacts: {list(result['artifacts'].keys())}")

        # 14. Tree of Thoughts
        print("\n14. Tree of Thoughts")
        tot = ToTAgent("ToT")
        result = await tot.solve("Optimize supply chain", breadth=2, depth=2)
        print(f"   Best path: {' -> '.join(result['best_path'][:3])}")

        # 15. Orchestrator
        print("\n15. AgentOrchestrator — Multi-Pattern")
        orch = AgentOrchestrator()
        result = await orch.run_multi_pattern(
            ["react", "rag", "cot"],
            "Explain neural networks",
        )
        print(f"   Patterns run: {result['patterns']}")
        print(f"   Results keys: {list(result['results'].keys())}")

        print("\n" + "=" * 70)
        print(f"Demo complete. Total patterns implemented: {len(orch.list_patterns())}")
        print("=" * 70)

    asyncio.run(demo())
