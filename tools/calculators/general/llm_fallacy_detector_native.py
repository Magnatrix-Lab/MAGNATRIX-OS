"""Native stdlib module: Fallacy Detector
Identifies common logical fallacies in arguments by pattern matching.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class FallacyType(Enum):
    AD_HOMINEM = "ad_hominem"
    STRAW_MAN = "straw_man"
    SLIPPERY_SLOPE = "slippery_slope"
    FALSE_DICHOTOMY = "false_dichotomy"
    APPEAL_TO_AUTHORITY = "appeal_to_authority"
    CIRCULAR = "circular_reasoning"
    HASTY_GENERALIZATION = "hasty_generalization"
    POST_HOC = "post_hoc"
    TU_QUOQUE = "tu_quoque"
    BANDWAGON = "bandwagon"

@dataclass
class FallacyDetector:
    argument_text: str

    def _check_patterns(self, fallacy: FallacyType) -> bool:
        text = self.argument_text.lower()
        patterns = {
            FallacyType.AD_HOMINEM: ["you are wrong because", "you always", "you never", "just like you", "typical of"],
            FallacyType.STRAW_MAN: ["so you are saying", "basically you think", "what you really mean", "twist"],
            FallacyType.SLIPPERY_SLOPE: ["lead to", "next thing", "before you know", "snowball", "gateway", "eventually"],
            FallacyType.FALSE_DICHOTOMY: ["either or", "only two options", "black and white", "no middle ground", "you are with us or"],
            FallacyType.APPEAL_TO_AUTHORITY: ["expert says", "scientists agree", "studies show", "according to", "authority says"],
            FallacyType.CIRCULAR: ["because it is true", "it is true because", "by definition", "that is just what it is"],
            FallacyType.HASTY_GENERALIZATION: ["all of them", "everyone knows", "always happens", "never works", "one time so", "based on my experience"],
            FallacyType.POST_HOC: ["after that", "since then", "happened because", "followed by", "caused by"],
            FallacyType.TU_QUOQUE: ["you do it too", "what about you", "you also", "look at yourself", "pot calling"],
            FallacyType.BANDWAGON: ["everyone is", "most people", "popular opinion", "consensus", "everybody agrees", "majority"],
        }
        for pattern in patterns.get(fallacy, []):
            if pattern in text:
                return True
        return False

    def detected_fallacies(self) -> List[str]:
        return [f.value for f in FallacyType if self._check_patterns(f)]

    def severity_score(self) -> int:
        return len(self.detected_fallacies())

    def stats(self) -> Dict:
        return {
            "argument": self.argument_text[:80],
            "detected_fallacies": self.detected_fallacies(),
            "severity": self.severity_score(),
            "fallacy_count": len(self.detected_fallacies()),
        }

def run():
    fd = FallacyDetector(argument_text="Everyone knows the Earth is flat. After the law was passed, crime increased. So you are saying we should just give up? Either you support this or you hate freedom. Scientists agree that this is true. You are wrong because you always mess things up.")
    print(fd.stats())

if __name__ == "__main__":
    run()
