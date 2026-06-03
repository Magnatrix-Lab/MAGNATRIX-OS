"""
llm_transformer_block_native.py
MAGNATRIX-OS Transformer Block Engine
Native Python, stdlib only.
Provides transformer block assembly, residual connections, pre/post-norm selection, and block stacking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class TransformerBlockEngine:
    """Transformer block assembly and execution."""

    def __init__(self, use_pre_norm: bool = True) -> None:
        self.use_pre_norm = use_pre_norm
        self._blocks: List[Dict[str, Any]] = []

    def add_block(self, attention_fn: Callable, ffn_fn: Callable, norm_fn: Callable, name: str = "block") -> None:
        self._blocks.append({"name": name, "attn": attention_fn, "ffn": ffn_fn, "norm": norm_fn})

    def forward(self, x: Any) -> Any:
        for block in self._blocks:
            if self.use_pre_norm:
                normed = block["norm"](x)
                attn_out = block["attn"](normed)
                x = x + attn_out
                normed = block["norm"](x)
                ffn_out = block["ffn"](normed)
                x = x + ffn_out
            else:
                attn_out = block["attn"](x)
                x = block["norm"](x + attn_out)
                ffn_out = block["ffn"](x)
                x = block["norm"](x + ffn_out)
        return x

    def get_stats(self) -> Dict[str, Any]:
        return {"blocks": len(self._blocks), "pre_norm": self.use_pre_norm}


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Transformer Block Engine")
    print("=" * 60)
    engine = TransformerBlockEngine(use_pre_norm=True)
    identity = lambda x: x
    engine.add_block(identity, identity, lambda x: [v * 0.5 for v in x], "block_0")
    x = [1.0, 2.0, 3.0]
    result = engine.forward(x)
    print(f"  Input: {x}")
    print(f"  Output: {result}")
    print(f"  Stats: {engine.get_stats()}")
    print("\nTransformer Block test complete.")

if __name__ == "__main__":
    run()
