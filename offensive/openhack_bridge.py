#!/usr/bin/env python3
"""
openhack_bridge.py — MAGNATRIX OpenHack Integration Bridge
Adaptasi metodologi Hadrian OpenHack (github.com/hadriansecurity/OpenHack)
ke dalam MAGNATRIX Layer 13 (Offensive Security).

OpenHack adalah whitebox security review framework dengan workflow:
  init-run → recon → create-scenarios → record-backlog → 
  scenario-loop → finding-candidates → triage-loop → findings

Bridge ini memungkinkan MAGNATRIX untuk:
  1. Menjalankan full OpenHack workflow via CLI wrapper
  2. Integrasi hasil ke Knowledge Graph (Layer 5)
  3. Broadcast findings ke Mesh Messaging (Layer 4)
  4. Trigger guardian jika critical finding detected
  5. Auto-triage dengan LLM via FreeLLM Router (Layer 1.5)

12 Expert families (OWASP/MITRE 2025):
  A01 broken-access-control
  A02 security-misconfiguration
  A03 software-supply-chain-failures
  A04 cryptographic-failures
  A05 injection
  CWE-119 memory-buffer-boundary-errors
  A06 insecure-design
  A07 authentication-failures
  A08 software-data-integrity-failures
  CWE-200 sensitive-information-exposure
  CWE-22/434 path-traversal-unrestricted-upload
  API4/CWE-770 unrestricted-resource-consumption
"""

import json
import os
import re
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


class OpenHackBridge:
    """Bridge antara MAGNATRIX dan OpenHack CLI workflow."""

    # 12 OWASP/MITRE expert families
    EXPERT_FAMILIES: Dict[str, Dict[str, str]] = {
        "broken-access-control": {
            "id": "A01",
            "title": "Broken Access Control",
            "category": "OWASP Top 10 2025",
            "signals": ["route", "auth_boundary", "admin_area", "ssrf"],
        },
        "security-misconfiguration": {
            "id": "A02",
            "title": "Security Misconfiguration",
            "category": "OWASP Top 10 2025",
            "signals": ["manifest", "config", "debug_endpoint", "default_cred"],
        },
        "software-supply-chain-failures": {
            "id": "A03",
            "title": "Software Supply Chain Failures",
            "category": "OWASP Top 10 2025",
            "signals": ["dependency", "package", "vendor", "build_pipeline"],
        },
        "cryptographic-failures": {
            "id": "A04",
            "title": "Cryptographic Failures",
            "category": "OWASP Top 10 2025",
            "signals": ["crypto", "hash", "random", "tls", "key_management"],
        },
        "injection": {
            "id": "A05",
            "title": "Injection",
            "category": "OWASP Top 10 2025",
            "signals": ["sql", "nosql", "command", "ldap", "xpath", "template"],
        },
        "memory-buffer-boundary-errors": {
            "id": "CWE-119",
            "title": "Memory Buffer Boundary Errors",
            "category": "CWE",
            "signals": ["buffer", "overflow", "underflow", "heap", "stack"],
        },
        "insecure-design": {
            "id": "A06",
            "title": "Insecure Design",
            "category": "OWASP Top 10 2025",
            "signals": ["design_flaw", "business_logic", "race_condition"],
        },
        "authentication-failures": {
            "id": "A07",
            "title": "Authentication Failures",
            "category": "OWASP Top 10 2025",
            "signals": ["auth", "session", "jwt", "oauth", "mfa", "brute_force"],
        },
        "software-data-integrity-failures": {
            "id": "A08",
            "title": "Software/Data Integrity Failures",
            "category": "OWASP Top 10 2025",
            "signals": ["deserialization", "integrity", "upload", "update"],
        },
        "sensitive-information-exposure": {
            "id": "CWE-200",
            "title": "Sensitive Information Exposure",
            "category": "CWE",
            "signals": ["leak", "debug_info", "error_message", "log"],
        },
        "path-traversal-unrestricted-upload": {
            "id": "CWE-22/434",
            "title": "Path Traversal / Unrestricted Upload",
            "category": "CWE",
            "signals": ["path_traversal", "upload", "file_write", "zip_slip"],
        },
        "unrestricted-resource-consumption": {
            "id": "API4/CWE-770",
            "title": "Unrestricted Resource Consumption",
            "category": "API/CWE",
            "signals": ["dos", "rate_limit", "memory", "cpu", "disk"],
        },
    }

    SEVERITY_WEIGHTS = {
        "critical": 10,
        "high": 7,
        "medium": 4,
        "low": 2,
        "info": 1,
    }

    def __init__(
        self,
        openhack_root: Optional[str] = None,
        magnatrix_root: str = "/mnt/agents/MAGNATRIX-OS",
        runs_dir: str = "runs",
    ):
        self.openhack_root = openhack_root or os.environ.get("OPENHACK_ROOT", "/opt/openhack")
        self.magnatrix_root = magnatrix_root
        self.runs_dir = Path(magnatrix_root) / "offensive" / runs_dir
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._load_existing_runs()

    # ------------------------------------------------------------------
    # Run Lifecycle
    # ------------------------------------------------------------------
    def init_run(self, target: str, git_url: str, run_id: Optional[str] = None, branch: Optional[str] = None) -> Dict[str, Any]:
        """Initialize new OpenHack run. Clone target, setup workspace."""
        run_id = run_id or f"{target}-{uuid.uuid4().hex[:8]}"
        run_path = self.runs_dir / target / run_id
        run_path.mkdir(parents=True, exist_ok=True)

        # Create run structure
        (run_path / "sourcecode").mkdir(exist_ok=True)
        (run_path / "recon-output").mkdir(exist_ok=True)
        (run_path / "scenarios" / "backlog").mkdir(parents=True, exist_ok=True)
        (run_path / "scenarios" / "finished").mkdir(parents=True, exist_ok=True)
        (run_path / "finding-candidates").mkdir(exist_ok=True)
        (run_path / "finding-triage" / "prompts").mkdir(parents=True, exist_ok=True)
        (run_path / "finding-triage" / "decisions").mkdir(parents=True, exist_ok=True)
        (run_path / "findings").mkdir(exist_ok=True)
        (run_path / "logs").mkdir(exist_ok=True)

        # Clone source
        clone_cmd = ["git", "clone", "--depth", "1"]
        if branch:
            clone_cmd.extend(["--branch", branch])
        clone_cmd.extend([git_url, str(run_path / "sourcecode")])

        try:
            subprocess.run(clone_cmd, capture_output=True, text=True, timeout=120)
        except Exception as e:
            return {"status": "error", "phase": "clone", "error": str(e)}

        # Write run-config.yaml
        config = {
            "target": target,
            "git_url": git_url,
            "run_id": run_id,
            "branch": branch or "main",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expert_scope": list(self.EXPERT_FAMILIES.keys()),
            "status": "initialized",
        }
        (run_path / "run-config.yaml").write_text(
            json.dumps(config, indent=2, default=str), encoding="utf-8"
        )

        # Write run-state.jsonl first event
        self._append_state(run_path, {"event": "initialized", "timestamp": time.time()})

        self._runs[run_id] = {"target": target, "path": str(run_path), "config": config}

        return {
            "status": "initialized",
            "run_id": run_id,
            "target": target,
            "path": str(run_path),
            "next_command": f"run_recon('{target}', '{run_id}')",
        }

    def run_recon(self, target: str, run_id: str, experts: Optional[List[str]] = None, semgrep: bool = False) -> Dict[str, Any]:
        """Run source reconnaissance."""
        run_path = self.runs_dir / target / run_id
        if not run_path.exists():
            return {"status": "error", "error": f"Run {run_id} not found"}

        scope = experts or list(self.EXPERT_FAMILIES.keys())
        sourcecode = run_path / "sourcecode"

        # Run recon scripts
        recon_results = {
            "routes": self._discover_routes(sourcecode),
            "inputs": self._discover_inputs(sourcecode),
            "sinks": self._discover_sinks(sourcecode),
            "auth_boundaries": self._discover_auth_boundaries(sourcecode),
            "exposures": self._discover_exposures(sourcecode),
            "dependencies": self._scan_dependencies(sourcecode),
        }

        # Write recon output
        recon_output = run_path / "recon-output"
        for name, data in recon_results.items():
            (recon_output / f"{name}.jsonl").write_text(
                "\n".join(json.dumps(item, default=str) for item in data), encoding="utf-8"
            )

        # Generate routing units
        routing_units = self._cluster_routing_units(recon_results)
        (recon_output / "routing-units.jsonl").write_text(
            "\n".join(json.dumps(u, default=str) for u in routing_units), encoding="utf-8"
        )

        # Coverage gaps
        coverage_gaps = self._identify_coverage_gaps(routing_units, scope)
        (recon_output / "coverage-gaps.json").write_text(
            json.dumps(coverage_gaps, indent=2, default=str), encoding="utf-8"
        )

        # Semgrep enrichment (optional)
        if semgrep:
            semgrep_results = self._run_semgrep(sourcecode)
            (recon_output / "semgrep-results.json").write_text(
                json.dumps(semgrep_results, indent=2, default=str), encoding="utf-8"
            )

        # Update state
        self._append_state(run_path, {"event": "recon_complete", "timestamp": time.time(), "routing_units": len(routing_units)})
        self._update_config(run_path, {"status": "recon_complete", "routing_units_count": len(routing_units)})

        return {
            "status": "recon_complete",
            "run_id": run_id,
            "routing_units": len(routing_units),
            "coverage_gaps": len(coverage_gaps),
            "next_command": f"create_scenarios('{target}', '{run_id}')",
        }

    def create_scenarios(self, target: str, run_id: str) -> Dict[str, Any]:
        """Generate scenario router prompt from routing units."""
        run_path = self.runs_dir / target / run_id
        recon_output = run_path / "recon-output"

        # Load routing units
        units_file = recon_output / "routing-units.jsonl"
        if not units_file.exists():
            return {"status": "error", "error": "No routing units found. Run recon first."}

        routing_units = [json.loads(line) for line in units_file.read_text().strip().split("\n") if line.strip()]

        # Build router prompt
        prompt = self._build_router_prompt(routing_units, run_path)
        scenarios_dir = run_path / "scenarios"
        (scenarios_dir / "scenario-router-prompt.md").write_text(prompt, encoding="utf-8")

        self._append_state(run_path, {"event": "scenario_router_prompt_ready", "timestamp": time.time()})

        return {
            "status": "router_prompt_ready",
            "run_id": run_id,
            "routing_units": len(routing_units),
            "prompt_path": str(scenarios_dir / "scenario-router-prompt.md"),
            "next_command": f"record_scenario_backlog('{target}', '{run_id}', router_result_json)",
        }

    def record_scenario_backlog(self, target: str, run_id: str, router_result: Dict[str, Any]) -> Dict[str, Any]:
        """Materialize router's selected backlog into scenarios."""
        run_path = self.runs_dir / target / run_id
        scenarios_dir = run_path / "scenarios"
        backlog_dir = scenarios_dir / "backlog"

        scenarios = router_result.get("scenarios", [])
        coverage_decisions = router_result.get("coverage_decisions", [])

        # Write index
        index = [{"scenario_id": s["id"], "expert": s["expert"], "routing_unit_id": s.get("routing_unit_id")} for s in scenarios]
        (scenarios_dir / "index.jsonl").write_text(
            "\n".join(json.dumps(i) for i in index), encoding="utf-8"
        )

        # Write individual scenario files
        for s in scenarios:
            sid = s["id"]
            (backlog_dir / f"{sid}.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
            # Render prompt
            prompt = self._render_scenario_prompt(s, run_path)
            (backlog_dir / f"{sid}.md").write_text(prompt, encoding="utf-8")

        # Write coverage decisions
        (scenarios_dir / "coverage-decisions.json").write_text(
            json.dumps(coverage_decisions, indent=2), encoding="utf-8"
        )

        self._append_state(run_path, {"event": "backlog_recorded", "timestamp": time.time(), "scenarios": len(scenarios)})
        self._update_config(run_path, {"status": "backlog_recorded", "scenarios_count": len(scenarios)})

        return {
            "status": "backlog_recorded",
            "run_id": run_id,
            "scenarios": len(scenarios),
            "next_command": f"run_scenario_loop('{target}', '{run_id}')",
        }

    def record_scenario_result(self, target: str, run_id: str, scenario_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Record expert result and materialize finding candidates."""
        run_path = self.runs_dir / target / run_id
        finished_dir = run_path / "scenarios" / "finished"
        candidates_dir = run_path / "finding-candidates"

        # Write finished scenario
        finished = {
            "scenario_id": scenario_id,
            "result": result,
            "timestamp": time.time(),
        }
        (finished_dir / f"{scenario_id}.json").write_text(json.dumps(finished, indent=2, default=str), encoding="utf-8")

        # Materialize finding candidates
        findings = result.get("findings", [])
        candidates = []
        for i, f in enumerate(findings):
            candidate_id = f"{scenario_id}-F{i+1:03d}"
            candidate = {
                "id": candidate_id,
                "scenario_id": scenario_id,
                "title": f.get("title", "Unknown"),
                "description": f.get("description", ""),
                "severity": f.get("severity", "medium"),
                "evidence": f.get("evidence", []),
                "status": "pending_triage",
                "timestamp": time.time(),
            }
            (candidates_dir / f"{candidate_id}.json").write_text(
                json.dumps(candidate, indent=2, default=str), encoding="utf-8"
            )
            candidates.append(candidate)

        self._append_state(run_path, {
            "event": "scenario_result_recorded",
            "scenario_id": scenario_id,
            "findings": len(findings),
            "candidates": len(candidates),
        })

        return {
            "status": "recorded",
            "scenario_id": scenario_id,
            "candidates_created": len(candidates),
            "next_command": f"run_triage_loop('{target}', '{run_id}')" if candidates else "continue_scenario_loop",
        }

    def record_finding_triage(self, target: str, run_id: str, candidate_id: str, triage_result: Dict[str, Any]) -> Dict[str, Any]:
        """Record triage decision. Accepted/downgraded → materialize finding."""
        run_path = self.runs_dir / target / run_id
        decisions_dir = run_path / "finding-triage" / "decisions"
        findings_dir = run_path / "findings"

        decision = {
            "candidate_id": candidate_id,
            "decision": triage_result.get("decision", "rejected"),
            "reason": triage_result.get("reason", ""),
            "confidence": triage_result.get("confidence", 0.0),
            "severity_override": triage_result.get("severity_override"),
            "timestamp": time.time(),
        }
        (decisions_dir / f"{candidate_id}.json").write_text(
            json.dumps(decision, indent=2, default=str), encoding="utf-8"
        )

        # Materialize finding if accepted or downgraded
        if decision["decision"] in ("accepted", "downgraded"):
            candidate_file = run_path / "finding-candidates" / f"{candidate_id}.json"
            if candidate_file.exists():
                candidate = json.loads(candidate_file.read_text())
                finding = {
                    "id": candidate_id,
                    "title": candidate["title"],
                    "description": candidate["description"],
                    "severity": decision.get("severity_override") or candidate["severity"],
                    "evidence": candidate["evidence"],
                    "triage_confidence": decision["confidence"],
                    "status": decision["decision"],
                    "timestamp": time.time(),
                }
                (findings_dir / f"{candidate_id}.md").write_text(
                    self._render_finding_md(finding), encoding="utf-8"
                )

        self._append_state(run_path, {
            "event": "triage_recorded",
            "candidate_id": candidate_id,
            "decision": decision["decision"],
        })

        return {
            "status": "triage_recorded",
            "candidate_id": candidate_id,
            "decision": decision["decision"],
        }

    def summarize_run(self, target: str, run_id: str) -> Dict[str, Any]:
        """Print counts + next checkpoint. Resume-friendly."""
        run_path = self.runs_dir / target / run_id
        if not run_path.exists():
            return {"status": "error", "error": f"Run {run_id} not found"}

        # Count artifacts
        scenarios_backlog = list((run_path / "scenarios" / "backlog").glob("S*.json")) if (run_path / "scenarios" / "backlog").exists() else []
        scenarios_finished = list((run_path / "scenarios" / "finished").glob("S*.json")) if (run_path / "scenarios" / "finished").exists() else []
        candidates = list((run_path / "finding-candidates").glob("*.json")) if (run_path / "finding-candidates").exists() else []
        triage_decisions = list((run_path / "finding-triage" / "decisions").glob("*.json")) if (run_path / "finding-triage" / "decisions").exists() else []
        findings = list((run_path / "findings").glob("*.md")) if (run_path / "findings").exists() else []

        # Determine next checkpoint
        next_checkpoint = "Unknown"
        if not scenarios_backlog:
            next_checkpoint = "create_scenarios() → record_scenario_backlog()"
        elif len(scenarios_finished) < len(scenarios_backlog):
            next_checkpoint = f"run_scenario_loop() — {len(scenarios_backlog) - len(scenarios_finished)} remaining"
        elif len(triage_decisions) < len(candidates):
            next_checkpoint = f"run_triage_loop() — {len(candidates) - len(triage_decisions)} remaining"
        else:
            next_checkpoint = "validate_run()"

        return {
            "status": "summary",
            "run_id": run_id,
            "target": target,
            "counts": {
                "scenarios_backlog": len(scenarios_backlog),
                "scenarios_finished": len(scenarios_finished),
                "candidates": len(candidates),
                "triage_decisions": len(triage_decisions),
                "findings": len(findings),
            },
            "next_checkpoint": next_checkpoint,
            "path": str(run_path),
        }

    def validate_run(self, target: str, run_id: str) -> Dict[str, Any]:
        """Validate schema, coverage, and integrity."""
        run_path = self.runs_dir / target / run_id
        errors = []
        warnings = []

        # Check required directories
        for subdir in ["sourcecode", "recon-output", "scenarios/backlog", "findings"]:
            if not (run_path / subdir).exists():
                errors.append(f"Missing directory: {subdir}")

        # Check config
        config_file = run_path / "run-config.yaml"
        if not config_file.exists():
            errors.append("Missing run-config.yaml")
        else:
            try:
                config = json.loads(config_file.read_text())
                if config.get("status") == "initialized" and (run_path / "recon-output" / "routing-units.jsonl").exists():
                    warnings.append("Status is 'initialized' but recon output exists")
            except Exception as e:
                errors.append(f"Invalid config: {e}")

        # Check orphaned candidates
        candidates = list((run_path / "finding-candidates").glob("*.json")) if (run_path / "finding-candidates").exists() else []
        triage_decisions = list((run_path / "finding-triage" / "decisions").glob("*.json")) if (run_path / "finding-triage" / "decisions").exists() else []
        candidate_ids = {p.stem for p in candidates}
        triaged_ids = {p.stem for p in triage_decisions}
        orphaned = candidate_ids - triaged_ids
        if orphaned:
            warnings.append(f"{len(orphaned)} candidate(s) without triage decision")

        # Check findings materialization
        findings = list((run_path / "findings").glob("*.md")) if (run_path / "findings").exists() else []
        accepted_decisions = []
        for d in triage_decisions:
            data = json.loads(d.read_text())
            if data.get("decision") in ("accepted", "downgraded"):
                accepted_decisions.append(d.stem)
        missing_findings = set(accepted_decisions) - {p.stem for p in findings}
        if missing_findings:
            warnings.append(f"{len(missing_findings)} accepted decision(s) without finding markdown")

        return {
            "status": "valid" if not errors else "invalid",
            "errors": errors,
            "warnings": warnings,
            "run_id": run_id,
        }

    # ------------------------------------------------------------------
    # MAGNATRIX Integration
    # ------------------------------------------------------------------
    def export_findings_to_knowledge(self, target: str, run_id: str) -> List[Dict[str, Any]]:
        """Export findings ke MAGNATRIX Knowledge Graph format."""
        run_path = self.runs_dir / target / run_id
        findings_dir = run_path / "findings"
        if not findings_dir.exists():
            return []

        exported = []
        for finding_file in findings_dir.glob("*.md"):
            # Parse markdown to extract JSON frontmatter or metadata
            text = finding_file.read_text(encoding="utf-8")
            # Extract title and severity from markdown
            title_match = re.search(r"#\s+(.+)", text)
            severity_match = re.search(r"Severity:\s*([^\n]+)", text, re.I)

            entity = {
                "type": "security_finding",
                "name": title_match.group(1) if title_match else finding_file.stem,
                "severity": severity_match.group(1).strip() if severity_match else "unknown",
                "source": f"openhack:{target}:{run_id}",
                "file_path": str(finding_file),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            exported.append(entity)
        return exported

    def get_critical_findings(self, target: str, run_id: str) -> List[Dict[str, Any]]:
        """Ambil findings dengan severity critical/high."""
        run_path = self.runs_dir / target / run_id
        findings_dir = run_path / "findings"
        if not findings_dir.exists():
            return []

        critical = []
        for f in findings_dir.glob("*.md"):
            text = f.read_text()
            if re.search(r"Severity:\s*(critical|high)", text, re.I):
                critical.append({"file": f.name, "path": str(f)})
        return critical

    def to_mesh_payload(self, target: str, run_id: str) -> Dict[str, Any]:
        """Generate mesh broadcast payload untuk swarm."""
        summary = self.summarize_run(target, run_id)
        critical = self.get_critical_findings(target, run_id)
        return {
            "msg_type": "SECURITY_AUDIT_COMPLETE",
            "run_id": run_id,
            "target": target,
            "summary": summary.get("counts", {}),
            "critical_findings_count": len(critical),
            "critical_findings": critical,
            "timestamp": time.time(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_existing_runs(self) -> None:
        """Load runs yang sudah ada di disk."""
        if not self.runs_dir.exists():
            return
        for target_dir in self.runs_dir.iterdir():
            if not target_dir.is_dir():
                continue
            for run_dir in target_dir.iterdir():
                if not run_dir.is_dir():
                    continue
                config_file = run_dir / "run-config.yaml"
                if config_file.exists():
                    try:
                        config = json.loads(config_file.read_text())
                        self._runs[run_dir.name] = {
                            "target": target_dir.name,
                            "path": str(run_dir),
                            "config": config,
                        }
                    except Exception:
                        pass

    def _append_state(self, run_path: Path, event: Dict[str, Any]) -> None:
        state_file = run_path / "run-state.jsonl"
        with state_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

    def _update_config(self, run_path: Path, updates: Dict[str, Any]) -> None:
        config_file = run_path / "run-config.yaml"
        if config_file.exists():
            config = json.loads(config_file.read_text())
            config.update(updates)
            config_file.write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")

    def _discover_routes(self, sourcecode: Path) -> List[Dict[str, Any]]:
        """Discover HTTP routes, API endpoints, GraphQL."""
        routes = []
        for pattern in ["**/*.py", "**/*.js", "**/*.ts", "**/*.go", "**/*.rb", "**/*.php"]:
            for f in sourcecode.rglob(pattern.replace("**/*.", "")):
                if pattern.endswith(".py"):
                    routes.extend(self._extract_python_routes(f))
                elif pattern.endswith(".js") or pattern.endswith(".ts"):
                    routes.extend(self._extract_js_routes(f))
        return routes

    def _extract_python_routes(self, f: Path) -> List[Dict[str, Any]]:
        routes = []
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            # Flask/FastAPI/Django route patterns
            for match in re.finditer(r'@(?:app|router|blueprint)\.route\(["\']([^"\']+)["\']', text):
                routes.append({"type": "http_route", "path": match.group(1), "file": str(f)})
            for match in re.finditer(r'(?:get|post|put|delete|patch)\(["\']([^"\']+)["\']', text):
                routes.append({"type": "http_route", "path": match.group(1), "file": str(f)})
        except Exception:
            pass
        return routes

    def _extract_js_routes(self, f: Path) -> List[Dict[str, Any]]:
        routes = []
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            for match in re.finditer(r'(?:app|router)\.(?:get|post|put|delete|patch)\(["\']([^"\']+)["\']', text):
                routes.append({"type": "http_route", "path": match.group(1), "file": str(f)})
        except Exception:
            pass
        return routes

    def _discover_inputs(self, sourcecode: Path) -> List[Dict[str, Any]]:
        """Discover user input points."""
        inputs = []
        for f in sourcecode.rglob("*"):
            if f.is_file() and f.stat().st_size < 1024 * 1024:  # skip >1MB
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    # Common input patterns
                    patterns = [
                        (r'request\.(?:args|form|json|files|headers|cookies)', "framework_input"),
                        (r'input\(', "user_input"),
                        (r'stdin|Scanner|BufferedReader', "stream_input"),
                        (r'process\.env', "env_input"),
                    ]
                    for pat, inp_type in patterns:
                        if re.search(pat, text):
                            inputs.append({"type": inp_type, "file": str(f), "pattern": pat})
                            break
                except Exception:
                    pass
        return inputs[:500]  # limit

    def _discover_sinks(self, sourcecode: Path) -> List[Dict[str, Any]]:
        """Discover dangerous sinks."""
        sinks = []
        sink_patterns = [
            (r'(?:exec|eval|system|subprocess\.call|os\.system)\s*\(', "command_execution"),
            (r'(?:query|execute|raw|cursor\.execute)\s*\(', "sql_execution"),
            (r'(?:render_template|render|redirect|url_for).*\+', "template_render"),
            (r'(?:fs\.readFile|readFileSync|open\()', "file_operation"),
            (r'(?:innerHTML|outerHTML|document\.write)', "dom_xss"),
        ]
        for f in sourcecode.rglob("*"):
            if f.is_file() and f.stat().st_size < 1024 * 1024:
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    for pat, sink_type in sink_patterns:
                        if re.search(pat, text):
                            sinks.append({"type": sink_type, "file": str(f), "pattern": pat})
                            break
                except Exception:
                    pass
        return sinks[:500]

    def _discover_auth_boundaries(self, sourcecode: Path) -> List[Dict[str, Any]]:
        """Discover auth boundaries and access control."""
        boundaries = []
        auth_patterns = [
            (r'(?:login|auth|authenticate|verify|check_perm|require_auth)', "auth_check"),
            (r'(?:@login_required|@authenticated|@protected)', "auth_decorator"),
            (r'(?:admin|superuser|staff|moderator)', "admin_area"),
            (r'(?:csrf|csrf_token|csrf_exempt)', "csrf_protection"),
        ]
        for f in sourcecode.rglob("*"):
            if f.is_file() and f.stat().st_size < 1024 * 1024:
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    for pat, boundary_type in auth_patterns:
                        if re.search(pat, text, re.I):
                            boundaries.append({"type": boundary_type, "file": str(f)})
                            break
                except Exception:
                    pass
        return boundaries[:500]

    def _discover_exposures(self, sourcecode: Path) -> List[Dict[str, Any]]:
        """Discover exposed sensitive data."""
        exposures = []
        exposure_patterns = [
            (r'(?:password|secret|token|key)\s*=\s*["\'][^"\']+["\']', "hardcoded_secret"),
            (r'(?:TODO|FIXME|HACK|BUG|XXX).*?(?:password|secret|auth)', "todo_secret"),
            (r'(?:\.env|config\.json|secrets\.yaml)', "config_file"),
            (r'(?:DEBUG|DEBUG_MODE|debug\s*=\s*True)', "debug_mode"),
        ]
        for f in sourcecode.rglob("*"):
            if f.is_file() and f.stat().st_size < 1024 * 1024:
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    for pat, exp_type in exposure_patterns:
                        if re.search(pat, text, re.I):
                            exposures.append({"type": exp_type, "file": str(f)})
                            break
                except Exception:
                    pass
        return exposures[:500]

    def _scan_dependencies(self, sourcecode: Path) -> List[Dict[str, Any]]:
        """Scan dependencies for known issues."""
        deps = []
        dep_files = [
            ("requirements.txt", r'^([a-zA-Z0-9_-]+)==([0-9.]+)'),
            ("package.json", r'"([@a-zA-Z0-9/_-]+)":\s*"([~^]?[0-9.]+)"'),
            ("Cargo.toml", r'^([a-zA-Z0-9_-]+)\s*=\s*"([0-9.]+)"'),
            ("go.mod", r'^\s*require\s+([a-zA-Z0-9./_-]+)\s+v?([0-9.]+)'),
        ]
        for filename, pattern in dep_files:
            for f in sourcecode.rglob(filename):
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    for match in re.finditer(pattern, text, re.M):
                        deps.append({
                            "type": filename,
                            "name": match.group(1),
                            "version": match.group(2),
                            "file": str(f),
                        })
                except Exception:
                    pass
        return deps

    def _cluster_routing_units(self, recon_results: Dict[str, List]) -> List[Dict[str, Any]]:
        """Cluster recon items into routing units."""
        units = []
        unit_id = 0

        # Group by file
        file_map: Dict[str, Dict[str, Any]] = {}
        for category, items in recon_results.items():
            for item in items:
                f = item.get("file", "unknown")
                if f not in file_map:
                    file_map[f] = {"file": f, "categories": set(), "items": []}
                file_map[f]["categories"].add(category)
                file_map[f]["items"].append(item)

        for f, data in file_map.items():
            unit_id += 1
            # Map to relevant expert families
            experts = set()
            for cat in data["categories"]:
                for expert_id, expert_info in self.EXPERT_FAMILIES.items():
                    if any(cat.replace("_", "").startswith(s.replace("_", "")) or s in cat for s in expert_info["signals"]):
                        experts.add(expert_id)

            units.append({
                "id": f"RU{unit_id:03d}",
                "file": f,
                "categories": list(data["categories"]),
                "item_count": len(data["items"]),
                "relevant_experts": list(experts),
                "signals": list(data["categories"]),
            })

        return units

    def _identify_coverage_gaps(self, routing_units: List[Dict], scope: List[str]) -> List[Dict[str, Any]]:
        """Identify which experts don't have routing units."""
        covered = set()
        for u in routing_units:
            covered.update(u.get("relevant_experts", []))

        gaps = []
        for expert in scope:
            if expert not in covered:
                gaps.append({
                    "expert": expert,
                    "reason": "No routing units mapped to this expert",
                    "suggestion": f"Re-run recon with --expert {expert} or broaden source scan",
                })
        return gaps

    def _run_semgrep(self, sourcecode: Path) -> List[Dict[str, Any]]:
        """Run Semgrep if available."""
        try:
            result = subprocess.run(
                ["semgrep", "--json", "--config=auto", str(sourcecode)],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode in (0, 1):  # 1 = findings
                data = json.loads(result.stdout)
                return data.get("results", [])
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
        return []

    def _build_router_prompt(self, routing_units: List[Dict], run_path: Path) -> str:
        """Build scenario router prompt."""
        lines = [
            "# Scenario Router Prompt",
            "",
            f"Target: {run_path.parent.name}",
            f"Run: {run_path.name}",
            f"Routing Units: {len(routing_units)}",
            "",
            "## Routing Units",
        ]
        for u in routing_units[:50]:  # limit to prevent huge prompts
            lines.append(f"### {u['id']} — {u['file']}")
            lines.append(f"- Categories: {', '.join(u['categories'])}")
            lines.append(f"- Relevant experts: {', '.join(u['relevant_experts'])}")
            lines.append("")

        lines.extend([
            "## Instructions",
            "Generate scenarios that cover the most important routing units.",
            "Each scenario maps one routing unit + one expert + one proof question.",
            "Output JSON with `scenarios` and `coverage_decisions` arrays.",
        ])
        return "\n".join(lines)

    def _render_scenario_prompt(self, scenario: Dict, run_path: Path) -> str:
        """Render expert scenario prompt."""
        expert_id = scenario.get("expert", "unknown")
        expert = self.EXPERT_FAMILIES.get(expert_id, {})
        return f"""# Scenario: {scenario.get('id', 'S000')}

## Expert: {expert.get('title', expert_id)}
Category: {expert.get('category', 'Unknown')}

## Routing Unit
{scenario.get('routing_unit_id', 'N/A')} — {scenario.get('file', 'N/A')}

## Proof Question
{scenario.get('proof_question', 'Is this surface vulnerable to the expert family?')}

## Instructions
1. Review the source code at the routing unit location.
2. Determine if the vulnerability family applies.
3. If yes: provide evidence, reproduction steps, and severity.
4. If no: explain why it's a false positive or not applicable.
5. Output JSON with `status` (verified/rejected/needs_context/candidate) and `findings` array.
"""

    def _render_finding_md(self, finding: Dict) -> str:
        """Render finding as markdown."""
        return f"""# {finding['title']}

**Severity:** {finding['severity']}
**Status:** {finding['status']}
**ID:** {finding['id']}
**Timestamp:** {datetime.fromtimestamp(finding['timestamp'], tz=timezone.utc).isoformat()}

## Description
{finding['description']}

## Evidence
{finding.get('evidence', [])}

## Triage Confidence
{finding.get('triage_confidence', 'N/A')}
"""


# ===================================================================
# Demo
# ===================================================================
if __name__ == "__main__":
    import tempfile

    print("=" * 60)
    print("MAGNATRIX OpenHack Bridge")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        bridge = OpenHackBridge(magnatrix_root=tmpdir)

        print("\n[1] Expert families:")
        for eid, info in bridge.EXPERT_FAMILIES.items():
            print(f"  • {eid:40s} — {info['id']:12s} {info['title']}")

        print("\n[2] Init run demo:")
        # Create dummy sourcecode
        src = Path(tmpdir) / "offensive" / "runs" / "demo" / "demo-001" / "sourcecode"
        src.mkdir(parents=True, exist_ok=True)
        (src / "app.py").write_text("""
from flask import Flask, request, render_template_string
import os

app = Flask(__name__)

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    query = f"SELECT * FROM users WHERE username='{username}'"
    return render_template_string(f"<h1>Hello {username}</h1>")

@app.route('/admin')
def admin():
    return "Admin panel"
""")
        (src / "requirements.txt").write_text("flask==2.0.1\nsqlalchemy==1.4.0\n")

        result = bridge.init_run("demo", "https://github.com/demo/app.git", run_id="demo-001")
        print(f"  Status: {result['status']}")
        print(f"  Run ID: {result['run_id']}")

        print("\n[3] Run recon:")
        recon = bridge.run_recon("demo", "demo-001")
        print(f"  Status: {recon['status']}")
        print(f"  Routing units: {recon['routing_units']}")
        print(f"  Coverage gaps: {recon['coverage_gaps']}")

        print("\n[4] Create scenarios:")
        scenarios = bridge.create_scenarios("demo", "demo-001")
        print(f"  Status: {scenarios['status']}")

        print("\n[5] Simulate router result + record backlog:")
        router_result = {
            "scenarios": [
                {"id": "S001", "expert": "injection", "routing_unit_id": "RU001", "file": "app.py", "proof_question": "Is login() vulnerable to SQL injection?"},
                {"id": "S002", "expert": "broken-access-control", "routing_unit_id": "RU002", "file": "app.py", "proof_question": "Is /admin protected by authentication?"},
                {"id": "S003", "expert": "sensitive-information-exposure", "routing_unit_id": "RU003", "file": "app.py", "proof_question": "Are secrets hardcoded in source?"},
            ],
            "coverage_decisions": [],
        }
        backlog = bridge.record_scenario_backlog("demo", "demo-001", router_result)
        print(f"  Status: {backlog['status']}")
        print(f"  Scenarios: {backlog['scenarios']}")

        print("\n[6] Record scenario result (S001 injection):")
        result = bridge.record_scenario_result("demo", "demo-001", "S001", {
            "status": "verified",
            "findings": [
                {"title": "SQL Injection in login()", "severity": "critical", "description": "User input concatenated directly into SQL query", "evidence": ["query = f\"SELECT * FROM users WHERE username='{username}'\""]}
            ],
        })
        print(f"  Candidates: {result['candidates_created']}")

        print("\n[7] Record triage (accept):")
        triage = bridge.record_finding_triage("demo", "demo-001", "S001-F001", {
            "decision": "accepted",
            "confidence": 0.95,
            "reason": "Clear evidence of string interpolation in SQL",
        })
        print(f"  Decision: {triage['decision']}")

        print("\n[8] Summarize run:")
        summary = bridge.summarize_run("demo", "demo-001")
        print(f"  Counts: {summary['counts']}")
        print(f"  Next: {summary['next_checkpoint']}")

        print("\n[9] Validate run:")
        validation = bridge.validate_run("demo", "demo-001")
        print(f"  Status: {validation['status']}")
        print(f"  Errors: {validation['errors']}")
        print(f"  Warnings: {validation['warnings']}")

        print("\n[10] Critical findings:")
        critical = bridge.get_critical_findings("demo", "demo-001")
        print(f"  Count: {len(critical)}")
        for c in critical:
            print(f"    → {c['file']}")

    print("\n" + "=" * 60)
    print("OpenHack Bridge ready.")
    print("=" * 60)
