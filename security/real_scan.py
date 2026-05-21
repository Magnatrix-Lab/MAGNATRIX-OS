#!/usr/bin/env python3
"""Real Security Scan — agentshield-style pattern detection"""

import os
import json

class SecurityScanner:
    def __init__(self):
        self.patterns = {
            "hardcoded_secret": ["api_key", "password", "secret", "token"],
            "sql_injection": ["SELECT * FROM", "INSERT INTO", "DELETE FROM"],
            "eval_danger": ["eval(", "exec(", "__import__"],
        }

    def scan_file(self, filepath):
        findings = []
        try:
            with open(filepath, "r", errors="ignore") as f:
                lines = f.readlines()
            for i, line in enumerate(lines, 1):
                for severity, patterns in self.patterns.items():
                    for p in patterns:
                        if p.lower() in line.lower():
                            findings.append({"file": filepath, "line": i, "match": p, "severity": severity})
        except:
            pass
        return findings

    def scan_directory(self, path="api-router/ccl/"):
        all_findings = []
        for root, dirs, files in os.walk(path):
            for f in files:
                if f.endswith((".py", ".ts", ".js", ".json", ".yaml", ".sh")):
                    filepath = os.path.join(root, f)
                    findings = self.scan_file(filepath)
                    all_findings.extend(findings)

        with open("security/scan_report.json", "w") as f:
            json.dump(all_findings, f, indent=2)

        print(f"🔍 Scanned {path}: {len(all_findings)} findings")
        for f in all_findings[:10]:
            print(f"  [{f['severity']}] {f['file']}:{f['line']} → {f['match']}")
        return all_findings

if __name__ == "__main__":
    scanner = SecurityScanner()
    scanner.scan_directory("api-router/ccl/")
