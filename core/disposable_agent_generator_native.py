#!/usr/bin/env python3
"""
Disposable Agent Generator for MAGNATRIX-OS
============================================
Generate disposable agents/modules from natural language prompts.
Auto-compile, deploy, execute, then destroy. Inspired by SpecterOps
"Disposable Tooling: Building LLM-Generated Mythic Agents".
Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import hashlib, importlib, os, random, re, string, sys, tempfile, threading, time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


class PromptParser:
    """Parse natural language prompts into structured agent specifications."""

    def __init__(self) -> None:
        self._action_patterns = {
            "collect": re.compile(r"collect|gather|fetch|extract|scrape", re.I),
            "send": re.compile(r"send|transmit|upload|exfil", re.I),
            "execute": re.compile(r"execute|run|launch|spawn", re.I),
            "monitor": re.compile(r"monitor|watch|track|log", re.I),
            "connect": re.compile(r"connect|callback|beacon|c2", re.I),
        }
        self._target_patterns = {
            "files": re.compile(r"file|document|data|directory|folder", re.I),
            "process": re.compile(r"process|application|program|service", re.I),
            "network": re.compile(r"network|traffic|packet|connection", re.I),
            "system": re.compile(r"system|host|machine|device", re.I),
            "registry": re.compile(r"registry|config|setting|key", re.I),
        }

    def parse(self, prompt: str) -> Dict[str, Any]:
        """Convert prompt to agent spec."""
        spec = {
            "actions": [],
            "targets": [],
            "constraints": [],
            "name": self._generate_name(),
        }
        for action, pattern in self._action_patterns.items():
            if pattern.search(prompt):
                spec["actions"].append(action)
        for target, pattern in self._target_patterns.items():
            if pattern.search(prompt):
                spec["targets"].append(target)
        if "stealth" in prompt.lower() or "silent" in prompt.lower():
            spec["constraints"].append("stealth")
        if "quick" in prompt.lower() or "fast" in prompt.lower():
            spec["constraints"].append("speed")
        if not spec["actions"]:
            spec["actions"].append("collect")
        return spec

    def _generate_name(self) -> str:
        adjectives = ["shadow", "ghost", "silent", "rapid", "frost", "ember", "void", "nebula"]
        nouns = ["wraith", "drone", "specter", "cipher", "phantom", "shade", "raven", "echo"]
        return f"{random.choice(adjectives)}_{random.choice(nouns)}_{random.randint(1000,9999)}"


class AgentTemplateEngine:
    """Generate agent source code from specifications."""

    TEMPLATES = {
        "collect_files": '''
import os, json
from pathlib import Path

def run(target_dir=".", extensions=None):
    results = []
    if extensions is None:
        extensions = [".txt", ".doc", ".pdf", ".csv"]
    for root, _, files in os.walk(target_dir):
        for f in files:
            if any(f.endswith(e) for e in extensions):
                fpath = os.path.join(root, f)
                try:
                    results.append({"path": fpath, "size": os.path.getsize(fpath)})
                except:
                    pass
    return json.dumps(results, default=str)

if __name__ == "__main__":
    print(run())
''',
        "collect_process": '''
import psutil, json, os

def run():
    processes = []
    for p in psutil.process_iter(["pid", "name", "username"]):
        try:
            processes.append(p.info)
        except:
            pass
    return json.dumps(processes, default=str)

if __name__ == "__main__":
    print(run())
''',
        "monitor_network": '''
import socket, json, time

def run(duration=5):
    connections = []
    start = time.time()
    while time.time() - start < duration:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.close()
        except:
            pass
    return json.dumps({"duration": duration, "connections": connections})

if __name__ == "__main__":
    print(run())
''',
        "execute_command": '''
import subprocess, json, sys

def run(command="whoami"):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        return json.dumps({"stdout": result.stdout, "stderr": result.stderr, "rc": result.returncode})
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    print(run())
''',
        "connect_callback": '''
import urllib.request, json, socket

def run(url="http://localhost:8080/beacon", data=None):
    if data is None:
        data = {"hostname": socket.gethostname(), "timestamp": int(__import__("time").time())}
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.dumps({"status": resp.status, "body": resp.read().decode()})
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    print(run())
''',
    }

    def generate(self, spec: Dict[str, Any]) -> str:
        """Generate source code from spec."""
        actions = spec.get("actions", ["collect"])
        targets = spec.get("targets", ["files"])
        name = spec.get("name", "agent_001")

        # Select template based on action + target
        key = f"{actions[0]}_{targets[0]}" if actions and targets else "collect_files"
        if key not in self.TEMPLATES:
            key = "collect_files"

        template = self.TEMPLATES[key]
        code = f'# Agent: {name}\n# Generated by MAGNATRIX-OS Disposable Agent Generator\n{template}'
        return code


class DisposableAgent:
    """A single-use disposable agent instance."""

    def __init__(self, agent_id: str, source_code: str, spec: Dict[str, Any]) -> None:
        self.agent_id = agent_id
        self.source_code = source_code
        self.spec = spec
        self.status = "created"
        self.result: Optional[str] = None
        self.created_at = time.time()
        self.executed_at: Optional[float] = None
        self.destroyed_at: Optional[float] = None
        self._module: Optional[Any] = None
        self._file_path: Optional[str] = None

    def compile(self) -> bool:
        """Compile agent source to temporary module."""
        try:
            # Write to temp file
            fd, path = tempfile.mkstemp(prefix=f"agent_{self.agent_id}_", suffix=".py")
            with os.fdopen(fd, "w") as f:
                f.write(self.source_code)
            self._file_path = path
            # Verify syntax
            compile(self.source_code, path, "exec")
            self.status = "compiled"
            return True
        except Exception as e:
            self.status = f"compile_error: {e}"
            return False

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the agent."""
        if self.status not in ("compiled", "created"):
            return {"error": "Agent not compiled", "status": self.status}
        try:
            # Load and execute
            namespace = {}
            exec(self.source_code, namespace)
            self._module = namespace
            # Find and call run function
            run_fn = namespace.get("run")
            if run_fn and callable(run_fn):
                self.result = str(run_fn(**kwargs))
            else:
                self.result = "No run() function found"
            self.status = "executed"
            self.executed_at = time.time()
            return {"status": "success", "result": self.result[:500], "agent_id": self.agent_id}
        except Exception as e:
            self.status = f"execute_error: {e}"
            return {"status": "error", "error": str(e), "agent_id": self.agent_id}

    def destroy(self) -> bool:
        """Destroy agent and clean up."""
        try:
            if self._file_path and os.path.exists(self._file_path):
                os.remove(self._file_path)
            self._module = None
            self.status = "destroyed"
            self.destroyed_at = time.time()
            return True
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "spec": self.spec,
            "created_at": self.created_at,
            "executed_at": self.executed_at,
            "destroyed_at": self.destroyed_at,
            "result_preview": self.result[:200] if self.result else None,
        }


class C2IntegrationLayer:
    """Integration layer for C2-style command and control."""

    def __init__(self, callback_url: str = "") -> None:
        self.callback_url = callback_url
        self.pending_tasks: List[Dict[str, Any]] = []
        self.results: List[Dict[str, Any]] = []
        self._running = False

    def register_task(self, task_id: str, agent_id: str, action: str, params: Dict[str, Any] = None) -> None:
        self.pending_tasks.append({
            "task_id": task_id,
            "agent_id": agent_id,
            "action": action,
            "params": params or {},
            "status": "pending",
        })

    def get_task(self, agent_id: str) -> Optional[Dict[str, Any]]:
        for task in self.pending_tasks:
            if task["agent_id"] == agent_id and task["status"] == "pending":
                task["status"] = "assigned"
                return task
        return None

    def submit_result(self, task_id: str, result: str) -> None:
        self.results.append({
            "task_id": task_id,
            "result": result,
            "timestamp": time.time(),
        })
        # Remove from pending
        self.pending_tasks = [t for t in self.pending_tasks if t["task_id"] != task_id]

    def beacon(self, agent_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Agent beacon: check for tasks and submit results."""
        task = self.get_task(agent_id)
        return {"task": task, "status": "ok"}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pending_tasks": len(self.pending_tasks),
            "completed_results": len(self.results),
            "callback_url": self.callback_url,
        }


class DisposableAgentGenerator:
    """Top-level disposable agent generator."""

    def __init__(self, repo_root: str = "") -> None:
        self.repo_root = repo_root
        self.parser = PromptParser()
        self.template_engine = AgentTemplateEngine()
        self.c2 = C2IntegrationLayer()
        self.agents: Dict[str, DisposableAgent] = {}
        self._agent_counter = 0

    def generate(self, prompt: str, auto_execute: bool = False, **kwargs) -> DisposableAgent:
        """Generate a disposable agent from a natural language prompt."""
        self._agent_counter += 1
        agent_id = f"disp_{self._agent_counter}_{int(time.time())}"

        # Parse prompt
        spec = self.parser.parse(prompt)
        spec["prompt"] = prompt

        # Generate code
        source = self.template_engine.generate(spec)

        # Create agent
        agent = DisposableAgent(agent_id, source, spec)
        self.agents[agent_id] = agent

        # Compile
        agent.compile()

        # Optionally execute
        if auto_execute:
            agent.execute(**kwargs)

        return agent

    def generate_and_destroy(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """One-shot: generate, execute, destroy."""
        agent = self.generate(prompt, auto_execute=True, **kwargs)
        result = agent.to_dict()
        result["execution"] = {"result": agent.result[:200] if agent.result else None}
        agent.destroy()
        return result

    def get_agent(self, agent_id: str) -> Optional[DisposableAgent]:
        return self.agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self.agents.values()]

    def cleanup(self) -> int:
        """Destroy all agents and clean up."""
        count = 0
        for agent in list(self.agents.values()):
            if agent.destroy():
                count += 1
        self.agents.clear()
        return count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_agents_generated": self._agent_counter,
            "active_agents": len(self.agents),
            "c2": self.c2.to_dict(),
        }
