"""SLAM Engine — landmark mapping, pose graph, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto
import math
import random

@dataclass
class Landmark:
    landmark_id: str
    x: float
    y: float

@dataclass
class PoseNode:
    pose_id: str
    x: float
    y: float
    theta: float
    landmarks: List[str] = field(default_factory=list)

class SLAMEngine:
    def __init__(self, sensor_range: float = 10.0, sensor_noise: float = 0.5):
        self.sensor_range = sensor_range
        self.sensor_noise = sensor_noise
        self.poses: List[PoseNode] = []
        self.landmarks: Dict[str, Landmark] = {}
        self.pose_graph: List[Tuple[str, str, Dict]] = []

    def add_pose(self, pose_id: str, x: float, y: float, theta: float):
        self.poses.append(PoseNode(pose_id, x, y, theta))

    def observe(self, pose_id: str, landmark_id: str, measured_x: float, measured_y: float):
        pose = next((p for p in self.poses if p.pose_id == pose_id), None)
        if not pose:
            return
        if landmark_id not in self.landmarks:
            # Initialize landmark from observation
            self.landmarks[landmark_id] = Landmark(landmark_id, pose.x + measured_x, pose.y + measured_y)
        pose.landmarks.append(landmark_id)
        self.pose_graph.append((pose_id, landmark_id, {"mx": measured_x, "my": measured_y}))

    def optimize(self, iterations: int = 10):
        for _ in range(iterations):
            for pose in self.poses:
                for lid in pose.landmarks:
                    lm = self.landmarks.get(lid)
                    if lm:
                        # Simple gradient descent update
                        dx = lm.x - pose.x
                        dy = lm.y - pose.y
                        pose.x += dx * 0.01
                        pose.y += dy * 0.01

    def get_map(self) -> Dict:
        return {"poses": len(self.poses), "landmarks": len(self.landmarks)}

    def stats(self) -> Dict:
        return {"poses": len(self.poses), "landmarks": len(self.landmarks), "edges": len(self.pose_graph)}

def run():
    slam = SLAMEngine(10, 0.3)
    slam.add_pose("p1", 0, 0, 0)
    slam.add_pose("p2", 5, 0, 0)
    slam.observe("p1", "lm1", 5, 0)
    slam.observe("p2", "lm1", 0, 0)
    slam.observe("p1", "lm2", 3, 4)
    slam.optimize(5)
    print(slam.stats())

if __name__ == "__main__":
    run()
