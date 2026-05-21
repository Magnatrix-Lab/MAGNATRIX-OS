# autoresearch (Karpathy) — Reference for MAGNATRIX Agentic OS

> **Repo**: https://github.com/karpathy/autoresearch | 82.4k stars | Recursive Self-Improvement Proof-of-Concept

## Status: REFERENCED / STUDIED

---

## Why This Matters for MAGNATRIX

Andrej Karpathy (ex-OpenAI, ex-Tesla AI Director) membuktikan bahwa **recursive self-improvement** bukan sekadar teori. Repo ini adalah implementasi nyata:

> "AI agent modify `train.py` → run training (5 min) → check result improved? → keep/discard → repeat overnight"

Ini adalah **foundational paper** untuk Phase 4 Proto-AGI di MAGNATRIX.

---

## Key Concepts untuk MAGNATRIX

### 1. Programming via Markdown
- `program.md` = context/constitution untuk AI agent
- Bukan modify code langsung, tapi agent di-program via Markdown
- **Meta-programming** pattern

### 2. Keep/Discard Logic
- Agent decide sendiri mana improvement worth keeping
- Proto-decision-making autonomous

### 3. Results Analysis
- `analysis.ipynb` + `results.tsv` = automated experiment tracking
- Layer 5 Knowledge persistence

### 4. Single-GPU Friendly
- nanochat training = lightweight
- Bisa jalan di edge device (Android Claw)

---

## Adaptation untuk MAGNATRIX

### Pattern: Recursive Code Improvement

```python
# magnatrix-os/collective-brain/autoresearch/pipeline.py

class RecursiveImprovementPipeline:
    """
    1. Observe: monitor own performance
    2. Hypothesize: generate improvement candidate
    3. Sandbox: test in isolated environment
    4. Evaluate: check metric improvement
    5. Keep/Discard: auto-decide
    6. Log: append-only audit trail
    """
    
    def run_loop(self, target_file: str, metric: str, max_iterations: int = 10):
        for i in range(max_iterations):
            # 1. Modify
            patch = self.generate_patch(target_file)
            
            # 2. Test
            result = self.run_test(patch)
            
            # 3. Evaluate
            improved = self.check_metric(result, metric)
            
            # 4. Decide
            if improved:
                self.apply_patch(patch)
                self.log("KEEP", patch, result)
            else:
                self.log("DISCARD", patch, result)
```

### Safety Gate (MAGNATRIX Addition)

```python
# Layer 11 Governance override
if patch_modifies_architecture_level:
    require_human_approval()
if patch_modifies_constitution:
    require_brain_consensus()
if patch_attempts_self_replicate:
    trigger_kill_chain()
```

---

## Files Downloaded

| File | Purpose |
|------|---------|
| `README.md` | Project overview |
| `program.md` | Constitution/context for agent |
| `analysis.ipynb` | Experiment tracking |
| `results.tsv` | Result database |
| `nanochat/` | Training code |

---

## Next Steps

1. Study `nanochat/` implementation
2. Adapt dari "nanochat training" → "general code improvement"
3. Integrate ke HERMES brain sebagai "self-improvement skill"
4. Pair dengan ECC harness untuk agent lifecycle
5. Pair dengan agentshield untuk security audit tiap patch

---

*"This is a proof-of-concept that recursive self-improvement works. MAGNATRIX will scale it to 15 layers."*
