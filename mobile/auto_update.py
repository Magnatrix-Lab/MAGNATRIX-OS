#!/usr/bin/env python3
"""Auto Update Check"""

import subprocess

class AutoUpdate:
    def check(self):
        try:
            subprocess.run(["git", "fetch", "origin"], capture_output=True)
            ahead = subprocess.check_output(["git", "rev-list", "HEAD..origin/main", "--count"], text=True).strip()
            if ahead == "0":
                return {"status": "up_to_date"}
            return {"status": "update_available", "behind": int(ahead)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    print(AutoUpdate().check())
