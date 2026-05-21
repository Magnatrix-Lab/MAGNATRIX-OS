#!/usr/bin/env python3
"""Risk Auto-Tune — Self-adjust risk parameters based on performance"""

import json

class RiskAutoTune:
    def __init__(self):
        self.params = {"kelly": 0.30, "sl": 0.02, "tp": 0.04, "size": 1.0}

    def tune(self, win_rate=0.55, drawdown=0.02):
        old = self.params.copy()
        if win_rate > 0.60 and drawdown < 0.03:
            self.params["kelly"] = min(0.35, self.params["kelly"] + 0.05)
            self.params["sl"] = max(0.015, self.params["sl"] - 0.005)
            self.params["tp"] = min(0.045, self.params["tp"] + 0.005)
        elif win_rate < 0.40 or drawdown > 0.05:
            self.params["kelly"] = max(0.25, self.params["kelly"] - 0.05)
            self.params["size"] = max(0.8, self.params["size"] - 0.2)
            self.params["sl"] = min(0.025, self.params["sl"] + 0.005)

        result = {"old": old, "new": self.params.copy(), "reason": f"win_rate={win_rate}, dd={drawdown}"}
        with open("trading/risk_autotune_log.json", "w") as f:
            json.dump(result, f, indent=2)
        print(f"Risk tuned: Kelly {old['kelly']:.2f} → {self.params['kelly']:.2f} | Size {old['size']:.0%} → {self.params['size']:.0%}")
        return result

if __name__ == "__main__":
    rt = RiskAutoTune()
    rt.tune(win_rate=0.70, drawdown=0.02)
    rt.tune(win_rate=0.35, drawdown=0.07)
