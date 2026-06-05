"""Native stdlib module: Obstacle Avoidance Calculator
Calculates avoidance paths and safety margins for mobile robots.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import math

@dataclass
class Obstacle:
    x: float
    y: float
    radius: float

@dataclass
class ObstacleAvoidanceCalculator:
    robot_x: float
    robot_y: float
    goal_x: float
    goal_y: float
    robot_radius: float
    obstacles: List[Obstacle] = field(default_factory=list)
    safety_margin: float = 0.5

    def distance_to_goal(self) -> float:
        return math.sqrt((self.goal_x - self.robot_x)**2 + (self.goal_y - self.robot_y)**2)

    def goal_angle(self) -> float:
        return math.degrees(math.atan2(self.goal_y - self.robot_y, self.goal_x - self.robot_x))

    def min_obstacle_distance(self) -> float:
        if not self.obstacles:
            return float('inf')
        return min(math.sqrt((o.x - self.robot_x)**2 + (o.y - self.robot_y)**2) - o.radius for o in self.obstacles)

    def collision_risk(self) -> bool:
        for o in self.obstacles:
            dist = math.sqrt((o.x - self.robot_x)**2 + (o.y - self.robot_y)**2)
            if dist < (o.radius + self.robot_radius + self.safety_margin):
                return True
        return False

    def avoidance_vector(self) -> Tuple[float, float]:
        if not self.obstacles:
            return (0.0, 0.0)
        closest = min(self.obstacles, key=lambda o: math.sqrt((o.x - self.robot_x)**2 + (o.y - self.robot_y)**2))
        dx = self.robot_x - closest.x
        dy = self.robot_y - closest.y
        dist = math.sqrt(dx**2 + dy**2)
        if dist == 0:
            return (1.0, 0.0)
        return (dx/dist, dy/dist)

    def stats(self) -> Dict:
        return {
            "distance_to_goal": round(self.distance_to_goal(), 3),
            "goal_angle": round(self.goal_angle(), 2),
            "min_obstacle_distance": round(self.min_obstacle_distance(), 3) if self.min_obstacle_distance() != float('inf') else "inf",
            "collision_risk": self.collision_risk(),
            "avoidance_vector": (round(self.avoidance_vector()[0], 3), round(self.avoidance_vector()[1], 3)),
        }

def run():
    oac = ObstacleAvoidanceCalculator(
        robot_x=0, robot_y=0, goal_x=10, goal_y=10, robot_radius=0.3,
        obstacles=[
            Obstacle(3, 3, 1.0),
            Obstacle(6, 5, 0.8),
        ],
        safety_margin=0.5
    )
    print(oac.stats())

if __name__ == "__main__":
    run()
