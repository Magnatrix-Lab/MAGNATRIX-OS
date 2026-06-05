"""Native stdlib module: Probability Logic Calculator
Calculates conditional probabilities, Bayes theorem, and logical probability.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class ProbabilityLogicCalculator:
    prior_a: float
    prior_b: float
    conditional_b_given_a: float

    def joint_probability(self) -> float:
        return self.prior_a * self.conditional_b_given_a

    def conditional_a_given_b(self) -> float:
        if self.prior_b == 0:
            return 0.0
        return (self.conditional_b_given_a * self.prior_a) / self.prior_b

    def independence_check(self) -> bool:
        if self.prior_a == 0 or self.prior_b == 0:
            return False
        expected_joint = self.prior_a * self.prior_b
        actual_joint = self.joint_probability()
        return abs(expected_joint - actual_joint) < 0.001

    def odds_ratio(self) -> float:
        if self.prior_b == 0 or self.prior_a == 0:
            return 0.0
        return (self.prior_a / (1 - self.prior_a)) / (self.prior_b / (1 - self.prior_b))

    def likelihood_ratio(self) -> float:
        if self.prior_b == 0:
            return 0.0
        return self.conditional_b_given_a / self.prior_b

    def posterior_odds(self) -> float:
        if self.prior_b == 0:
            return 0.0
        return (self.prior_a / (1 - self.prior_a)) * (self.conditional_b_given_a / self.prior_b)

    def posterior_probability(self) -> float:
        odds = self.posterior_odds()
        return odds / (1 + odds)

    def stats(self) -> Dict:
        return {
            "prior_a": self.prior_a,
            "prior_b": self.prior_b,
            "p_b_given_a": self.conditional_b_given_a,
            "joint_probability": round(self.joint_probability(), 4),
            "p_a_given_b": round(self.conditional_a_given_b(), 4),
            "independent": self.independence_check(),
            "likelihood_ratio": round(self.likelihood_ratio(), 4),
            "posterior_probability": round(self.posterior_probability(), 4),
        }

def run():
    plc = ProbabilityLogicCalculator(prior_a=0.01, prior_b=0.1, conditional_b_given_a=0.9)
    print(plc.stats())

if __name__ == "__main__":
    run()
