#!/usr/bin/env python3
"""compute_hunter_native.py — Auto-Hunting GPU, ASIC, CPU for Mesh LLM Deployment.

Discovers free/low-cost compute resources, matches capability to LLM requirements,
auto-deploys models, auto-scales, auto-fallback. Compute-matched mesh intelligence.
"""

from __future__ import annotations
import json, time, random, hashlib, math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto


class ComputeType(Enum):
    GPU = "gpu"
    CPU = "cpu"
    ASIC = "asic"
    TPU = "tpu"
    FPGA = "fpga"
    EDGE = "edge"


class ProviderCategory(Enum):
    CLOUD_FREE = "cloud_free"
    CLOUD_TRIAL = "cloud_trial"
    COLAB = "colab"
    KAGGLE = "kaggle"
    ACADEMIC = "academic"
    COMMUNITY = "community"
    LOCAL = "local"
    SERVERLESS = "serverless"
    EDGE = "edge"


@dataclass
class ComputeNode:
    id: str
    provider: str
    category: ProviderCategory
    compute_type: ComputeType
    region: str
    specs: Dict[str, Any]
    vram_mb: Optional[int]
    ram_mb: int
    cores: int
    clock_ghz: float
    tflops: Optional[float]
    cost_per_hour: float  # 0.0 = free
    availability: float  # 0-1 probability
    queue_time_min: int
    max_runtime_hours: int
    status: str
    assigned_model: Optional[str] = None
    utilization: float = 0.0


@dataclass
class ModelRequirement:
    model_id: str
    param_count: int
    quant_bits: int
    min_vram_mb: int
    min_ram_mb: int
    min_tflops: Optional[float]
    preferred_compute: ComputeType
    max_latency_ms: int
    batch_size: int
    parallelism: int


class ComputeRegistry:
    """Registry of known free/cheap compute resources."""

    def __init__(self):
        self._nodes: List[ComputeNode] = []
        self._init_known_resources()

    def _init_known_resources(self):
        self._nodes = [
            # GPU Free/Trial
            ComputeNode("GH-GPU-1", "GitHub Codespaces", ProviderCategory.CLOUD_FREE, ComputeType.GPU, "US-East", {"gpu": "NVIDIA T4", "cuda": "12.1"}, 16384, 8192, 4, 2.5, 8.1, 0.0, 0.8, 5, 4, "available"),
            ComputeNode("GC-GPU-1", "Google Colab", ProviderCategory.COLAB, ComputeType.GPU, "US-Central", {"gpu": "NVIDIA T4", "cuda": "12.1"}, 16384, 12288, 2, 2.5, 8.1, 0.0, 0.7, 10, 12, "available"),
            ComputeNode("GC-GPU-2", "Google Colab Pro", ProviderCategory.COLAB, ComputeType.GPU, "US-Central", {"gpu": "NVIDIA A100", "cuda": "12.1"}, 40960, 24576, 2, 2.5, 19.5, 9.99, 0.6, 15, 24, "available"),
            ComputeNode("KG-GPU-1", "Kaggle", ProviderCategory.KAGGLE, ComputeType.GPU, "US-Central", {"gpu": "NVIDIA T4", "cuda": "12.1"}, 16384, 16384, 2, 2.5, 8.1, 0.0, 0.75, 8, 9, "available"),
            ComputeNode("KG-GPU-2", "Kaggle TPU", ProviderCategory.KAGGLE, ComputeType.TPU, "US-Central", {"tpu": "TPU v3-8", "tpu_version": "v3"}, None, 32768, 8, 2.0, 45.0, 0.0, 0.6, 12, 9, "available"),
            ComputeNode("AWS-GPU-1", "AWS SageMaker Free", ProviderCategory.CLOUD_TRIAL, ComputeType.GPU, "US-East", {"gpu": "NVIDIA T4", "cuda": "12.1"}, 16384, 8192, 4, 2.5, 8.1, 0.0, 0.5, 20, 4, "available"),
            ComputeNode("GCP-GPU-1", "GCP Vertex Free", ProviderCategory.CLOUD_TRIAL, ComputeType.GPU, "US-East", {"gpu": "NVIDIA T4", "cuda": "12.1"}, 16384, 8192, 4, 2.5, 8.1, 0.0, 0.5, 20, 4, "available"),
            ComputeNode("AZ-GPU-1", "Azure ML Free", ProviderCategory.CLOUD_TRIAL, ComputeType.GPU, "US-East", {"gpu": "NVIDIA T4", "cuda": "12.1"}, 16384, 8192, 4, 2.5, 8.1, 0.0, 0.5, 20, 4, "available"),
            ComputeNode("DO-GPU-1", "DigitalOcean GPU", ProviderCategory.CLOUD_TRIAL, ComputeType.GPU, "US-East", {"gpu": "NVIDIA H100", "cuda": "12.2"}, 81920, 65536, 8, 3.0, 67.0, 2.5, 0.9, 2, 8, "available"),
            ComputeNode("LN-GPU-1", "Lambda GPU", ProviderCategory.CLOUD_TRIAL, ComputeType.GPU, "US-West", {"gpu": "NVIDIA A100", "cuda": "12.1"}, 40960, 32768, 8, 2.5, 19.5, 1.5, 0.85, 3, 4, "available"),
            ComputeNode("PG-GPU-1", "Paperspace Free", ProviderCategory.CLOUD_FREE, ComputeType.GPU, "US-East", {"gpu": "NVIDIA T4", "cuda": "12.1"}, 16384, 8192, 4, 2.5, 8.1, 0.0, 0.7, 10, 6, "available"),
            ComputeNode("RN-GPU-1", "RunPod Community", ProviderCategory.COMMUNITY, ComputeType.GPU, "US-East", {"gpu": "NVIDIA RTX 4090", "cuda": "12.1"}, 24576, 32768, 8, 3.0, 82.0, 0.44, 0.9, 1, 24, "available"),
            ComputeNode("VR-GPU-1", "Vast.ai Spot", ProviderCategory.COMMUNITY, ComputeType.GPU, "Global", {"gpu": "NVIDIA RTX 3090", "cuda": "12.1"}, 24576, 32768, 8, 2.5, 35.0, 0.20, 0.9, 1, 24, "available"),
            ComputeNode("FL-GPU-1", "FluidStack", ProviderCategory.COMMUNITY, ComputeType.GPU, "US-East", {"gpu": "NVIDIA A100", "cuda": "12.1"}, 40960, 65536, 8, 2.5, 19.5, 1.2, 0.85, 2, 24, "available"),
            ComputeNode("CR-GPU-1", "CoreWeave", ProviderCategory.COMMUNITY, ComputeType.GPU, "US-East", {"gpu": "NVIDIA A100x8", "cuda": "12.1"}, 40960*8, 262144, 64, 2.5, 156.0, 2.0, 0.9, 1, 24, "available"),
            ComputeNode("LN-GPU-2", "LinGPU", ProviderCategory.COMMUNITY, ComputeType.GPU, "EU-West", {"gpu": "NVIDIA RTX A6000", "cuda": "12.1"}, 49152, 65536, 8, 2.5, 38.0, 0.80, 0.9, 1, 24, "available"),
            ComputeNode("SH-GPU-1", "Shadeform", ProviderCategory.COMMUNITY, ComputeType.GPU, "US-East", {"gpu": "NVIDIA H100", "cuda": "12.2"}, 81920, 262144, 8, 3.0, 67.0, 2.0, 0.9, 1, 24, "available"),
            # CPU Free/Trial
            ComputeNode("GH-CPU-1", "GitHub Actions", ProviderCategory.CLOUD_FREE, ComputeType.CPU, "US-East", {"cpu": "Intel Xeon", "cores": 4}, None, 7168, 4, 2.5, None, 0.0, 0.9, 1, 6, "available"),
            ComputeNode("OR-CPU-1", "Oracle Cloud Free", ProviderCategory.CLOUD_FREE, ComputeType.CPU, "Multi", {"cpu": "AMD EPYC", "cores": 4}, None, 24576, 4, 2.0, None, 0.0, 0.95, 0, 8760, "available"),
            ComputeNode("AWS-CPU-1", "AWS EC2 Free", ProviderCategory.CLOUD_FREE, ComputeType.CPU, "US-East", {"cpu": "Intel Xeon", "cores": 2}, None, 1024, 2, 2.5, None, 0.0, 0.95, 0, 750, "available"),
            ComputeNode("GCP-CPU-1", "GCP Free", ProviderCategory.CLOUD_FREE, ComputeType.CPU, "US-East", {"cpu": "Intel Xeon", "cores": 2}, None, 1024, 2, 2.5, None, 0.0, 0.95, 0, 8760, "available"),
            ComputeNode("AZ-CPU-1", "Azure Free", ProviderCategory.CLOUD_FREE, ComputeType.CPU, "US-East", {"cpu": "Intel Xeon", "cores": 2}, None, 1024, 2, 2.5, None, 0.0, 0.95, 0, 750, "available"),
            ComputeNode("DO-CPU-1", "DigitalOcean Free", ProviderCategory.CLOUD_TRIAL, ComputeType.CPU, "US-East", {"cpu": "Intel Xeon", "cores": 1}, None, 1024, 1, 2.5, None, 0.0, 0.95, 0, 2000, "available"),
            ComputeNode("HF-CPU-1", "HuggingFace Spaces", ProviderCategory.COMMUNITY, ComputeType.CPU, "US-East", {"cpu": "Intel Xeon", "cores": 2}, None, 16384, 2, 2.5, None, 0.0, 0.85, 5, 24, "available"),
            ComputeNode("HF-CPU-2", "HuggingFace ZeroGPU", ProviderCategory.COMMUNITY, ComputeType.GPU, "US-East", {"gpu": "NVIDIA A10G", "cuda": "12.1"}, 24576, 32768, 8, 2.5, 31.0, 0.0, 0.7, 10, 24, "available"),
            ComputeNode("RE-CPU-1", "Replicate Free", ProviderCategory.COMMUNITY, ComputeType.CPU, "US-East", {"cpu": "Intel Xeon", "cores": 4}, None, 8192, 4, 2.5, None, 0.0, 0.8, 5, 24, "available"),
            ComputeNode("BE-CPU-1", "Beam Cloud", ProviderCategory.COMMUNITY, ComputeType.CPU, "US-East", {"cpu": "Intel Xeon", "cores": 8}, None, 32768, 8, 2.5, None, 0.0, 0.8, 5, 24, "available"),
            # ASIC/Edge
            ComputeNode("GC-TPU-1", "Google Cloud TPU", ProviderCategory.CLOUD_TRIAL, ComputeType.TPU, "US-Central", {"tpu": "TPU v4", "tpu_version": "v4"}, None, 32768, 4, 2.0, 275.0, 0.0, 0.5, 20, 4, "available"),
            ComputeNode("GC-TPU-2", "Google Cloud TPU", ProviderCategory.CLOUD_TRIAL, ComputeType.TPU, "US-Central", {"tpu": "TPU v5e", "tpu_version": "v5e"}, None, 32768, 8, 2.0, 393.0, 0.0, 0.5, 20, 4, "available"),
            ComputeNode("ED-ASIC-1", "Edge TPU (Coral)", ProviderCategory.EDGE, ComputeType.ASIC, "Edge", {"asic": "Coral Edge TPU", "int8_only": True}, None, 1024, 1, 1.0, 4.0, 0.0, 0.95, 0, 8760, "available"),
            ComputeNode("ED-FPGA-1", "AMD FPGA", ProviderCategory.EDGE, ComputeType.FPGA, "Edge", {"fpga": "AMD Alveo", "int8": True}, None, 8192, 4, 2.0, 15.0, 0.0, 0.95, 0, 8760, "available"),
        ]

    def discover(self, compute_type: ComputeType = None) -> List[ComputeNode]:
        if compute_type:
            return [n for n in self._nodes if n.compute_type == compute_type]
        return self._nodes

    def get_free(self) -> List[ComputeNode]:
        return [n for n in self._nodes if n.cost_per_hour == 0.0 and n.status == "available"]

    def get_best_for_vram(self, min_vram_mb: int) -> List[ComputeNode]:
        candidates = [n for n in self._nodes if n.vram_mb and n.vram_mb >= min_vram_mb and n.status == "available"]
        return sorted(candidates, key=lambda n: (n.cost_per_hour, -n.availability))[:10]

    def get_best_for_cpu(self, min_cores: int, min_ram_mb: int) -> List[ComputeNode]:
        candidates = [n for n in self._nodes if n.cores >= min_cores and n.ram_mb >= min_ram_mb and n.status == "available"]
        return sorted(candidates, key=lambda n: (n.cost_per_hour, -n.availability))[:10]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total": len(self._nodes),
            "gpu": sum(1 for n in self._nodes if n.compute_type == ComputeType.GPU),
            "cpu": sum(1 for n in self._nodes if n.compute_type == ComputeType.CPU),
            "tpu": sum(1 for n in self._nodes if n.compute_type == ComputeType.TPU),
            "asic": sum(1 for n in self._nodes if n.compute_type == ComputeType.ASIC),
            "free": sum(1 for n in self._nodes if n.cost_per_hour == 0.0),
            "available": sum(1 for n in self._nodes if n.status == "available"),
        }


class ModelMatcher:
    """Match LLM requirements to compute resources."""

    def __init__(self, registry: ComputeRegistry):
        self.registry = registry

    def estimate_vram(self, params: int, quant_bits: int, batch_size: int = 1) -> int:
        """Estimate VRAM needed for inference."""
        bytes_per_param = quant_bits / 8
        base = params * bytes_per_param
        kv_cache = base * 0.2 * batch_size
        overhead = base * 0.1
        return int((base + kv_cache + overhead) / (1024 * 1024))

    def find_match(self, req: ModelRequirement) -> Optional[ComputeNode]:
        """Find best compute node for a model requirement."""
        candidates = self.registry.discover(req.preferred_compute)
        if req.min_vram_mb:
            candidates = [n for n in candidates if n.vram_mb and n.vram_mb >= req.min_vram_mb]
        candidates = [n for n in candidates if n.ram_mb >= req.min_ram_mb]
        if req.min_tflops:
            candidates = [n for n in candidates if n.tflops and n.tflops >= req.min_tflops]
        if not candidates:
            return None
        # Score: lower cost, higher availability, more capacity margin
        def score(n):
            cost_score = 1.0 / (1.0 + n.cost_per_hour)
            avail_score = n.availability
            margin_score = 1.0
            if n.vram_mb and req.min_vram_mb:
                margin_score = n.vram_mb / req.min_vram_mb
            return cost_score * 0.4 + avail_score * 0.4 + min(margin_score, 2.0) * 0.2
        return max(candidates, key=score)

    def match_all(self, reqs: List[ModelRequirement]) -> List[Tuple[ModelRequirement, Optional[ComputeNode]]]:
        return [(req, self.find_match(req)) for req in reqs]


class AutoDeployer:
    """Auto-deploy LLM models to matched compute nodes."""

    def __init__(self, registry: ComputeRegistry, matcher: ModelMatcher):
        self.registry = registry
        self.matcher = matcher
        self._deployments: List[Dict[str, Any]] = []

    def deploy(self, model_req: ModelRequirement) -> Dict[str, Any]:
        node = self.matcher.find_match(model_req)
        if not node:
            return {"error": "No matching compute node found", "model_id": model_req.model_id}
        node.status = "busy"
        node.assigned_model = model_req.model_id
        node.utilization = 0.85
        deploy_id = f"DEPLOY-{hashlib.sha256(f'{model_req.model_id}:{node.id}:{time.time()}'.encode()).hexdigest()[:8]}"
        result = {
            "deploy_id": deploy_id, "model_id": model_req.model_id,
            "node_id": node.id, "provider": node.provider,
            "compute_type": node.compute_type.value, "region": node.region,
            "vram_mb": node.vram_mb, "ram_mb": node.ram_mb,
            "cost_per_hour": node.cost_per_hour, "estimated_latency_ms": model_req.max_latency_ms,
            "status": "deployed", "deployed_at": time.time(),
        }
        self._deployments.append(result)
        return result

    def scale_up(self, model_id: str, replicas: int = 2) -> List[Dict[str, Any]]:
        """Deploy additional replicas across available nodes."""
        results = []
        available = [n for n in self.registry._nodes if n.status == "available"]
        for i, node in enumerate(available[:replicas]):
            node.status = "busy"
            node.assigned_model = model_id
            results.append({"replica": i + 1, "node_id": node.id, "provider": node.provider, "status": "scaled"})
        return results

    def get_deployments(self) -> List[Dict[str, Any]]:
        return self._deployments

    def get_stats(self) -> Dict[str, Any]:
        return {"total_deployments": len(self._deployments), "active_nodes": sum(1 for n in self.registry._nodes if n.status == "busy")}


class MeshComputeEngine:
    """Main orchestrator: discover → match → deploy → scale."""

    def __init__(self):
        self.registry = ComputeRegistry()
        self.matcher = ModelMatcher(self.registry)
        self.deployer = AutoDeployer(self.registry, self.matcher)

    def full_mesh_deploy(self) -> Dict[str, Any]:
        print(f"{'='*60}")
        print("[COMPUTE-HUNTER] Auto-Hunting GPU/ASIC/CPU for Mesh LLM")
        print(f"{'='*60}")

        stats = self.registry.get_stats()
        print(f"\nRegistry: {stats['total']} nodes")
        print(f"    GPU: {stats['gpu']} | CPU: {stats['cpu']} | TPU: {stats['tpu']} | ASIC: {stats['asic']}")
        print(f"    Free: {stats['free']} | Available: {stats['available']}")

        # Define model requirements
        models = [
            ModelRequirement("magnatrix-125m", 125_000_000, 16, 512, 4096, None, ComputeType.CPU, 500, 1, 1),
            ModelRequirement("magnatrix-1b", 1_000_000_000, 16, 3072, 8192, 5.0, ComputeType.GPU, 300, 1, 1),
            ModelRequirement("magnatrix-7b", 7_000_000_000, 4, 4096, 16384, 15.0, ComputeType.GPU, 200, 1, 1),
            ModelRequirement("magnatrix-7b-int8", 7_000_000_000, 8, 8192, 16384, 8.0, ComputeType.GPU, 200, 1, 1),
            ModelRequirement("magnatrix-7b-int4", 7_000_000_000, 4, 5120, 16384, 5.0, ComputeType.GPU, 200, 1, 1),
            ModelRequirement("magnatrix-70b", 70_000_000_000, 4, 40960, 65536, 50.0, ComputeType.GPU, 500, 1, 8),
        ]

        print(f"\nMatching {len(models)} models to compute nodes:")
        for req in models:
            vram_est = self.matcher.estimate_vram(req.param_count, req.quant_bits)
            match = self.matcher.find_match(req)
            if match:
                deploy = self.deployer.deploy(req)
                print(f"    {req.model_id}: {match.provider} ({match.compute_type.value}) | vram_est={vram_est}MB | cost=${match.cost_per_hour}/h | match={match.id}")
            else:
                print(f"    {req.model_id}: NO MATCH (vram_est={vram_est}MB) — fallback to CPU")
                # Fallback to CPU
                cpu_nodes = self.registry.get_best_for_cpu(4, 8192)
                if cpu_nodes:
                    fallback = cpu_nodes[0]
                    fallback.status = "busy"
                    print(f"      -> Fallback: {fallback.provider} CPU")

        # Scale up top model
        print(f"\nScaling up 7B model...")
        scaled = self.deployer.scale_up("magnatrix-7b", replicas=2)
        for s in scaled:
            print(f"    Replica {s['replica']}: {s['node_id']} ({s['provider']})")

        print(f"\nDeployments: {len(self.deployer.get_deployments())}")
        print(f"  Active nodes: {sum(1 for n in self.registry._nodes if n.status == 'busy')}")
        print(f"{'='*60}\n")
        return self.deployer.get_stats()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "registry": self.registry.get_stats(),
            "deployer": self.deployer.get_stats(),
        }


if __name__ == "__main__":
    engine = MeshComputeEngine()
    result = engine.full_mesh_deploy()
    print(f"[STATS] {json.dumps(result, indent=2)}")
