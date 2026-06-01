#!/usr/bin/env python3
"""docs/deployment_guide_native.py — Deployment Guide Generator"""
from __future__ import annotations
import os, platform, json
from typing import Dict, List

class DeploymentGuide:
    def __init__(self):
        self.platform = platform.system()
        self.arch = platform.machine()
        self.sections: List[str] = []

    def detect_platform(self) -> Dict[str, str]:
        return {"os": self.platform, "arch": self.arch, "python": platform.python_version()}

    def check_prerequisites(self) -> List[str]:
        checks = ["Python 3.11+", "pip", "git"]
        if self.platform == "Linux":
            checks.extend(["systemd", "cron"])
        return checks

    def generate(self, output: str = "/tmp/deployment_guide.md") -> str:
        lines = [f"# MAGNATRIX-OS Deployment Guide", ""]
        lines.append(f"**Platform:** {self.platform} ({self.arch})")
        lines.append(f"**Python:** {platform.python_version()}")
        lines.append("")

        lines.append("## Prerequisites")
        for p in self.check_prerequisites():
            lines.append(f"- [ ] {p}")
        lines.append("")

        lines.append("## Installation")
        lines.append("```bash")
        lines.append("git clone https://github.com/Magnatrix-Lab/MAGNATRIX-OS")
        lines.append("cd MAGNATRIX-OS")
        lines.append("pip install -r requirements.txt")
        lines.append("```")
        lines.append("")

        lines.append("## Configuration")
        lines.append("Edit `config/system.yaml` with your settings.")
        lines.append("")

        lines.append("## Service Setup")
        if self.platform == "Linux":
            lines.append("```bash")
            lines.append("sudo cp systemd/magnatrix.service /etc/systemd/system/")
            lines.append("sudo systemctl enable --now magnatrix")
            lines.append("```")
        lines.append("")

        lines.append("## Verification")
        lines.append("```bash")
        lines.append("python -m magnatrix.health_check")
        lines.append("```")
        lines.append("")

        lines.append("## Troubleshooting")
        lines.append("- Port 8080 in use: change in config")
        lines.append("- Permission denied: check file ownership")
        lines.append("")

        content = "
".join(lines)
        with open(output, "w") as f:
            f.write(content)
        return output

if __name__ == "__main__":
    guide = DeploymentGuide()
    print(f"Platform: {guide.detect_platform()}")
    path = guide.generate()
    print(f"Guide: {path}")
