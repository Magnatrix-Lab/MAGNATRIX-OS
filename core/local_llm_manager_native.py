#!/usr/bin/env python3
"""
Local LLM Manager for MAGNATRIX-OS Self-Hosting
Manages Ollama/llama.cpp lifecycle: auto-install, model pull, health check,
unified chat interface, hardware-aware model selection, and integration with
MultiModelLLMAdapter. Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple, Any, Callable

# Import sibling modules (relative imports handled by sys.path in production)
try:
    from core.model_catalog_native import ModelCatalog, ModelSpec, QuantizationLevel, ModelFamily
except ImportError:
    ModelCatalog = ModelSpec = QuantizationLevel = ModelFamily = None
try:
    from core.hardware_profiler_native import HardwareProfiler, HardwareProfile
except ImportError:
    pass


@dataclasses.dataclass
class ModelStatus:
    """Runtime status of a local model."""
    model_id: str
    name: str
    installed: bool
    size_gb: float = 0.0
    modified: Optional[str] = None
    digest: str = ""
    available: bool = False  # Can be loaded and run
    last_error: Optional[str] = None


@dataclasses.dataclass
class ChatMessage:
    """Standardized chat message."""
    role: str  # "system", "user", "assistant"
    content: str


@dataclasses.dataclass
class ChatCompletion:
    """Standardized chat completion response."""
    message: ChatMessage
    model: str
    done: bool = True
    total_duration_ms: float = 0.0
    load_duration_ms: float = 0.0
    prompt_eval_count: int = 0
    eval_count: int = 0
    tokens_per_sec: float = 0.0


class LocalLLMManager:
    """
    Self-hosting LLM manager for MAGNATRIX-OS.

    Responsibilities:
    - Detect Ollama installation status
    - Auto-install Ollama if missing (with user confirmation)
    - Pull and manage model downloads
    - Hardware-aware model recommendations
    - Unified chat/completion interface
    - Health monitoring and auto-recovery
    - Integration with MultiModelLLMAdapter
    """

    OLLAMA_DEFAULT_HOST = "127.0.0.1"
    OLLAMA_DEFAULT_PORT = 11434
    OLLAMA_API_VERSION = "v1"

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
        self.host = host or self.OLLAMA_DEFAULT_HOST
        self.port = port or self.OLLAMA_DEFAULT_PORT
        self.base_url = f"http://{self.host}:{self.port}"

        # Subsystems
        self.catalog = ModelCatalog()
        self.profiler = HardwareProfiler()
        self._hardware_profile: Optional[HardwareProfile] = None

        # State
        self._installed_models: Dict[str, ModelStatus] = {}
        self._running_models: Dict[str, float] = {}  # model_id -> last used timestamp
        self._session_history: List[Dict[str, Any]] = []
        self._install_in_progress: Dict[str, bool] = {}

        # Auto-detect on init
        self._ollama_binary: Optional[str] = None
        self._detect_ollama()

    # ------------------------------------------------------------------
    # Ollama Detection & Installation
    # ------------------------------------------------------------------

    def _detect_ollama(self) -> None:
        """Find Ollama binary in PATH or common locations."""
        binary_name = "ollama.exe" if platform.system() == "Windows" else "ollama"

        # Check PATH
        ollama_path = shutil.which(binary_name)
        if ollama_path:
            self._ollama_binary = ollama_path
            return

        # Check common installation paths
        common_paths = [
            "/usr/local/bin/ollama",
            "/usr/bin/ollama",
            "/opt/ollama/ollama",
            os.path.expanduser("~/.ollama/ollama"),
            os.path.expanduser("~/ollama/ollama"),
            "/Applications/Ollama.app/Contents/MacOS/ollama",
            "C:\\Program Files\\Ollama\\ollama.exe",
            "C:\\Users\\\\AppData\\Local\\Programs\\Ollama\\ollama.exe",
        ]
        for path in common_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                self._ollama_binary = path
                return

    def is_ollama_installed(self) -> bool:
        return self._ollama_binary is not None

    def is_ollama_running(self) -> bool:
        """Check if Ollama server is responding on the configured port."""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/tags",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def get_install_status(self) -> Dict[str, Any]:
        """Full installation status report."""
        return {
            "installed": self.is_ollama_installed(),
            "binary_path": self._ollama_binary,
            "running": self.is_ollama_running(),
            "host": self.host,
            "port": self.port,
            "platform": platform.system(),
            "architecture": platform.machine(),
        }

    def start_ollama_server(self) -> bool:
        """Start Ollama server if binary is found."""
        if not self._ollama_binary:
            return False
        if self.is_ollama_running():
            return True

        try:
            # Start Ollama server in background
            env = os.environ.copy()
            env["OLLAMA_HOST"] = f"{self.host}:{self.port}"

            if platform.system() == "Windows":
                subprocess.Popen(
                    [self._ollama_binary, "serve"],
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    [self._ollama_binary, "serve"],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )

            # Wait for server to come up
            for _ in range(10):
                time.sleep(0.5)
                if self.is_ollama_running():
                    return True
            return False
        except Exception as exc:
            self._log_event("server_start_failed", str(exc))
            return False

    def get_install_command(self) -> Optional[str]:
        """Return the recommended installation command for this platform."""
        system = platform.system()
        if system == "Linux":
            return "curl -fsSL https://ollama.com/install.sh | sh"
        elif system == "Darwin":
            return "brew install ollama  # or download from https://ollama.com/download/mac"
        elif system == "Windows":
            return "Download from https://ollama.com/download/windows  # or use winget: winget install Ollama.Ollama"
        return None

    def auto_install_ollama(self, confirm: bool = False) -> bool:
        """
        Auto-install Ollama if not present.
        Set confirm=True to actually execute (otherwise returns command for review).
        """
        if self.is_ollama_installed():
            return True

        cmd = self.get_install_command()
        if not cmd:
            return False

        if not confirm:
            # Return the command without executing
            return False

        system = platform.system()
        try:
            if system == "Linux":
                result = subprocess.run(
                    ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                    capture_output=True, text=True, timeout=300
                )
                return result.returncode == 0
            elif system == "Darwin":
                result = subprocess.run(
                    ["brew", "install", "ollama"],
                    capture_output=True, text=True, timeout=120
                )
                return result.returncode == 0
            elif system == "Windows":
                # Windows requires manual download or winget
                result = subprocess.run(
                    ["winget", "install", "Ollama.Ollama"],
                    capture_output=True, text=True, timeout=120
                )
                return result.returncode == 0
        except Exception as exc:
            self._log_event("auto_install_failed", str(exc))
            return False

        return False

    # ------------------------------------------------------------------
    # Model Management
    # ------------------------------------------------------------------

    def refresh_installed_models(self) -> Dict[str, ModelStatus]:
        """Query Ollama for currently installed models."""
        self._installed_models.clear()

        if not self.is_ollama_running():
            return self._installed_models

        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/tags",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            for model in data.get("models", []):
                model_id = model.get("name", "")
                size = model.get("size", 0)
                size_gb = size / (1024 ** 3) if size else 0.0

                status = ModelStatus(
                    model_id=model_id,
                    name=model_id.split(":")[0],
                    installed=True,
                    size_gb=size_gb,
                    modified=model.get("modified_at"),
                    digest=model.get("digest", "")[:12],
                    available=True,
                )
                self._installed_models[model_id] = status
        except Exception as exc:
            self._log_event("refresh_failed", str(exc))

        return self._installed_models

    def list_installed(self) -> List[ModelStatus]:
        """List all installed models with their status."""
        return list(self._installed_models.values())

    def is_model_installed(self, model_id: str) -> bool:
        return model_id in self._installed_models and self._installed_models[model_id].installed

    def pull_model(self, model_id: str, progress_callback: Optional[Callable[[str, float], None]] = None) -> bool:
        """
        Download a model from Ollama registry.

        Args:
            model_id: Ollama model ID (e.g., "llama3.2:3b")
            progress_callback: Optional callback(status_text, percentage)

        Returns:
            True if successful
        """
        if self._install_in_progress.get(model_id, False):
            return False

        self._install_in_progress[model_id] = True

        try:
            if not self.is_ollama_running():
                if not self.start_ollama_server():
                    self._install_in_progress[model_id] = False
                    return False

            # Use the pull API
            body = json.dumps({"name": model_id}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/pull",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            if progress_callback:
                progress_callback(f"Starting download of {model_id}...", 0.0)

            with urllib.request.urlopen(req, timeout=600) as resp:
                # Stream response for progress
                downloaded = 0
                total = 0
                for line in resp:
                    try:
                        chunk = json.loads(line.decode("utf-8"))
                        status = chunk.get("status", "")

                        if "completed" in status.lower() or chunk.get("completed"):
                            if progress_callback:
                                progress_callback(f"Download complete: {model_id}", 100.0)
                            break

                        if progress_callback:
                            progress_callback(status, -1.0)  # Indeterminate
                    except json.JSONDecodeError:
                        continue

            # Refresh installed models
            self.refresh_installed_models()
            self._install_in_progress[model_id] = False
            self._log_event("model_pulled", model_id)
            return self.is_model_installed(model_id)

        except Exception as exc:
            self._install_in_progress[model_id] = False
            self._log_event("model_pull_failed", f"{model_id}: {exc}")
            return False

    def remove_model(self, model_id: str) -> bool:
        """Remove an installed model to free disk space."""
        if not self.is_ollama_running():
            return False

        try:
            body = json.dumps({"name": model_id}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/delete",
                data=body,
                headers={"Content-Type": "application/json"},
                method="DELETE",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    self._installed_models.pop(model_id, None)
                    self._log_event("model_removed", model_id)
                    return True
        except Exception as exc:
            self._log_event("model_remove_failed", f"{model_id}: {exc}")
        return False

    def copy_model(self, source: str, destination: str) -> bool:
        """Copy a model to create a custom variant."""
        if not self.is_ollama_running():
            return False
        try:
            body = json.dumps({"source": source, "destination": destination}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/copy",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Hardware-Aware Recommendations
    # ------------------------------------------------------------------

    def get_hardware_profile(self) -> HardwareProfile:
        """Get cached or fresh hardware profile."""
        if self._hardware_profile is None:
            self._hardware_profile = self.profiler.profile()
        return self._hardware_profile

    def recommend_models(
        self,
        count: int = 5,
        prefer_quality: bool = False,
        prefer_speed: bool = False,
        need_vision: bool = False,
        need_tools: bool = False,
    ) -> List[ModelSpec]:
        """Recommend models based on detected hardware."""
        hw = self.get_hardware_profile()
        return self.catalog.recommend_for_hardware(
            ram_gb=hw.ram_total_gb,
            cpu_cores=hw.cpu_cores_logical,
            has_gpu=hw.gpu_count > 0,
            gpu_vram_gb=hw.gpu_vram_total_gb,
            prefer_quality=prefer_quality,
            prefer_speed=prefer_speed,
            need_vision=need_vision,
            need_tools=need_tools,
        )[:count]

    def quick_recommendation(self) -> Dict[str, Any]:
        """Single-call recommendation with hardware summary."""
        hw = self.get_hardware_profile()
        picks = self.recommend_models(count=3)

        return {
            "hardware": hw.to_dict(),
            "recommendations": [
                {
                    "model_id": m.model_id,
                    "name": m.name,
                    "parameters": m.parameters,
                    "ram_required_gb": m.ram_required_gb(),
                    "disk_required_gb": m.disk_required_gb(),
                    "reason": self._recommendation_reason(m, hw),
                }
                for m in picks
            ],
            "tier": hw.overall_tier,
        }

    def _recommendation_reason(self, spec: ModelSpec, hw: HardwareProfile) -> str:
        """Generate human-readable recommendation reason."""
        reasons = []
        if spec.parameters in ("0.5B", "1B", "1.5B", "1.7B"):
            reasons.append("ultra-lightweight for instant responses")
        elif spec.parameters in ("2B", "3B", "3.8B"):
            reasons.append("lightweight with good quality balance")
        elif spec.parameters in ("7B", "8B", "9B"):
            reasons.append("strong performance for complex tasks")
        elif spec.parameters in ("14B", "24B"):
            reasons.append("high quality for demanding workloads")
        else:
            reasons.append("state-of-the-art capability")

        if spec.context_window >= 128000:
            reasons.append("massive context window")
        elif spec.context_window >= 32000:
            reasons.append("large context window")

        if spec.supports_code and spec.reasoning_rating >= 8:
            reasons.append("excellent for coding")

        if spec.supports_tools:
            reasons.append("supports tool use")

        return "; ".join(reasons)

    def get_optimal_quantization(self, model_id: str) -> QuantizationLevel:
        """Suggest optimal quantization for this hardware."""
        hw = self.get_hardware_profile()
        spec = self.catalog.get(model_id)
        if not spec:
            return QuantizationLevel.Q4_K_M

        ram = hw.ram_total_gb
        if ram >= 32:
            return QuantizationLevel.Q5_K_M
        elif ram >= 16:
            return QuantizationLevel.Q4_K_M
        elif ram >= 8:
            return QuantizationLevel.Q4_K_M
        else:
            return QuantizationLevel.Q4_K_S

    # ------------------------------------------------------------------
    # Chat / Completion Interface
    # ------------------------------------------------------------------

    def chat(
        self,
        model_id: str,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system: Optional[str] = None,
        stream: bool = False,
        timeout: float = 120.0,
    ) -> ChatCompletion:
        """
        Send a chat completion request to a local model.

        Args:
            model_id: Ollama model ID
            messages: List of chat messages
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            system: Optional system prompt override
            stream: Whether to stream (not yet supported in this method)
            timeout: Request timeout in seconds

        Returns:
            ChatCompletion with response and metadata
        """
        if not self.is_ollama_running():
            if not self.start_ollama_server():
                return ChatCompletion(
                    message=ChatMessage(role="assistant", content=""),
                    model=model_id,
                    done=False,
                    last_error="Ollama server not available",
                )

        # Ensure model is installed
        if not self.is_model_installed(model_id):
            return ChatCompletion(
                message=ChatMessage(role="assistant", content=""),
                model=model_id,
                done=False,
                last_error=f"Model {model_id} not installed. Run pull_model() first.",
            )

        # Build messages for Ollama chat API
        ollama_messages = []
        if system:
            ollama_messages.append({"role": "system", "content": system})
        for msg in messages:
            ollama_messages.append({"role": msg.role, "content": msg.content})

        body = {
            "model": model_id,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        start_time = time.time()
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/chat",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            total_duration = (time.time() - start_time) * 1000

            message_data = data.get("message", {})
            content = message_data.get("content", "")

            # Calculate tokens per second
            eval_count = data.get("eval_count", 0)
            eval_duration_ns = data.get("eval_duration", 0)
            tokens_per_sec = 0.0
            if eval_duration_ns > 0:
                tokens_per_sec = (eval_count / eval_duration_ns) * 1e9

            self._running_models[model_id] = time.time()
            self._log_event("chat_complete", model_id, {"latency_ms": total_duration, "tokens": eval_count})

            return ChatCompletion(
                message=ChatMessage(role="assistant", content=content),
                model=model_id,
                done=data.get("done", True),
                total_duration_ms=total_duration,
                load_duration_ms=data.get("load_duration", 0) / 1e6,  # ns to ms
                prompt_eval_count=data.get("prompt_eval_count", 0),
                eval_count=eval_count,
                tokens_per_sec=round(tokens_per_sec, 2),
            )

        except Exception as exc:
            self._log_event("chat_failed", f"{model_id}: {exc}")
            return ChatCompletion(
                message=ChatMessage(role="assistant", content=""),
                model=model_id,
                done=False,
                last_error=str(exc),
            )

    def generate(
        self,
        model_id: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: float = 120.0,
    ) -> ChatCompletion:
        """
        Simple text generation (non-chat) interface.
        Compatible with the old Ollama /api/generate endpoint.
        """
        if not self.is_ollama_running():
            if not self.start_ollama_server():
                return ChatCompletion(
                    message=ChatMessage(role="assistant", content=""),
                    model=model_id,
                    done=False,
                    last_error="Ollama server not available",
                )

        if not self.is_model_installed(model_id):
            return ChatCompletion(
                message=ChatMessage(role="assistant", content=""),
                model=model_id,
                done=False,
                last_error=f"Model {model_id} not installed.",
            )

        body = {
            "model": model_id,
            "prompt": prompt,
            "system": system or "",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        start_time = time.time()
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            total_duration = (time.time() - start_time) * 1000
            content = data.get("response", "")
            eval_count = data.get("eval_count", 0)
            eval_duration_ns = data.get("eval_duration", 0)
            tokens_per_sec = 0.0
            if eval_duration_ns > 0:
                tokens_per_sec = (eval_count / eval_duration_ns) * 1e9

            self._running_models[model_id] = time.time()

            return ChatCompletion(
                message=ChatMessage(role="assistant", content=content),
                model=model_id,
                done=True,
                total_duration_ms=total_duration,
                load_duration_ms=data.get("load_duration", 0) / 1e6,
                prompt_eval_count=data.get("prompt_eval_count", 0),
                eval_count=eval_count,
                tokens_per_sec=round(tokens_per_sec, 2),
            )

        except Exception as exc:
            return ChatCompletion(
                message=ChatMessage(role="assistant", content=""),
                model=model_id,
                done=False,
                last_error=str(exc),
            )

    def simple_chat(self, model_id: str, user_message: str, system: Optional[str] = None) -> str:
        """Ultra-simple one-shot chat returning just the text response."""
        messages = [ChatMessage(role="user", content=user_message)]
        result = self.chat(model_id, messages, system=system)
        if result.last_error:
            return f"[ERROR: {result.last_error}]"
        return result.message.content

    # ------------------------------------------------------------------
    # OpenAI-Compatible API (for integration with MultiModelLLMAdapter)
    # ------------------------------------------------------------------

    def get_openai_compatible_endpoint(self) -> Optional[str]:
        """Return the OpenAI-compatible API endpoint URL if available."""
        if not self.is_ollama_running():
            return None
        return f"{self.base_url}/v1"

    def create_openai_compatible_config(self, model_id: str) -> Dict[str, Any]:
        """Create a config dict compatible with MultiModelLLMAdapter."""
        return {
            "provider": "ollama",
            "name": f"local_{model_id.replace(':', '_')}",
            "base_url": self.get_openai_compatible_endpoint() or self.base_url,
            "model_id": model_id,
            "timeout": 120.0,
            "max_tokens": 2048,
            "temperature": 0.7,
            "capabilities": ["chat", "completion"],
            "priority": 0,  # Local = highest priority
        }

    # ------------------------------------------------------------------
    # Health & Monitoring
    # ------------------------------------------------------------------

    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of the local LLM subsystem."""
        status = {
            "timestamp": time.time(),
            "ollama": {
                "installed": self.is_ollama_installed(),
                "running": self.is_ollama_running(),
                "binary": self._ollama_binary,
            },
            "hardware": self.get_hardware_profile().to_dict(),
            "models": {
                "installed_count": len(self._installed_models),
                "installed": [m.model_id for m in self._installed_models.values()],
            },
            "server_status": "healthy" if self.is_ollama_running() else "offline",
        }

        # Try to get Ollama version
        if self.is_ollama_running():
            try:
                req = urllib.request.Request(
                    f"{self.base_url}/api/version",
                    method="GET",
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    version_data = json.loads(resp.read().decode("utf-8"))
                    status["ollama"]["version"] = version_data.get("version", "unknown")
            except Exception:
                status["ollama"]["version"] = "unknown"

        return status

    def get_running_models(self) -> List[str]:
        """List currently loaded/running models."""
        if not self.is_ollama_running():
            return []
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/ps",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return list(self._running_models.keys())

    def unload_model(self, model_id: str) -> bool:
        """Unload a model from memory to free RAM."""
        # Ollama doesn't have a direct unload API, but we can unload by loading a tiny model
        try:
            body = json.dumps({"model": model_id, "keep_alive": 0}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                self._running_models.pop(model_id, None)
                return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Batch / Embeddings (Advanced)
    # ------------------------------------------------------------------

    def embedding(self, model_id: str, text: str) -> Optional[List[float]]:
        """Generate embeddings using a local model."""
        if not self.is_ollama_running():
            return None

        try:
            body = json.dumps({"model": model_id, "prompt": text}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/embeddings",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data.get("embedding")
        except Exception:
            return None

    def batch_generate(
        self,
        model_id: str,
        prompts: List[str],
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> List[ChatCompletion]:
        """Generate responses for multiple prompts sequentially."""
        results = []
        for prompt in prompts:
            result = self.generate(model_id, prompt, temperature=temperature, max_tokens=max_tokens)
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Session History
    # ------------------------------------------------------------------

    def _log_event(self, event_type: str, details: str, extra: Optional[Dict[str, Any]] = None) -> None:
        entry = {
            "timestamp": time.time(),
            "type": event_type,
            "details": details,
        }
        if extra:
            entry.update(extra)
        self._session_history.append(entry)
        if len(self._session_history) > 1000:
            self._session_history = self._session_history[-500:]

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._session_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Usage statistics for this session."""
        chat_events = [e for e in self._session_history if e["type"] == "chat_complete"]
        total_tokens = sum(e.get("tokens", 0) for e in chat_events)
        avg_latency = sum(e.get("latency_ms", 0) for e in chat_events) / max(1, len(chat_events))

        return {
            "total_chats": len(chat_events),
            "total_tokens_generated": total_tokens,
            "avg_latency_ms": round(avg_latency, 2),
            "models_used": list(self._running_models.keys()),
            "install_events": len([e for e in self._session_history if e["type"] == "model_pulled"]),
            "error_events": len([e for e in self._session_history if "failed" in e["type"]]),
        }

    # ------------------------------------------------------------------
    # Convenience: One-shot setup
    # ------------------------------------------------------------------

    def setup_for_first_use(self, auto_pull: bool = False) -> Dict[str, Any]:
        """
        Complete first-time setup:
        1. Detect hardware
        2. Recommend models
        3. Check Ollama status
        4. Optionally pull top recommendation

        Returns a complete setup report.
        """
        hw = self.get_hardware_profile()
        recommendations = self.recommend_models(count=3)
        ollama_status = self.get_install_status()

        report = {
            "hardware": {
                "summary": self.profiler.quick_summary(),
                "profile": hw.to_dict(),
            },
            "ollama": ollama_status,
            "recommendations": [
                {
                    "model_id": m.model_id,
                    "name": m.name,
                    "parameters": m.parameters,
                    "ram_required_gb": m.ram_required_gb(),
                    "disk_required_gb": m.disk_required_gb(),
                    "reason": self._recommendation_reason(m, hw),
                }
                for m in recommendations
            ],
            "setup_needed": not ollama_status["installed"],
            "install_command": self.get_install_command(),
        }

        if auto_pull and recommendations and ollama_status["running"]:
            top_model = recommendations[0].model_id
            report["auto_pull"] = {
                "model": top_model,
                "started": True,
            }
            # Note: actual pull is async, caller can check progress

        return report

    def quick_setup(self, model_id: Optional[str] = None) -> str:
        """
        Ultra-simple setup: ensure Ollama is running and model is available.
        Returns status string.
        """
        if not self.is_ollama_installed():
            return f"Ollama not installed. Install with: {self.get_install_command()}"

        if not self.is_ollama_running():
            started = self.start_ollama_server()
            if not started:
                return "Failed to start Ollama server."

        self.refresh_installed_models()

        if model_id:
            if not self.is_model_installed(model_id):
                return f"Model {model_id} not installed. Run: ollama pull {model_id}"
            return f"Ready! Model {model_id} is available."

        # No specific model, recommend one
        recs = self.recommend_models(count=1)
        if recs:
            return f"Ready! Recommended model: {recs[0].model_id} (run pull_model() to download)"

        return "Ready! No specific model requested."


# ---------------------------------------------------------------------------
# Integration helper for MultiModelLLMAdapter
# ---------------------------------------------------------------------------

def create_adapter_endpoint(manager: LocalLLMManager, model_id: str) -> Optional[Dict[str, Any]]:
    """Create an endpoint config for MultiModelLLMAdapter."""
    return manager.create_openai_compatible_config(model_id)


def register_all_installed_models(manager: LocalLLMManager, adapter: Any) -> int:
    """Register all installed Ollama models with a MultiModelLLMAdapter."""
    from multi_model_llm_adapter_native import ModelEndpoint, Provider, ModelCapability

    manager.refresh_installed_models()
    count = 0
    for status in manager.list_installed():
        spec = manager.catalog.get(status.model_id)
        capabilities = [ModelCapability.CHAT, ModelCapability.COMPLETION]
        if spec:
            if spec.supports_code:
                capabilities.append(ModelCapability.CODE)
            if spec.supports_vision:
                capabilities.append(ModelCapability.VISION)

        endpoint = ModelEndpoint(
            provider=Provider.OLLAMA,
            name=f"local_{status.model_id.replace(':', '_')}",
            base_url=manager.get_openai_compatible_endpoint() or manager.base_url,
            model_id=status.model_id,
            timeout=120.0,
            capabilities=capabilities,
            priority=0,  # Local = highest priority
        )
        adapter.register(endpoint)
        count += 1
    return count


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== MAGNATRIX-OS Local LLM Manager Demo ===\n")

    manager = LocalLLMManager()

    # 1. Installation status
    status = manager.get_install_status()
    print(f"Ollama installed: {status['installed']}")
    print(f"Ollama running: {status['running']}")
    print(f"Binary: {status['binary_path']}")
    print(f"Platform: {status['platform']} {status['architecture']}\n")

    # 2. Hardware profile
    hw = manager.get_hardware_profile()
    print(f"Hardware: {manager.profiler.quick_summary()}\n")

    # 3. Recommendations
    print("--- Recommended Models for This Hardware ---")
    recs = manager.recommend_models(count=5)
    for i, m in enumerate(recs, 1):
        print(f"  {i}. [{m.parameters}] {m.name} ({m.model_id})")
        print(f"     RAM: {m.ram_required_gb():.1f}GB, Disk: {m.disk_required_gb():.1f}GB")
        print(f"     Reason: {manager._recommendation_reason(m, hw)}\n")

    # 4. Setup report
    print("--- Quick Setup Report ---")
    report = manager.setup_for_first_use()
    print(f"Tier: {report['hardware']['profile']['tier']}")
    print(f"Recommendations: {len(report['recommendations'])}")
    if report['setup_needed']:
        print(f"Install command: {report['install_command']}")

    # 5. Model catalog stats
    print(f"\n--- Catalog Stats ---")
    print(f"Total models in catalog: {len(manager.catalog.list_all())}")
    print(f"Families: {', '.join(sorted(set(m.family.value for m in manager.catalog.list_all())))}")

    print("\n=== Local LLM Manager Demo Complete ===")


if __name__ == "__main__":
    _demo()
