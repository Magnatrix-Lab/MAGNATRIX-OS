#!/usr/bin/env python3
"""
Self Improvement Loop — Orchestrator
Layer 13.5 — Self Improvement

Main loop: hunt → extract → generate → test → commit → push → log.
Pure Python stdlib.  Intended to run as a cron job or daemon.
"""

import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# ---------------------------------------------------------------------------
# Local imports (expect sibling files)
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from repo_hunter_native import RepoHunter, SearchQuery
from pattern_extractor_native import PatternExtractor
from native_generator_native import NativeGenerator

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CONFIG: Dict[str, Any] = {
    "queries": [
        {
            "keywords": ["python", "architecture"],
            "language": "python",
            "min_stars": 500,
            "topics": ["design-patterns"],
            "sort": "stars",
            "max_results": 5,
        },
        {
            "keywords": ["async", "framework"],
            "language": "python",
            "min_stars": 300,
            "topics": ["asyncio"],
            "sort": "updated",
            "max_results": 3,
        },
        {
            "keywords": ["event", "sourcing"],
            "language": "python",
            "min_stars": 200,
            "sort": "stars",
            "max_results": 3,
        },
    ],
    "max_repos_per_run": 8,
    "max_py_files_per_repo": 15,
    "test_cmd": [sys.executable, "-m", "py_compile"],
    "git_remote": "origin",
    "git_branch": "main",
    "commit_message_template": "[auto-repo-hunter] {module_name} from {repo} (layer {layer})",
    "log_file": os.path.join(_SCRIPT_DIR, "self_improvement_log.jsonl"),
    "patterns_dir": os.path.join(_SCRIPT_DIR, "generated_patterns"),
    "sleep_between_repos": 2,
}

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
class LoopLogger:
    """Append-only JSONL logger for every loop iteration."""

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)

    def log(self, record: Dict[str, Any]) -> None:
        record["_ts"] = datetime.now(timezone.utc).isoformat()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

# ---------------------------------------------------------------------------
# Pipeline Steps
# ---------------------------------------------------------------------------
class SelfImprovementLoop:
    """Orchestrates the full hunt-extract-generate-test-commit pipeline."""

    def __init__(self, config: Dict[str, Any] = None):
        self.cfg = config or CONFIG
        self.logger = LoopLogger(self.cfg["log_file"])
        self.hunter = RepoHunter()
        self.extractor = PatternExtractor()
        os.makedirs(self.cfg["patterns_dir"], exist_ok=True)

    def _run_test(self, file_path: str) -> Dict[str, Any]:
        """Compile-check a generated Python file."""
        cmd = self.cfg["test_cmd"] + [file_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return {
                "passed": result.returncode == 0,
                "stdout": result.stdout[:500],
                "stderr": result.stderr[:500],
                "returncode": result.returncode,
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _git_commit(self, file_path: str, message: str) -> bool:
        """Stage and commit a single file."""
        try:
            subprocess.run(["git", "add", file_path], check=True, capture_output=True, timeout=30)
            subprocess.run(["git", "commit", "-m", message], check=True, capture_output=True, timeout=30)
            return True
        except subprocess.CalledProcessError as e:
            # Nothing to commit or other git issue
            self.logger.log({"event": "git_commit_skipped", "path": file_path, "stderr": e.stderr.decode()[:200] if e.stderr else ""})
            return False
        except Exception as e:
            self.logger.log({"event": "git_commit_error", "path": file_path, "error": str(e)})
            return False

    def _git_push(self) -> bool:
        """Push current branch to configured remote."""
        try:
            subprocess.run(
                ["git", "push", self.cfg["git_remote"], self.cfg["git_branch"]],
                check=True, capture_output=True, timeout=60,
            )
            return True
        except Exception as e:
            self.logger.log({"event": "git_push_error", "error": str(e)})
            return False

    def _process_repo(self, repo) -> Dict[str, Any]:
        """Run full pipeline on a single RepoResult."""
        record: Dict[str, Any] = {
            "event": "repo_pipeline",
            "repo": repo.full_name,
            "url": repo.html_url,
        }

        # 1. Extract
        try:
            summary = self.extractor.extract(
                repo_full_name=repo.full_name,
                repo_url=repo.html_url,
                max_py_files=self.cfg["max_py_files_per_repo"],
            )
            pattern_path = self.extractor.save(summary, self.cfg["patterns_dir"])
            record["pattern_file"] = pattern_path
            record["patterns_found"] = len(summary.patterns)
        except Exception as e:
            record["stage"] = "extract"
            record["status"] = "failed"
            record["error"] = traceback.format_exc()
            self.logger.log(record)
            return record

        # 2. Generate
        try:
            gen = NativeGenerator(pattern_path)
            out_path, mod_name = gen.generate()
            record["generated_file"] = out_path
            record["module_name"] = mod_name
            record["layer"] = gen._classify_layer()[0]
        except Exception as e:
            record["stage"] = "generate"
            record["status"] = "failed"
            record["error"] = traceback.format_exc()
            self.logger.log(record)
            return record

        # 3. Test
        test_result = self._run_test(out_path)
        record["test"] = test_result
        if not test_result["passed"]:
            record["stage"] = "test"
            record["status"] = "failed"
            self.logger.log(record)
            return record

        # 4. Commit
        commit_msg = self.cfg["commit_message_template"].format(
            module_name=mod_name, repo=repo.full_name, layer=record.get("layer", "unknown"),
        )
        committed = self._git_commit(out_path, commit_msg)
        record["committed"] = committed

        # 5. (Push is done once per run, not per repo)
        record["stage"] = "complete"
        record["status"] = "success"
        self.logger.log(record)
        return record

    def run(self) -> List[Dict[str, Any]]:
        """
        Execute one full loop iteration.
        Returns list of result records.
        """
        start_ts = datetime.now(timezone.utc).isoformat()
        self.logger.log({"event": "loop_start", "start": start_ts})

        # --- HUNT ---
        discovered: List[Any] = []
        for qdict in self.cfg["queries"]:
            query = SearchQuery(
                keywords=qdict.get("keywords", []),
                language=qdict.get("language"),
                min_stars=qdict.get("min_stars"),
                topics=qdict.get("topics", []),
                sort=qdict.get("sort", "stars"),
            )
            batch = self.hunter.search(query, max_results=qdict.get("max_results", 5))
            discovered.extend(batch)
            time.sleep(1)

        # Deduplicate by full_name, sort by relevance
        seen: set = set()
        unique: List[Any] = []
        for r in sorted(discovered, key=lambda x: -x.relevance_score):
            if r.full_name not in seen:
                seen.add(r.full_name)
                unique.append(r)

        repos_to_process = unique[: self.cfg["max_repos_per_run"]]
        self.logger.log({"event": "hunt_complete", "found": len(unique), "processing": len(repos_to_process)})

        # --- EXTRACT → GENERATE → TEST → COMMIT ---
        results: List[Dict[str, Any]] = []
        for repo in repos_to_process:
            result = self._process_repo(repo)
            results.append(result)
            time.sleep(self.cfg.get("sleep_between_repos", 2))

        # --- PUSH ---
        pushed = self._git_push()
        self.logger.log({"event": "loop_end", "pushed": pushed, "results_count": len(results)})

        return results

    def report(self, results: List[Dict[str, Any]]) -> str:
        """Human-readable summary of last run."""
        lines = [
            "=== Self Improvement Loop Report ===",
            f"Run time: {datetime.now(timezone.utc).isoformat()}",
            f"Repos processed: {len(results)}",
            "",
        ]
        success = sum(1 for r in results if r.get("status") == "success")
        failed = len(results) - success
        lines.append(f"Success: {success} | Failed: {failed}")
        lines.append("")
        for r in results:
            emoji = "✅" if r.get("status") == "success" else "❌"
            lines.append(f"{emoji} {r['repo']} — {r.get('stage', '?')} — layer {r.get('layer', '?')}")
            if r.get("generated_file"):
                lines.append(f"   → {r['generated_file']}")
        return "\n".join(lines)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: List[str] = None) -> int:
    """Entry point for cron / manual invocation."""
    argv = argv or sys.argv[1:]
    loop = SelfImprovementLoop()

    # Optional: load custom config JSON
    if argv and argv[0].endswith(".json") and os.path.exists(argv[0]):
        with open(argv[0], "r", encoding="utf-8") as f:
            loop.cfg = json.load(f)
        print(f"[loop] loaded config from {argv[0]}")

    print("[loop] starting self-improvement iteration…")
    results = loop.run()
    print(loop.report(results))
    return 0 if all(r.get("status") == "success" for r in results) else 1

if __name__ == "__main__":
    sys.exit(main())
