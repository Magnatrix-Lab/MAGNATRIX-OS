#!/usr/bin/env python3
"""
Container Manager for MAGNATRIX-OS
Docker/container detection, container info, and image management.
Native stdlib only (subprocess for docker CLI).

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import time
from typing import Any, Dict, List, Optional


@dataclasses.dataclass
class ContainerInfo:
    container_id: str
    image: str
    status: str
    names: List[str]
    ports: Dict[str, Any]
    created: str
    size: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.container_id,
            "image": self.image,
            "status": self.status,
            "names": self.names,
            "ports": self.ports,
            "created": self.created,
            "size": self.size,
        }


@dataclasses.dataclass
class ImageInfo:
    image_id: str
    repo_tags: List[str]
    created: str
    size: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.image_id,
            "tags": self.repo_tags,
            "created": self.created,
            "size": self.size,
        }


class ContainerManager:
    """Manages Docker containers and images via CLI."""

    def __init__(self) -> None:
        self._docker_available = self._check_docker()

    def _check_docker(self) -> bool:
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def _docker_cmd(self, args: List[str]) -> subprocess.CompletedProcess:
        if not self._docker_available:
            raise RuntimeError("Docker not available")
        return subprocess.run(["docker"] + args, capture_output=True, text=True, timeout=30)

    def is_available(self) -> bool:
        return self._docker_available

    def is_in_container(self) -> bool:
        return os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")

    def get_container_id(self) -> Optional[str]:
        try:
            with open("/proc/self/cgroup", "r") as f:
                for line in f:
                    if "docker" in line:
                        parts = line.strip().split("/")
                        return parts[-1] if parts[-1] else None
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Container operations
    # ------------------------------------------------------------------

    def list_containers(self, all: bool = False) -> List[ContainerInfo]:
        args = ["ps", "--format", "{{json .}}"]
        if all:
            args.append("-a")
        result = self._docker_cmd(args)
        containers = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                containers.append(ContainerInfo(
                    container_id=data.get("ID", "")[:12],
                    image=data.get("Image", ""),
                    status=data.get("Status", ""),
                    names=data.get("Names", "").split(","),
                    ports=data.get("Ports", {}),
                    created=data.get("CreatedAt", ""),
                    size=data.get("Size", ""),
                ))
            except Exception:
                pass
        return containers

    def container_stats(self, container_id: str) -> Dict[str, Any]:
        result = self._docker_cmd(["stats", "--no-stream", "--format", "{{json .}}", container_id])
        try:
            return json.loads(result.stdout.strip().split("\n")[0])
        except Exception:
            return {}

    def start_container(self, container_id: str) -> bool:
        result = self._docker_cmd(["start", container_id])
        return result.returncode == 0

    def stop_container(self, container_id: str) -> bool:
        result = self._docker_cmd(["stop", container_id])
        return result.returncode == 0

    def remove_container(self, container_id: str, force: bool = False) -> bool:
        args = ["rm", container_id]
        if force:
            args.append("-f")
        result = self._docker_cmd(args)
        return result.returncode == 0

    # ------------------------------------------------------------------
    # Image operations
    # ------------------------------------------------------------------

    def list_images(self) -> List[ImageInfo]:
        result = self._docker_cmd(["images", "--format", "{{json .}}"])
        images = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                images.append(ImageInfo(
                    image_id=data.get("ID", "")[:12],
                    repo_tags=[data.get("Repository", "") + ":" + data.get("Tag", "")],
                    created=data.get("CreatedAt", ""),
                    size=self._parse_size(data.get("Size", "0")),
                ))
            except Exception:
                pass
        return images

    def pull_image(self, image: str) -> bool:
        result = self._docker_cmd(["pull", image])
        return result.returncode == 0

    def remove_image(self, image_id: str) -> bool:
        result = self._docker_cmd(["rmi", image_id])
        return result.returncode == 0

    def build_image(self, path: str, tag: str) -> bool:
        result = self._docker_cmd(["build", "-t", tag, path])
        return result.returncode == 0

    def _parse_size(self, size_str: str) -> int:
        try:
            size_str = size_str.strip().upper()
            if size_str.endswith("GB"):
                return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
            elif size_str.endswith("MB"):
                return int(float(size_str[:-2]) * 1024 * 1024)
            elif size_str.endswith("KB"):
                return int(float(size_str[:-2]) * 1024)
            else:
                return int(float(size_str))
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        return {
            "docker_available": self._docker_available,
            "in_container": self.is_in_container(),
            "container_id": self.get_container_id(),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    mgr = ContainerManager()
    print("=== Container Manager Demo ===\n")
    print(f"Docker available: {mgr.is_available()}")
    print(f"In container: {mgr.is_in_container()}")
    print(f"Container ID: {mgr.get_container_id()}")
    if mgr.is_available():
        print(f"Containers: {len(mgr.list_containers(all=True))}")
        print(f"Images: {len(mgr.list_images())}")
    print(f"Stats: {mgr.stats()}")


if __name__ == "__main__":
    _demo()
