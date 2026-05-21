#!/usr/bin/env python3
"""Real Sentiment — RSS fetch from CoinDesk + CoinTelegraph"""

import requests

class RealSentiment:
    def __init__(self):
        self.bullish = ["surge", "rally", "adopt", "bullish", "moon", "pump"]
        self.bearish = ["crash", "ban", "hack", "bearish", "dump", "fear"]

    def fetch_headlines(self):
        try:
            r = requests.get("https://r.jina.ai/https://feeds.coindesk.com/coindesk", timeout=15)
            return r.text.split("
")[:10]
        except:
            return ["Error fetching RSS"]

    def analyze(self, headlines):
        score = 0
        for h in headlines:
            h_lower = h.lower()
            score += sum(1 for w in self.bullish if w in h_lower)
            score -= sum(1 for w in self.bearish if w in h_lower)
        return {"score": score, "rating": "STRONGLY_BEARISH" if score < -3 else "BEARISH" if score < 0 else "NEUTRAL" if score == 0 else "BULLISH"}

    def run(self):
        headlines = self.fetch_headlines()
        result = self.analyze(headlines)
        print(f"Sentiment: {result['rating']} (score: {result['score']})")
        return result

if __name__ == "__main__":
    s = RealSentiment()
    s.run()
