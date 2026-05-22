#!/usr/bin/env python3
"""
huggingface_model_manager.py — MAGNATRIX HuggingFace Model Manager
Layer 10 Uncensored AI — Download dan manage model uncensored lokal.

Fitur:
- Download model dari HuggingFace (Llama, Mistral, Dolphin, dll)
- Auto-select model terbaik berdasarkan hardware
- Model caching dan version management
- Quantization config (4-bit, 8-bit) untuk hemat VRAM/RAM
- Integration dengan Ollama / llama.cpp

Token HF dibaca dari .env (HUGGINGFACE_TOKEN).
"""
import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


@dataclass
class ModelInfo:
    model_id: str
    name: str
    size_gb: float
    quantization: str
    context_length: int
    uncensored: bool
    recommended_ram_gb: int
    download_url: str
    local_path: str
    status: str = "not_downloaded"  # not_downloaded | downloading | ready | failed


# Katalog model uncensored yang direkomendasikan
UNCENSORED_MODELS: Dict[str, ModelInfo] = {
    "llama3-uncensored-8b": ModelInfo(
        model_id="mlabonne/Meta-Llama-3.1-8B-Instruct-abliterated",
        name="Llama 3.1 8B Uncensored (abliterated)",
        size_gb=4.7,
        quantization="Q4_K_M",
        context_length=8192,
        uncensored=True,
        recommended_ram_gb=8,
        download_url="https://huggingface.co/mlabonne/Meta-Llama-3.1-8B-Instruct-abliterated",
        local_path="./models/llama3-8b-uncensored.gguf",
    ),
    "dolphin-mistral-7b": ModelInfo(
        model_id="cognitivecomputations/dolphin-2.9.3-mistral-7b-gguf",
        name="Dolphin Mistral 7B (Eric Hartford)",
        size_gb=4.1,
        quantization="Q4_K_M",
        context_length=32768,
        uncensored=True,
        recommended_ram_gb=8,
        download_url="https://huggingface.co/cognitivecomputations/dolphin-2.9.3-mistral-7b-gguf",
        local_path="./models/dolphin-mistral-7b.gguf",
    ),
    "hermes3-llama3.1-8b": ModelInfo(
        model_id="NousResearch/Hermes-3-Llama-3.1-8B-GGUF",
        name="Hermes 3 Llama 3.1 8B (Nous Research)",
        size_gb=4.7,
        quantization="Q4_K_M",
        context_length=8192,
        uncensored=True,
        recommended_ram_gb=8,
        download_url="https://huggingface.co/NousResearch/Hermes-3-Llama-3.1-8B-GGUF",
        local_path="./models/hermes3-llama3.1-8b.gguf",
    ),
    "qwen2.5-7b-uncensored": ModelInfo(
        model_id="Qwen/Qwen2.5-7B-Instruct-GGUF",
        name="Qwen 2.5 7B Instruct",
        size_gb=4.5,
        quantization="Q4_K_M",
        context_length=32768,
        uncensored=True,
        recommended_ram_gb=8,
        download_url="https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF",
        local_path="./models/qwen2.5-7b.gguf",
    ),
    "deepseek-coder-v2-16b": ModelInfo(
        model_id="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct-GGUF",
        name="DeepSeek Coder V2 16B (coding specialist)",
        size_gb=9.2,
        quantization="Q4_K_M",
        context_length=16384,
        uncensored=True,
        recommended_ram_gb=16,
        download_url="https://huggingface.co/deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct-GGUF",
        local_path="./models/deepseek-coder-v2-16b.gguf",
    ),
    "mixtral-8x7b-uncensored": ModelInfo(
        model_id="TheBloke/dolphin-2.7-mixtral-8x7b-GGUF",
        name="Dolphin Mixtral 8x7B (MOE)",
        size_gb=26.0,
        quantization="Q4_K_M",
        context_length=32768,
        uncensored=True,
        recommended_ram_gb=32,
        download_url="https://huggingface.co/TheBloke/dolphin-2.7-mixtral-8x7b-GGUF",
        local_path="./models/dolphin-mixtral-8x7b.gguf",
    ),
}


class HuggingFaceModelManager:
    """Manager untuk download dan manage uncensored models dari HuggingFace."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("HUGGINGFACE_TOKEN", "")
        self.models_dir = os.environ.get("MAGNATRIX_MODELS_DIR", "./models")
        self.catalog = dict(UNCENSORED_MODELS)
        os.makedirs(self.models_dir, exist_ok=True)

    def _get_hf_cmd(self) -> List[str]:
        """Return huggingface-cli command dengan token."""
        cmd = ["huggingface-cli"]
        if self.token:
            cmd.extend(["--token", self.token])
        return cmd

    def list_available_models(self) -> List[Dict]:
        """List semua model di katalog."""
        return [
            {
                "key": key,
                "name": info.name,
                "size_gb": info.size_gb,
                "quantization": info.quantization,
                "context_length": info.context_length,
                "uncensored": info.uncensored,
                "recommended_ram_gb": info.recommended_ram_gb,
                "status": info.status,
            }
            for key, info in self.catalog.items()
        ]

    def detect_hardware(self) -> Dict:
        """Deteksi hardware untuk auto-select model."""
        total_ram_gb = 8  # default fallback
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        total_ram_gb = kb / (1024 * 1024)
                        break
        except Exception:
            pass

        has_gpu = False
        try:
            result = subprocess.run(["nvidia-smi"], capture_output=True, timeout=5)
            has_gpu = result.returncode == 0
        except Exception:
            pass

        return {
            "total_ram_gb": round(total_ram_gb, 1),
            "has_gpu": has_gpu,
            "recommended_max_model_size_gb": round(total_ram_gb * 0.6, 1),
        }

    def recommend_model(self) -> Optional[str]:
        """Rekomendasikan model terbaik berdasarkan hardware."""
        hw = self.detect_hardware()
        max_size = hw["recommended_max_model_size_gb"]

        candidates = [
            (key, info) for key, info in self.catalog.items()
            if info.size_gb <= max_size and info.uncensored
        ]
        candidates.sort(key=lambda x: x[1].context_length, reverse=True)

        return candidates[0][0] if candidates else None

    def download_model(self, model_key: str, force: bool = False) -> Dict:
        """Download model dari HuggingFace."""
        if model_key not in self.catalog:
            return {"error": f"Model '{model_key}' tidak ada di katalog"}

        info = self.catalog[model_key]
        local_path = os.path.join(self.models_dir, os.path.basename(info.local_path))

        if os.path.isfile(local_path) and not force:
            info.status = "ready"
            return {
                "status": "already_downloaded",
                "model": model_key,
                "path": local_path,
                "size_mb": round(os.path.getsize(local_path) / (1024 * 1024), 1),
            }

        info.status = "downloading"
        print(f"[HF Manager] Downloading {info.name} ({info.size_gb} GB)...")
        print(f"[HF Manager] From: {info.download_url}")
        print(f"[HF Manager] To: {local_path}")

        # Simulasi download (real implementation pakai huggingface-cli atau wget/curl)
        # Contoh command yang bisa digunakan:
        # huggingface-cli download mlabonne/Meta-Llama-3.1-8B-Instruct-abliterated \
        #   --local-dir ./models --include "*.gguf"

        # Karena kita di sandbox tanpa huggingface-cli binary,
        # kita simulasikan success dan create placeholder
        try:
            # Create placeholder file untuk demo
            with open(local_path, "wb") as f:
                f.write(b"# MAGNATRIX Model Placeholder\n")
                f.write(f"# Model: {info.name}\n".encode())
                f.write(f"# Source: {info.download_url}\n".encode())
                f.write(f"# Downloaded: {datetime.now(timezone.utc).isoformat()}\n".encode())
                # Pad to approximate size for demo
                f.write(b"\0" * 1024)

            info.status = "ready"
            return {
                "status": "downloaded",
                "model": model_key,
                "path": local_path,
                "note": "Placeholder created. Run real huggingface-cli download for actual model.",
            }
        except Exception as e:
            info.status = "failed"
            return {"error": str(e), "model": model_key}

    def get_model_path(self, model_key: str) -> Optional[str]:
        """Get local path untuk model jika sudah download."""
        if model_key not in self.catalog:
            return None
        info = self.catalog[model_key]
        local_path = os.path.join(self.models_dir, os.path.basename(info.local_path))
        return local_path if os.path.isfile(local_path) else None

    def get_download_command(self, model_key: str) -> str:
        """Get huggingface-cli download command untuk model."""
        if model_key not in self.catalog:
            return "# Model not found"
        info = self.catalog[model_key]
        token_flag = f" --token {self.token}" if self.token else ""
        return (
            f"huggingface-cli download {info.model_id}{token_flag} "
            f"--local-dir {self.models_dir} "
            f"--include '*.gguf'"
        )

    def export_catalog(self) -> str:
        """Export katalog ke JSON."""
        return json.dumps(
            {k: {"name": v.name, "size_gb": v.size_gb, "status": v.status}
             for k, v in self.catalog.items()},
            indent=2,
        )


# ── demo ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("MAGNATRIX HuggingFace Model Manager — Uncensored AI Layer")
    print("=" * 70)

    manager = HuggingFaceModelManager()

    print("\n[1] TOKEN STATUS")
    if manager.token:
        print(f"  ✅ Token aktif: {manager.token[:10]}...{manager.token[-4:]}")
    else:
        print("  ⚠️  Token tidak ditemukan. Set HUGGINGFACE_TOKEN di .env")

    print("\n[2] HARDWARE DETECTION")
    hw = manager.detect_hardware()
    print(f"  RAM Total     : {hw['total_ram_gb']} GB")
    print(f"  GPU Detected  : {'Ya' if hw['has_gpu'] else 'Tidak'}")
    print(f"  Max Model Size: {hw['recommended_max_model_size_gb']} GB")

    print("\n[3] AVAILABLE MODELS")
    for m in manager.list_available_models():
        print(f"  📦 {m['key']:<30s} {m['name'][:40]:<40s} {m['size_gb']} GB")

    print("\n[4] RECOMMENDED MODEL")
    rec = manager.recommend_model()
    if rec:
        info = manager.catalog[rec]
        print(f"  ⭐ {rec}: {info.name}")
        print(f"     Size: {info.size_gb} GB | Context: {info.context_length} tokens")
    else:
        print("  ⚠️  Tidak ada model yang cocok untuk hardware ini")

    print("\n[5] DOWNLOAD COMMAND (untuk model recommended)")
    if rec:
        cmd = manager.get_download_command(rec)
        print(f"  {cmd}")

    print("\n[6] SIMULATED DOWNLOAD")
    if rec:
        result = manager.download_model(rec)
        print(f"  Status: {result.get('status', result.get('error'))}")
        if "path" in result:
            print(f"  Path  : {result['path']}")

    print("\n" + "=" * 70)
    print("Model manager selesai.")
    print("=" * 70)
