#!/usr/bin/env python3
"""
Hardware Inference + Edge Deployment for MAGNATRIX-OS
====================================================
Hardware-aware model selection, on-device inference optimization,
edge deployment, quantization-aware execution. Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import json, os, platform, struct, subprocess, time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class HardwarePlatform(Enum):
    CPU = "cpu"
    GPU = "gpu"
    TPU = "tpu"
    NPU = "npu"
    MOBILE = "mobile"
    EDGE = "edge"


class QuantizationType(Enum):
    NONE = "none"
    INT8 = "int8"
    INT4 = "int4"
    FP16 = "fp16"
    GGUF_Q4 = "gguf_q4"
    GGUF_Q8 = "gguf_q8"


@dataclass
class HardwareProfile:
    """Detected hardware profile."""
    platform: str = "cpu"
    cpu_cores: int = 1
    cpu_freq_mhz: float = 0.0
    ram_gb: float = 0.0
    has_gpu: bool = False
    has_npu: bool = False
    has_tpu: bool = False
    os_name: str = ""
    arch: str = ""
    supports_avx2: bool = False
    supports_neon: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def detect(cls) -> "HardwareProfile":
        """Auto-detect hardware."""
        profile = cls()
        profile.os_name = platform.system()
        profile.arch = platform.machine()
        try:
            profile.cpu_cores = os.cpu_count() or 1
        except Exception:
            pass
        # RAM detection
        try:
            if profile.os_name == "Linux":
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            kb = int(line.split()[1])
                            profile.ram_gb = kb / (1024 * 1024)
                            break
            elif profile.os_name == "Darwin":
                result = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
                if result.returncode == 0:
                    profile.ram_gb = int(result.stdout.strip()) / (1024**3)
        except Exception:
            pass
        # Architecture flags
        if profile.arch in ("x86_64", "AMD64"):
            try:
                with open("/proc/cpuinfo", "r") as f:
                    cpuinfo = f.read()
                    profile.supports_avx2 = "avx2" in cpuinfo.lower()
            except Exception:
                pass
        elif profile.arch in ("arm64", "aarch64"):
            profile.supports_neon = True
        return profile


@dataclass
class ModelSpec:
    """Model specification for deployment."""
    model_id: str
    name: str
    size_mb: float = 0.0
    params_b: float = 0.0
    quantization: QuantizationType = QuantizationType.NONE
    required_ram_mb: float = 0.0
    target_platform: List[HardwarePlatform] = field(default_factory=list)
    performance_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["quantization"] = self.quantization.value
        d["target_platform"] = [p.value for p in self.target_platform]
        return d


class HardwareProfiler:
    """Profiles hardware and recommends model configurations."""

    def __init__(self) -> None:
        self.profile = HardwareProfile.detect()
        self._models: Dict[str, ModelSpec] = {}

    def register_model(self, spec: ModelSpec) -> None:
        self._models[spec.model_id] = spec

    def can_run(self, model_id: str) -> Tuple[bool, str]:
        """Check if hardware can run a model."""
        model = self._models.get(model_id)
        if not model:
            return False, "Model not registered"
        if model.required_ram_mb > self.profile.ram_gb * 1024:
            return False, f"Insufficient RAM: {self.profile.ram_gb:.1f}GB < {model.required_ram_mb/1024:.1f}GB required"
        if model.size_mb > self.profile.ram_gb * 1024 * 0.7:
            return False, f"Model too large for available RAM"
        return True, "OK"

    def recommend_quantization(self, model_id: str) -> QuantizationType:
        """Recommend quantization level for hardware."""
        model = self._models.get(model_id)
        if not model:
            return QuantizationType.NONE
        ram_mb = self.profile.ram_gb * 1024
        if ram_mb < 4096:
            return QuantizationType.GGUF_Q4
        elif ram_mb < 8192:
            return QuantizationType.INT8
        elif self.profile.has_gpu or self.profile.has_npu:
            return QuantizationType.FP16
        return QuantizationType.GGUF_Q8

    def recommend_model(self, task: str = "general") -> Optional[str]:
        """Recommend best model for hardware and task."""
        candidates = []
        for model_id, model in self._models.items():
            can_run, _ = self.can_run(model_id)
            if can_run:
                score = model.performance_score
                # Bonus for quantization match
                rec_q = self.recommend_quantization(model_id)
                if model.quantization == rec_q:
                    score *= 1.2
                candidates.append((model_id, score))
        if not candidates:
            return None
        return max(candidates, key=lambda x: x[1])[0]

    def get_profile(self) -> Dict[str, Any]:
        return self.profile.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile.to_dict(),
            "models": len(self._models),
            "recommendations": {m: self.recommend_quantization(m).value for m in self._models},
        }


class InferenceOptimizer:
    """Optimizes inference for on-device execution."""

    def __init__(self, profiler: HardwareProfiler) -> None:
        self.profiler = profiler
        self._optimization_log: List[Dict[str, Any]] = []

    def optimize(self, model_id: str, input_shape: Tuple[int, ...] = ()) -> Dict[str, Any]:
        """Generate optimization config for a model."""
        can_run, reason = self.profiler.can_run(model_id)
        if not can_run:
            return {"error": reason, "optimized": False}
        rec_q = self.profiler.recommend_quantization(model_id)
        config = {
            "model_id": model_id,
            "quantization": rec_q.value,
            "thread_count": self.profiler.profile.cpu_cores,
            "batch_size": 1,
            "memory_limit_mb": self.profiler.profile.ram_gb * 1024 * 0.6,
            "use_gpu": self.profiler.profile.has_gpu,
            "use_npu": self.profiler.profile.has_npu,
            "optimized": True,
        }
        # Platform-specific tweaks
        if self.profiler.profile.arch in ("arm64", "aarch64"):
            config["use_neon"] = True
            config["thread_count"] = max(1, self.profiler.profile.cpu_cores // 2)
        if self.profiler.profile.ram_gb < 4:
            config["batch_size"] = 1
            config["memory_limit_mb"] = min(config["memory_limit_mb"], 1024)
        self._optimization_log.append({"model": model_id, "config": config, "timestamp": time.time()})
        return config

    def benchmark(self, model_id: str, iterations: int = 10) -> Dict[str, Any]:
        """Benchmark inference performance."""
        times = []
        for _ in range(iterations):
            t0 = time.time()
            time.sleep(0.001)  # Simulate inference
            times.append((time.time() - t0) * 1000)
        avg = sum(times) / len(times)
        return {
            "model_id": model_id,
            "avg_latency_ms": round(avg, 2),
            "throughput_qps": round(1000 / avg, 2) if avg > 0 else 0,
            "iterations": iterations,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {"optimizations": len(self._optimization_log)}


class EdgeDeployer:
    """Deploys models to edge devices."""

    def __init__(self, profiler: HardwareProfiler) -> None:
        self.profiler = profiler
        self._deployments: Dict[str, Dict[str, Any]] = {}

    def deploy(self, model_id: str, target: str = "local") -> Dict[str, Any]:
        """Deploy a model to target device."""
        can_run, reason = self.profiler.can_run(model_id)
        if not can_run:
            return {"error": reason, "deployed": False}
        optimizer = InferenceOptimizer(self.profiler)
        config = optimizer.optimize(model_id)
        deployment = {
            "model_id": model_id,
            "target": target,
            "config": config,
            "deployed_at": time.time(),
            "status": "active",
        }
        self._deployments[model_id] = deployment
        return {"deployed": True, "deployment": deployment}

    def undeploy(self, model_id: str) -> bool:
        if model_id in self._deployments:
            self._deployments[model_id]["status"] = "stopped"
            return True
        return False

    def get_deployment(self, model_id: str) -> Optional[Dict[str, Any]]:
        return self._deployments.get(model_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deployments": len(self._deployments),
            "targets": list(set(d["target"] for d in self._deployments.values())),
        }


class HardwareInferenceEngine:
    """Top-level hardware inference + edge deployment engine."""

    def __init__(self, repo_root: str = "") -> None:
        self.repo_root = repo_root
        self.profiler = HardwareProfiler()
        self.optimizer = InferenceOptimizer(self.profiler)
        self.deployer = EdgeDeployer(self.profiler)
        self._seed_models()

    def _seed_models(self) -> None:
        # Seed with common open-source models
        self.profiler.register_model(ModelSpec(
            model_id="qwen2.5-7b",
            name="Qwen 2.5 7B",
            size_mb=14000,
            params_b=7.0,
            required_ram_mb=16000,
            target_platform=[HardwarePlatform.CPU, HardwarePlatform.GPU],
            performance_score=0.85,
        ))
        self.profiler.register_model(ModelSpec(
            model_id="llama3.2-3b",
            name="Llama 3.2 3B",
            size_mb=6000,
            params_b=3.0,
            required_ram_mb=8000,
            target_platform=[HardwarePlatform.CPU, HardwarePlatform.GPU, HardwarePlatform.MOBILE],
            performance_score=0.80,
        ))
        self.profiler.register_model(ModelSpec(
            model_id="phi-4-4b",
            name="Phi-4 4B",
            size_mb=8000,
            params_b=4.0,
            required_ram_mb=10000,
            target_platform=[HardwarePlatform.CPU, HardwarePlatform.GPU, HardwarePlatform.EDGE],
            performance_score=0.82,
        ))
        self.profiler.register_model(ModelSpec(
            model_id="tinyllama-1b",
            name="TinyLlama 1.1B",
            size_mb=2200,
            params_b=1.1,
            required_ram_mb=4000,
            target_platform=[HardwarePlatform.CPU, HardwarePlatform.MOBILE, HardwarePlatform.EDGE],
            performance_score=0.65,
        ))

    def detect_hardware(self) -> Dict[str, Any]:
        return self.profiler.get_profile()

    def recommend(self, task: str = "general") -> Optional[str]:
        return self.profiler.recommend_model(task)

    def optimize(self, model_id: str) -> Dict[str, Any]:
        return self.optimizer.optimize(model_id)

    def benchmark(self, model_id: str, iterations: int = 10) -> Dict[str, Any]:
        return self.optimizer.benchmark(model_id, iterations)

    def deploy(self, model_id: str, target: str = "local") -> Dict[str, Any]:
        return self.deployer.deploy(model_id, target)

    def get_status(self) -> Dict[str, Any]:
        return {
            "hardware": self.profiler.get_profile(),
            "models": len(self.profiler._models),
            "deployments": self.deployer.to_dict(),
            "recommendation": self.recommend(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_status()
