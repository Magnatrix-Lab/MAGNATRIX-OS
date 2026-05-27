#!/usr/bin/env python3
"""
MAGNATRIX-OS IDE Integration Native (Layer 12)
Hub untuk 10+ IDE/AI-coding tools: auto-detect, command proxy, two-way sync.
"""
import os, json, subprocess, shutil, urllib.request, urllib.error, time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto

# Bridge imports (may not all be available)
try:
    from ide.cline_bridge import ClineBridge
except ImportError:
    ClineBridge = None
try:
    from ide.opencode_bridge import OpencodeBridge
except ImportError:
    OpencodeBridge = None
try:
    from ide.openhand_bridge import OpenhandBridge
except ImportError:
    OpenhandBridge = None
try:
    from ide.antygravity_bridge import AntygravityBridge
except ImportError:
    AntygravityBridge = None
try:
    from ide.kimi_claw_bridge import KimiClawBridge
except ImportError:
    KimiClawBridge = None


class IDEType(Enum):
    AIDER = auto(); CLINE = auto(); OPENCODE = auto()
    OPENHAND = auto(); GITHUB = auto(); COPILOT = auto()
    CURSOR = auto(); ANTYGRAVITY = auto(); CLAUDE_CODE = auto()
    KIMI_CLAW = auto()


@dataclass
class IDEConfig:
    name: str
    ide_type: IDEType
    executable: Optional[str] = None
    config_path: Optional[str] = None
    api_key_env: str = ""
    base_url: str = ""
    enabled: bool = False
    capabilities: List[str] = field(default_factory=list)


@dataclass
class IDEResult:
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class IDEDetector:
    """Auto-detect installed IDEs."""

    DETECTION_RULES = {
        IDEType.AIDER: {
            "binaries": ["aider", "aider.bat"],
            "config_paths": ["~/.aider.conf.yml", "~/.aider.conf.yaml"],
        },
        IDEType.CLINE: {
            "binaries": ["cline"],
            "config_paths": ["~/.cline/config.json"],
            "vscode_ext": "saoudrizwan.claude-dev",
        },
        IDEType.OPENCODE: {
            "binaries": ["opencode"],
            "config_paths": ["~/.opencode/config.json"],
        },
        IDEType.OPENHAND: {
            "binaries": ["openhands", "openhands-cli"],
            "config_paths": ["~/.openhands/config.toml"],
        },
        IDEType.CURSOR: {
            "binaries": ["cursor", "Cursor.exe", "Cursor.app"],
            "config_paths": ["~/.cursor/config.json", "~/Library/Application Support/Cursor/User/settings.json"],
        },
        IDEType.CLAUDE_CODE: {
            "binaries": ["claude", "claude.exe"],
            "config_paths": ["~/.claude/config.json"],
        },
        IDEType.ANTYGRAVITY: {
            "binaries": ["antygravity"],
            "config_paths": ["~/.antygravity/config.json"],
        },
        IDEType.KIMI_CLAW: {
            "binaries": [],
            "config_paths": ["~/.kimi/config.json"],
        },
        IDEType.GITHUB: {
            "binaries": ["gh"],
            "config_paths": ["~/.config/gh/config.yml"],
        },
        IDEType.COPILOT: {
            "binaries": [],
            "config_paths": ["~/.github/copilot"],
        },
    }

    @classmethod
    def detect_all(cls) -> Dict[IDEType, IDEConfig]:
        found = {}
        for ide_type, rules in cls.DETECTION_RULES.items():
            bin_path = None
            for b in rules["binaries"]:
                path = shutil.which(b)
                if path:
                    bin_path = path
                    break
            config_found = False
            for c in rules["config_paths"]:
                expanded = os.path.expanduser(c)
                if os.path.exists(expanded):
                    config_found = True
                    break
            if bin_path or config_found:
                found[ide_type] = IDEConfig(
                    name=ide_type.name,
                    ide_type=ide_type,
                    executable=bin_path,
                    config_path=rules["config_paths"][0] if rules["config_paths"] else None,
                    enabled=True,
                )
        return found

    @classmethod
    def detect_vscode_extensions(cls) -> List[str]:
        """Detect VS Code extensions for Cline, Copilot, etc."""
        exts = []
        ext_dirs = [
            os.path.expanduser("~/.vscode/extensions"),
            os.path.expanduser("~/Library/Application Support/Code/User/globalStorage"),
        ]
        for d in ext_dirs:
            if os.path.isdir(d):
                for entry in os.listdir(d):
                    if "cline" in entry.lower() or "claude-dev" in entry.lower():
                        exts.append("cline")
                    if "copilot" in entry.lower():
                        exts.append("copilot")
        return exts


class IDEBridge(ABC):
    """Base class for IDE bridges."""

    def __init__(self, config: IDEConfig):
        self.config = config

    def is_available(self) -> bool:
        return self.config.executable is not None or self._has_config()

    def _has_config(self) -> bool:
        if self.config.config_path:
            return os.path.exists(os.path.expanduser(self.config.config_path))
        return False

    @abstractmethod
    def send_command(self, command: str, context: Dict[str, Any] = None) -> IDEResult:
        ...

    @abstractmethod
    def read_feedback(self) -> List[Dict[str, Any]]:
        ...


class AiderBridge(IDEBridge):
    """Bridge to Aider (pair programming with LLM)."""

    def send_command(self, command: str, context: Dict[str, Any] = None) -> IDEResult:
        ctx = context or {}
        files = ctx.get("files", [])
        model = ctx.get("model", "gpt-4o")
        cmd_parts = [self.config.executable or "aider"]
        if model:
            cmd_parts.extend(["--model", model])
        for f in files:
            cmd_parts.append(f)
        cmd_parts.extend(["--message", command])
        try:
            result = subprocess.run(
                cmd_parts, capture_output=True, text=True, timeout=120, cwd=ctx.get("cwd")
            )
            return IDEResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
            )
        except Exception as e:
            return IDEResult(success=False, output="", error=str(e))

    def read_feedback(self) -> List[Dict[str, Any]]:
        return []  # Aider is command-line, feedback via stdout


class CursorBridge(IDEBridge):
    """Bridge to Cursor IDE."""

    def send_command(self, command: str, context: Dict[str, Any] = None) -> IDEResult:
        ctx = context or {}
        # Cursor uses VS Code extension protocol or custom protocol
        # For automation, we can use Cursor's command palette or edit settings
        settings_path = os.path.expanduser("~/.cursor/settings.json")
        try:
            # Write command to a temp file that Cursor can pick up
            tmp_cmd = os.path.expanduser("~/.magnatrix/cursor_cmd.json")
            os.makedirs(os.path.dirname(tmp_cmd), exist_ok=True)
            with open(tmp_cmd, "w") as f:
                json.dump({"command": command, "context": ctx, "timestamp": time.time()}, f)
            return IDEResult(
                success=True,
                output=f"Command queued for Cursor: {command[:60]}...",
                metadata={"queue_file": tmp_cmd},
            )
        except Exception as e:
            return IDEResult(success=False, output="", error=str(e))

    def read_feedback(self) -> List[Dict[str, Any]]:
        feedback_file = os.path.expanduser("~/.magnatrix/cursor_feedback.json")
        if os.path.exists(feedback_file):
            try:
                with open(feedback_file) as f:
                    return [json.load(f)]
            except Exception:
                pass
        return []


class ClaudeCodeBridge(IDEBridge):
    """Bridge to Claude Code (Anthropic)."""

    def send_command(self, command: str, context: Dict[str, Any] = None) -> IDEResult:
        ctx = context or {}
        cmd_parts = [self.config.executable or "claude"]
        cmd_parts.extend(["--no-git", "--output", "json"])
        cmd_parts.append(command)
        try:
            result = subprocess.run(
                cmd_parts, capture_output=True, text=True, timeout=120, cwd=ctx.get("cwd")
            )
            return IDEResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
            )
        except Exception as e:
            return IDEResult(success=False, output="", error=str(e))

    def read_feedback(self) -> List[Dict[str, Any]]:
        return []


class GitHubBridge(IDEBridge):
    """Bridge to GitHub API (not an IDE but essential for code workflow)."""

    def __init__(self, config: IDEConfig):
        super().__init__(config)
        self.token = os.environ.get("GITHUB_TOKEN", "")
        self.base_url = "https://api.github.com"

    def _api(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MAGNATRIX-OS/0.9.5",
        }
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": str(e), "status": e.code}
        except Exception as e:
            return {"error": str(e)}

    def send_command(self, command: str, context: Dict[str, Any] = None) -> IDEResult:
        ctx = context or {}
        parts = command.split()
        if not parts:
            return IDEResult(success=False, output="", error="Empty command")

        action = parts[0].lower()
        if action == "pr" and len(parts) >= 4:
            owner, repo, title = parts[1], parts[2], " ".join(parts[3:])
            result = self._api(f"repos/{owner}/{repo}/pulls", "POST", {
                "title": title,
                "head": ctx.get("branch", "main"),
                "base": ctx.get("base", "main"),
            })
            return IDEResult(
                success="error" not in result,
                output=json.dumps(result, indent=2),
                error=result.get("error"),
            )
        elif action == "commit" and len(parts) >= 4:
            owner, repo, message = parts[1], parts[2], " ".join(parts[3:])
            # GitHub commits require git push first — this is a simplified proxy
            return IDEResult(
                success=True,
                output=f"Commit command queued: {message[:60]}... (push via git)",
            )
        elif action == "review" and len(parts) >= 4:
            owner, repo, pr_num = parts[1], parts[2], parts[3]
            result = self._api(f"repos/{owner}/{repo}/pulls/{pr_num}/reviews", "POST", {
                "body": ctx.get("review_body", "LGTM"),
                "event": "APPROVE",
            })
            return IDEResult(
                success="error" not in result,
                output=json.dumps(result, indent=2),
                error=result.get("error"),
            )

        return IDEResult(success=False, output="", error=f"Unknown GitHub command: {action}")

    def read_feedback(self) -> List[Dict[str, Any]]:
        return []


class IDEIntegrationNative:
    """
    Main IDE Integration Hub for MAGNATRIX-OS.
    Manages all IDE bridges, routes commands, collects feedback.
    """

    BRIDGE_MAP = {
        IDEType.AIDER: AiderBridge,
        IDEType.CLINE: ClineBridge,
        IDEType.OPENCODE: OpencodeBridge,
        IDEType.OPENHAND: OpenhandBridge,
        IDEType.CURSOR: CursorBridge,
        IDEType.CLAUDE_CODE: ClaudeCodeBridge,
        IDEType.ANTYGRAVITY: AntygravityBridge,
        IDEType.KIMI_CLAW: KimiClawBridge,
        IDEType.GITHUB: GitHubBridge,
    }

    def __init__(self):
        self.bridges: Dict[IDEType, IDEBridge] = {}
        self.configs: Dict[IDEType, IDEConfig] = {}
        self._discover()

    def _discover(self):
        detected = IDEDetector.detect_all()
        for ide_type, config in detected.items():
            self.configs[ide_type] = config
            bridge_cls = self.BRIDGE_MAP.get(ide_type)
            if bridge_cls:
                self.bridges[ide_type] = bridge_cls(config)

    def list_ides(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": c.name,
                "type": c.ide_type.name,
                "enabled": c.enabled,
                "available": self.bridges.get(c.ide_type, object()).is_available() if c.ide_type in self.bridges else False,
                "executable": c.executable,
            }
            for c in self.configs.values()
        ]

    def send(self, ide_type: IDEType, command: str, context: Dict[str, Any] = None) -> IDEResult:
        bridge = self.bridges.get(ide_type)
        if not bridge:
            return IDEResult(success=False, output="", error=f"IDE {ide_type.name} not available")
        return bridge.send_command(command, context)

    def broadcast(self, command: str, context: Dict[str, Any] = None) -> Dict[IDEType, IDEResult]:
        """Send command to all available IDEs."""
        results = {}
        for ide_type, bridge in self.bridges.items():
            if bridge.is_available():
                results[ide_type] = bridge.send_command(command, context)
        return results

    def collect_feedback(self) -> Dict[IDEType, List[Dict]]:
        feedback = {}
        for ide_type, bridge in self.bridges.items():
            feedback[ide_type] = bridge.read_feedback()
        return feedback


def _demo():
    print("=" * 60)
    print("MAGNATRIX-OS IDE Integration Demo")
    print("=" * 60)

    hub = IDEIntegrationNative()
    ides = hub.list_ides()
    print(f"\n[1] Detected {len(ides)} IDE(s):")
    for i in ides:
        status = "✅" if i["available"] else "❌"
        print(f"    {status} {i['name']} ({i['type']}) — exec: {i['executable'] or 'N/A'}")

    # Try sending to each
    print("\n[2] Sending test command to available IDEs...")
    results = hub.broadcast("echo 'Hello from MAGNATRIX-OS'")
    for ide_type, result in results.items():
        print(f"    {ide_type.name}: success={result.success}")
        if not result.success:
            print(f"      Error: {result.error}")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
