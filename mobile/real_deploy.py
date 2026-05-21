#!/usr/bin/env python3
"""Real Device Deploy"""

import subprocess

class RealDeploy:
    def check(self):
        try:
            r = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True)
            devices = [l for l in r.stdout.split("
")[1:] if l.strip()]
            return {"found": True, "devices": devices}
        except FileNotFoundError:
            return {"found": False, "install": "https://developer.android.com/studio/releases/platform-tools"}

if __name__ == "__main__":
    print(RealDeploy().check())
