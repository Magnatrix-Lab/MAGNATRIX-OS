"""Native stdlib module: PID Tuner
Calculates PID controller gains and performance metrics.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class PIDTuner:
    kp: float
    ki: float
    kd: float
    setpoint: float
    process_variable: float
    dt: float = 1.0

    def error(self) -> float:
        return self.setpoint - self.process_variable

    def proportional_term(self) -> float:
        return self.kp * self.error()

    def integral_term(self, integral_error: float) -> float:
        return self.ki * integral_error * self.dt

    def derivative_term(self, previous_error: float) -> float:
        if self.dt == 0:
            return 0.0
        return self.kd * (self.error() - previous_error) / self.dt

    def output(self, integral_error: float, previous_error: float) -> float:
        return self.proportional_term() + self.integral_term(integral_error) + self.derivative_term(previous_error)

    def ziegler_nichols_p(self, ku: float, tu: float) -> Dict:
        return {"kp": 0.5 * ku, "ki": 0.0, "kd": 0.0}

    def ziegler_nichols_pi(self, ku: float, tu: float) -> Dict:
        return {"kp": 0.45 * ku, "ki": 0.54 * ku / tu, "kd": 0.0}

    def ziegler_nichols_pid(self, ku: float, tu: float) -> Dict:
        return {"kp": 0.6 * ku, "ki": 1.2 * ku / tu, "kd": 0.075 * ku * tu}

    def stats(self, integral_error: float = 0, previous_error: float = 0) -> Dict:
        return {
            "error": round(self.error(), 4),
            "proportional": round(self.proportional_term(), 4),
            "integral": round(self.integral_term(integral_error), 4),
            "derivative": round(self.derivative_term(previous_error), 4),
            "output": round(self.output(integral_error, previous_error), 4),
        }

def run():
    pid = PIDTuner(kp=1.0, ki=0.1, kd=0.5, setpoint=100, process_variable=85, dt=0.1)
    print(pid.stats(integral_error=50, previous_error=20))
    print(pid.ziegler_nichols_pid(ku=10, tu=2))

if __name__ == "__main__":
    run()
