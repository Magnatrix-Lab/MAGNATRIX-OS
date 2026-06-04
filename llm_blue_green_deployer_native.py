"""Blue-Green Deployer — zero-downtime deployment, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import time

class Environment(Enum):
    BLUE = auto()
    GREEN = auto()

@dataclass
class DeploymentEnv:
    env: Environment
    version: str
    active: bool
    healthy: bool
    traffic_percentage: float

class BlueGreenDeployer:
    def __init__(self):
        self.blue: Optional[DeploymentEnv] = None
        self.green: Optional[DeploymentEnv] = None
        self.current: Optional[Environment] = None
        self.switch_history: List[Dict] = []

    def deploy(self, env: Environment, version: str):
        target = DeploymentEnv(env, version, False, True, 0.0)
        if env == Environment.BLUE:
            self.blue = target
        else:
            self.green = target

    def activate(self, env: Environment):
        if env == Environment.BLUE and self.blue:
            self.blue.active = True
            self.blue.traffic_percentage = 100.0
            self.current = Environment.BLUE
            if self.green:
                self.green.active = False
                self.green.traffic_percentage = 0.0
        elif env == Environment.GREEN and self.green:
            self.green.active = True
            self.green.traffic_percentage = 100.0
            self.current = Environment.GREEN
            if self.blue:
                self.blue.active = False
                self.blue.traffic_percentage = 0.0
        self.switch_history.append({"to": env.name, "time": time.time()})

    def get_active(self) -> Optional[DeploymentEnv]:
        if self.current == Environment.BLUE:
            return self.blue
        return self.green

    def get_idle(self) -> Optional[DeploymentEnv]:
        if self.current == Environment.BLUE:
            return self.green
        return self.blue

    def swap(self):
        if self.current == Environment.BLUE and self.green and self.green.healthy:
            self.activate(Environment.GREEN)
        elif self.current == Environment.GREEN and self.blue and self.blue.healthy:
            self.activate(Environment.BLUE)

    def stats(self) -> Dict:
        return {
            "blue_version": self.blue.version if self.blue else None,
            "green_version": self.green.version if self.green else None,
            "current": self.current.name if self.current else None,
            "switches": len(self.switch_history)
        }

def run():
    deployer = BlueGreenDeployer()
    deployer.deploy(Environment.BLUE, "v1.0")
    deployer.deploy(Environment.GREEN, "v2.0")
    deployer.activate(Environment.BLUE)
    print("Active:", deployer.get_active().version if deployer.get_active() else None)
    deployer.swap()
    print("After swap:", deployer.get_active().version if deployer.get_active() else None)
    print(deployer.stats())

if __name__ == "__main__":
    run()
