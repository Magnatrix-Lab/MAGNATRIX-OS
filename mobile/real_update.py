#!/usr/bin/env python3
"""Real Git Update Check"""

import subprocess

class RealUpdate:
    def check(self):
        try:
            branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
            files = subprocess.check_output(["git", "status", "--short"], text=True)
            count = len([l for l in files.split("
") if l.strip()])
            return {"branch": branch, "local_changes": count, "status": "ok"}
        except:
            return {"status": "not_git"}

if __name__ == "__main__":
    print(RealUpdate().check())
