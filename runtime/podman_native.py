#!/usr/bin/env python3
"""podman_native.py - Podman container engine simulation. Pure Python."""
from __future__ import annotations
import json, math, hashlib, sqlite3, random, re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Container Runtime
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LinuxNamespace:
    type: str
    path: str = ""
    def __repr__(self) -> str:
        return f"<LinuxNamespace {self.type}>"

@dataclass
class CgroupLimit:
    resource: str
    limit: int
    unit: str = ""
    def __repr__(self) -> str:
        return f"<CgroupLimit {self.resource}={self.limit}{self.unit}>"

@dataclass
class SeccompRule:
    syscall: str
    action: str = "SCMP_ACT_ALLOW"
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    def __repr__(self) -> str:
        return f"<SeccompRule {self.syscall}={self.action}>"

@dataclass
class CapabilitySet:
    bounding: List[str] = field(default_factory=list)
    effective: List[str] = field(default_factory=list)
    permitted: List[str] = field(default_factory=list)
    inheritable: List[str] = field(default_factory=list)
    ambient: List[str] = field(default_factory=list)
    def __repr__(self) -> str:
        return f"<CapabilitySet bounding={len(self.bounding)}>"

@dataclass
class ContainerSpec:
    """OCI-style container specification."""
    id: str
    rootfs: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    cwd: str = "/"
    user: str = "root"
    namespaces: List[LinuxNamespace] = field(default_factory=list)
    cgroups: List[CgroupLimit] = field(default_factory=list)
    seccomp: List[SeccompRule] = field(default_factory=list)
    capabilities: CapabilitySet = field(default_factory=CapabilitySet)
    mounts: List[Dict[str, str]] = field(default_factory=list)
    hostname: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    stop_signal: str = "SIGTERM"
    stop_timeout: int = 10
    def __repr__(self) -> str:
        return f"<ContainerSpec id={self.id} rootfs={self.rootfs} args={self.args}>"

@dataclass
class Process:
    """Running or exited container process state."""
    pid: int
    status: str
    exit_code: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    command: str = ""
    def __repr__(self) -> str:
        return f"<Process pid={self.pid} status={self.status}>"

class NamespaceManager:
    """Simulate Linux namespace isolation."""
    def __init__(self) -> None:
        self._namespaces: Dict[str, Dict[str, Any]] = {}
        self._next_pid = 1000
    def __repr__(self) -> str:
        return f"<NamespaceManager namespaces={len(self._namespaces)}>"
    def create(self, ns_type: str, container_id: str) -> str:
        ns_id = f"{ns_type}:{container_id}:{self._next_pid}"
        self._next_pid += 1
        self._namespaces[ns_id] = {"type": ns_type, "container_id": container_id, "pids": []}
        return ns_id
    def attach(self, ns_id: str, pid: int) -> None:
        if ns_id in self._namespaces:
            self._namespaces[ns_id]["pids"].append(pid)
    def list_for_container(self, container_id: str) -> List[str]:
        return [k for k, v in self._namespaces.items() if v.get("container_id") == container_id]

class CgroupManager:
    """Simulate cgroup resource control."""
    def __init__(self) -> None:
        self._limits: Dict[str, List[CgroupLimit]] = {}
    def __repr__(self) -> str:
        return f"<CgroupManager containers={len(self._limits)}>"
    def set_limits(self, container_id: str, limits: List[CgroupLimit]) -> None:
        self._limits[container_id] = limits
    def get_limits(self, container_id: str) -> List[CgroupLimit]:
        return self._limits.get(container_id, [])
    def enforce(self, container_id: str, resource: str, usage: int) -> bool:
        limits = self._limits.get(container_id, [])
        for limit in limits:
            if limit.resource == resource and usage > limit.limit:
                return False
        return True

class ContainerRuntime:
    """Container lifecycle manager simulating runc-like behavior."""
    def __init__(self, db_path: Optional[str] = None) -> None:
        self._containers: Dict[str, ContainerSpec] = {}
        self._processes: Dict[str, Process] = {}
        self._ns_manager = NamespaceManager()
        self._cgroup_manager = CgroupManager()
        self._db_path = db_path
        if db_path:
            self._init_db()
    def __repr__(self) -> str:
        running = sum(1 for p in self._processes.values() if p.status == "running")
        return f"<ContainerRuntime containers={len(self._containers)} running={running}>"
    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS containers (id TEXT PRIMARY KEY, spec TEXT, status TEXT, created_at TEXT)")
        conn.commit()
        conn.close()
    def create(self, spec: ContainerSpec) -> Process:
        self._containers[spec.id] = spec
        for ns in spec.namespaces:
            ns_id = self._ns_manager.create(ns.type, spec.id)
            self._ns_manager.attach(ns_id, self._ns_manager._next_pid)
        if spec.cgroups:
            self._cgroup_manager.set_limits(spec.id, spec.cgroups)
        process = Process(pid=self._ns_manager._next_pid - 1, status="created",
                          command=" ".join(spec.args) if spec.args else "sh")
        self._processes[spec.id] = process
        if self._db_path:
            conn = sqlite3.connect(self._db_path)
            conn.execute("INSERT OR REPLACE INTO containers VALUES (?,?,?,?)",
                         (spec.id, json.dumps(spec.__dict__, default=str), "created",
                          datetime.now(timezone.utc).isoformat()))
            conn.commit()
            conn.close()
        return process
    def start(self, container_id: str) -> bool:
        process = self._processes.get(container_id)
        if not process or process.status != "created":
            return False
        process.status = "running"
        process.start_time = datetime.now(timezone.utc)
        return True
    def stop(self, container_id: str, timeout: int = 10) -> bool:
        process = self._processes.get(container_id)
        if not process or process.status not in ("running", "paused"):
            return False
        process.status = "stopped"
        process.end_time = datetime.now(timezone.utc)
        process.exit_code = 0
        return True
    def remove(self, container_id: str, force: bool = False) -> bool:
        if container_id not in self._containers:
            return False
        process = self._processes.get(container_id)
        if process and process.status == "running" and not force:
            return False
        del self._containers[container_id]
        if container_id in self._processes:
            del self._processes[container_id]
        return True
    def pause(self, container_id: str) -> bool:
        process = self._processes.get(container_id)
        if process and process.status == "running":
            process.status = "paused"
            return True
        return False
    def unpause(self, container_id: str) -> bool:
        process = self._processes.get(container_id)
        if process and process.status == "paused":
            process.status = "running"
            return True
        return False
    def inspect(self, container_id: str) -> Dict[str, Any]:
        spec = self._containers.get(container_id)
        process = self._processes.get(container_id)
        if not spec:
            return {}
        return {"id": spec.id, "status": process.status if process else "unknown",
                "rootfs": spec.rootfs, "args": spec.args, "env": spec.env,
                "user": spec.user, "hostname": spec.hostname, "labels": spec.labels,
                "pid": process.pid if process else None,
                "start_time": process.start_time.isoformat() if process and process.start_time else None,
                "cgroups": [f"{c.resource}={c.limit}" for c in spec.cgroups]}
    def list_containers(self, all_containers: bool = False) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for cid in self._containers:
            proc = self._processes.get(cid)
            if all_containers or (proc and proc.status in ("running", "paused", "created")):
                results.append(self.inspect(cid))
        return results

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Image Layers & Storage
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ImageLayer:
    """A single layer in an image layer chain."""
    id: str
    parent_id: Optional[str] = None
    digest: str = ""
    size: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    files: List[str] = field(default_factory=list)
    def __repr__(self) -> str:
        return f"<ImageLayer id={self.id[:12]} size={self.size} files={len(self.files)}>"

@dataclass
class ImageConfig:
    """Image configuration (entrypoint, cmd, env, etc.)."""
    entrypoint: List[str] = field(default_factory=list)
    cmd: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    working_dir: str = ""
    user: str = ""
    exposed_ports: List[str] = field(default_factory=list)
    volumes: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    healthcheck: Dict[str, Any] = field(default_factory=dict)
    def __repr__(self) -> str:
        return f"<ImageConfig entrypoint={self.entrypoint} cmd={self.cmd}>"

@dataclass
class Image:
    """A container image."""
    id: str
    tags: List[str] = field(default_factory=list)
    layers: List[str] = field(default_factory=list)
    config: ImageConfig = field(default_factory=ImageConfig)
    size: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    architecture: str = "amd64"
    os: str = "linux"
    def __repr__(self) -> str:
        return f"<Image id={self.id[:12]} tags={self.tags} layers={len(self.layers)}>"

class LayerStore:
    """Store and manage image layers as a DAG."""
    def __init__(self) -> None:
        self._layers: Dict[str, ImageLayer] = {}
        self._children: Dict[str, List[str]] = {}
    def __repr__(self) -> str:
        return f"<LayerStore layers={len(self._layers)}>"
    def add(self, layer: ImageLayer) -> None:
        self._layers[layer.id] = layer
        if layer.parent_id:
            self._children.setdefault(layer.parent_id, []).append(layer.id)
    def get(self, layer_id: str) -> Optional[ImageLayer]:
        return self._layers.get(layer_id)
    def chain(self, layer_id: str) -> List[ImageLayer]:
        chain: List[ImageLayer] = []
        current = layer_id
        while current:
            layer = self._layers.get(current)
            if not layer:
                break
            chain.append(layer)
            current = layer.parent_id
        return list(reversed(chain))
    def assemble_rootfs(self, layer_ids: List[str]) -> List[str]:
        all_files: Set[str] = set()
        for lid in layer_ids:
            for layer in self.chain(lid):
                all_files.update(layer.files)
        return sorted(all_files)

class ImageStore:
    """Registry of images with tag management."""
    def __init__(self, db_path: Optional[str] = None) -> None:
        self._images: Dict[str, Image] = {}
        self._tags: Dict[str, str] = {}
        self._layer_store = LayerStore()
        self._db_path = db_path
        if db_path:
            self._init_db()
    def __repr__(self) -> str:
        return f"<ImageStore images={len(self._images)} tags={len(self._tags)}>"
    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS images (id TEXT PRIMARY KEY, tags TEXT, layers TEXT, config TEXT, size INTEGER, created_at TEXT)")
        conn.commit()
        conn.close()
    def add(self, image: Image) -> None:
        self._images[image.id] = image
        for tag in image.tags:
            self._tags[tag] = image.id
        if self._db_path:
            conn = sqlite3.connect(self._db_path)
            conn.execute("INSERT OR REPLACE INTO images VALUES (?,?,?,?,?,?)",
                         (image.id, json.dumps(image.tags), json.dumps(image.layers),
                          json.dumps(image.config.__dict__, default=str), image.size,
                          image.created_at.isoformat()))
            conn.commit()
            conn.close()
    def get(self, image_id: str) -> Optional[Image]:
        return self._images.get(image_id)
    def resolve(self, tag: str) -> Optional[Image]:
        image_id = self._tags.get(tag)
        if image_id:
            return self._images.get(image_id)
        return None
    def list_images(self) -> List[Image]:
        return list(self._images.values())
    def untag(self, tag: str) -> bool:
        if tag in self._tags:
            del self._tags[tag]
            return True
        return False
    def remove(self, image_id: str) -> bool:
        if image_id in self._images:
            del self._images[image_id]
            to_remove = [t for t, iid in self._tags.items() if iid == image_id]
            for t in to_remove:
                del self._tags[t]
            return True
        return False
    def layer_store(self) -> LayerStore:
        return self._layer_store

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Image Builder: Dockerfile Parser + Layer Cache
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DockerfileInstruction:
    """Single parsed Dockerfile instruction."""
    command: str
    arguments: str
    line_number: int = 0
    def __repr__(self) -> str:
        return f"<DockerfileInstruction {self.command} {self.arguments[:40]}>"

class DockerfileParser:
    """Parse Dockerfile into a sequence of instructions."""
    VALID_COMMANDS = {"FROM", "RUN", "COPY", "ADD", "ENV", "EXPOSE", "WORKDIR",
                      "CMD", "ENTRYPOINT", "LABEL", "VOLUME", "USER", "ARG",
                      "HEALTHCHECK", "SHELL"}
    def __init__(self) -> None:
        self._instructions: List[DockerfileInstruction] = []
    def __repr__(self) -> str:
        return f"<DockerfileParser instructions={len(self._instructions)}>"
    def parse(self, dockerfile_content: str) -> List[DockerfileInstruction]:
        self._instructions = []
        lines = dockerfile_content.splitlines()
        for i, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if not parts:
                continue
            cmd = parts[0].upper()
            args = parts[1] if len(parts) > 1 else ""
            if cmd in self.VALID_COMMANDS:
                self._instructions.append(DockerfileInstruction(command=cmd, arguments=args, line_number=i))
        return self._instructions
    def get_base_image(self) -> Optional[str]:
        for inst in self._instructions:
            if inst.command == "FROM":
                return inst.arguments.strip()
        return None

@dataclass
class BuildContext:
    """Build context with files for COPY/ADD."""
    path: str
    files: Dict[str, str] = field(default_factory=dict)
    def __repr__(self) -> str:
        return f"<BuildContext path={self.path} files={len(self.files)}>"
    def get_file(self, rel_path: str) -> Optional[str]:
        return self.files.get(rel_path)

class LayerCache:
    """Hash-based cache for build layers."""
    def __init__(self) -> None:
        self._cache: Dict[str, ImageLayer] = {}
    def __repr__(self) -> str:
        return f"<LayerCache entries={len(self._cache)}>"
    def _hash(self, instruction: str, context_hash: str) -> str:
        return hashlib.sha256(f"{instruction}:{context_hash}".encode()).hexdigest()[:16]
    def get(self, instruction: str, context_hash: str) -> Optional[ImageLayer]:
        key = self._hash(instruction, context_hash)
        return self._cache.get(key)
    def put(self, instruction: str, context_hash: str, layer: ImageLayer) -> None:
        key = self._hash(instruction, context_hash)
        self._cache[key] = layer
    def invalidate(self) -> None:
        self._cache.clear()

@dataclass
class BuildOptions:
    """Options controlling the image build process."""
    no_cache: bool = False
    build_args: Dict[str, str] = field(default_factory=dict)
    target: str = ""
    platform: str = "linux/amd64"
    squash: bool = False
    layers: bool = True
    def __repr__(self) -> str:
        return f"<BuildOptions no_cache={self.no_cache} target={self.target}>"

class ImageBuilder:
    """Build images from Dockerfiles with layer caching."""
    def __init__(self, image_store: ImageStore, layer_cache: Optional[LayerCache] = None) -> None:
        self.image_store = image_store
        self.layer_cache = layer_cache or LayerCache()
        self._parser = DockerfileParser()
        self._build_log: List[str] = []
    def __repr__(self) -> str:
        return f"<ImageBuilder log_entries={len(self._build_log)}>"
    def build(self, dockerfile: str, context: BuildContext,
              tag: str = "", options: Optional[BuildOptions] = None) -> Image:
        opts = options or BuildOptions()
        instructions = self._parser.parse(dockerfile)
        base_image_tag = self._parser.get_base_image() or "scratch"
        base_image = self.image_store.resolve(base_image_tag)
        parent_layer_id = base_image.layers[-1] if base_image and base_image.layers else None
        built_layers: List[str] = []
        if base_image:
            built_layers = list(base_image.layers)
        context_hash = hashlib.sha256(json.dumps(context.files, sort_keys=True).encode()).hexdigest()[:16]
        for inst in instructions:
            if inst.command in ("RUN", "COPY", "ADD"):
                cache_key = f"{inst.command} {inst.arguments}"
                if not opts.no_cache:
                    cached = self.layer_cache.get(cache_key, context_hash)
                    if cached:
                        built_layers.append(cached.id)
                        self._build_log.append(f"  -> CACHE HIT {cached.id[:12]}")
                        parent_layer_id = cached.id
                        continue
                layer_id = hashlib.sha256(
                    f"{parent_layer_id or 'scratch'}:{inst.command}:{inst.arguments}:{datetime.now(timezone.utc)}".encode()
                ).hexdigest()[:16]
                new_layer = ImageLayer(
                    id=layer_id, parent_id=parent_layer_id,
                    created_by=f"{inst.command} {inst.arguments}",
                    size=random_size(), files=simulate_files(inst)
                )
                self.image_store.layer_store().add(new_layer)
                self.layer_cache.put(cache_key, context_hash, new_layer)
                built_layers.append(layer_id)
                parent_layer_id = layer_id
                self._build_log.append(f"  -> LAYER {layer_id[:12]} ({inst.command})")
            elif inst.command == "ENV":
                self._build_log.append(f"  -> ENV {inst.arguments}")
            elif inst.command == "EXPOSE":
                self._build_log.append(f"  -> EXPOSE {inst.arguments}")
            elif inst.command == "WORKDIR":
                self._build_log.append(f"  -> WORKDIR {inst.arguments}")
            elif inst.command == "CMD":
                self._build_log.append(f"  -> CMD {inst.arguments}")
            elif inst.command == "ENTRYPOINT":
                self._build_log.append(f"  -> ENTRYPOINT {inst.arguments}")
        image_id = hashlib.sha256(f"{tag or 'untagged'}:{':'.join(built_layers)}".encode()).hexdigest()[:16]
        config = ImageConfig()
        for inst in instructions:
            if inst.command == "CMD":
                config.cmd = parse_json_or_split(inst.arguments)
            elif inst.command == "ENTRYPOINT":
                config.entrypoint = parse_json_or_split(inst.arguments)
            elif inst.command == "ENV":
                parts = inst.arguments.split("=", 1)
                if len(parts) == 2:
                    config.env[parts[0].strip()] = parts[1].strip().strip('"')
            elif inst.command == "WORKDIR":
                config.working_dir = inst.arguments.strip()
            elif inst.command == "USER":
                config.user = inst.arguments.strip()
            elif inst.command == "EXPOSE":
                config.exposed_ports.extend(inst.arguments.split())
            elif inst.command == "VOLUME":
                config.volumes.extend(parse_json_or_split(inst.arguments))
        total_size = sum(self.image_store.layer_store().get(lid).size or 0 for lid in built_layers)
        image = Image(id=image_id, tags=[tag] if tag else [], layers=built_layers,
                      config=config, size=total_size)
        self.image_store.add(image)
        self._build_log.append(f"  -> IMAGE {image_id[:12]} tagged {tag}")
        return image
    def get_log(self) -> List[str]:
        return self._build_log

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Pod Manager
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PodSpec:
    """Specification for a pod (group of containers)."""
    id: str
    name: str
    namespace: str = "default"
    labels: Dict[str, str] = field(default_factory=dict)
    shared_namespaces: List[str] = field(default_factory=lambda: ["network", "ipc", "uts"])
    hostname: str = ""
    infra_image: str = "k8s.gcr.io/pause:3.6"
    dns_search: List[str] = field(default_factory=list)
    dns_server: List[str] = field(default_factory=list)
    def __repr__(self) -> str:
        return f"<PodSpec {self.name} ns={self.namespace}>"

@dataclass
class PodNetworkConfig:
    """Network configuration for a pod."""
    pod_id: str
    network_name: str = "podman"
    ip_address: str = ""
    mac_address: str = ""
    port_mappings: List[Dict[str, Any]] = field(default_factory=list)
    def __repr__(self) -> str:
        return f"<PodNetworkConfig {self.pod_id} ip={self.ip_address}>"

class InfraContainer:
    """The pause/hold container that maintains shared namespaces."""
    def __init__(self, pod_spec: PodSpec, runtime: ContainerRuntime) -> None:
        self.pod_spec = pod_spec
        self.runtime = runtime
        self.container_id = f"infra-{pod_spec.id}"
        self._created = False
    def __repr__(self) -> str:
        return f"<InfraContainer pod={self.pod_spec.name}>"
    def create(self) -> Process:
        spec = ContainerSpec(
            id=self.container_id, rootfs="/var/lib/containers/infra",
            args=["/pause"],
            hostname=self.pod_spec.hostname or self.pod_spec.name,
            namespaces=[LinuxNamespace(t) for t in self.pod_spec.shared_namespaces]
        )
        proc = self.runtime.create(spec)
        self._created = True
        return proc
    def start(self) -> bool:
        return self.runtime.start(self.container_id)
    def stop(self) -> bool:
        return self.runtime.stop(self.container_id)

class Pod:
    """A pod containing one or more containers."""
    def __init__(self, spec: PodSpec, runtime: ContainerRuntime) -> None:
        self.spec = spec
        self.runtime = runtime
        self.infra = InfraContainer(spec, runtime)
        self.containers: List[str] = []
        self.network: Optional[PodNetworkConfig] = None
        self._status: str = "created"
        self._created_at = datetime.now(timezone.utc)
    def __repr__(self) -> str:
        return f"<Pod {self.spec.name} containers={len(self.containers)} status={self._status}>"
    def start(self) -> bool:
        if not self.infra._created:
            self.infra.create()
        if not self.infra.start():
            return False
        for cid in self.containers:
            self.runtime.start(cid)
        self._status = "running"
        return True
    def stop(self) -> bool:
        for cid in self.containers:
            self.runtime.stop(cid)
        self.infra.stop()
        self._status = "exited"
        return True
    def add_container(self, container_id: str) -> bool:
        self.containers.append(container_id)
        return True
    def remove_container(self, container_id: str) -> bool:
        if container_id in self.containers:
            self.containers.remove(container_id)
            return True
        return False
    def inspect(self) -> Dict[str, Any]:
        return {"id": self.spec.id, "name": self.spec.name, "namespace": self.spec.namespace,
                "status": self._status, "infra_id": self.infra.container_id,
                "containers": self.containers, "shared_namespaces": self.spec.shared_namespaces,
                "labels": self.spec.labels, "created_at": self._created_at.isoformat()}

class PodManager:
    """Manage pods lifecycle."""
    def __init__(self, runtime: ContainerRuntime) -> None:
        self.runtime = runtime
        self._pods: Dict[str, Pod] = {}
    def __repr__(self) -> str:
        return f"<PodManager pods={len(self._pods)}>"
    def create(self, spec: PodSpec) -> Pod:
        pod = Pod(spec, self.runtime)
        self._pods[spec.id] = pod
        return pod
    def get(self, pod_id: str) -> Optional[Pod]:
        return self._pods.get(pod_id)
    def remove(self, pod_id: str, force: bool = False) -> bool:
        pod = self._pods.get(pod_id)
        if not pod:
            return False
        pod.stop()
        for cid in list(pod.containers):
            self.runtime.remove(cid, force=force)
        self.runtime.remove(pod.infra.container_id, force=force)
        del self._pods[pod_id]
        return True
    def list_pods(self) -> List[Dict[str, Any]]:
        return [pod.inspect() for pod in self._pods.values()]
    def start_pod(self, pod_id: str) -> bool:
        pod = self._pods.get(pod_id)
        if pod:
            return pod.start()
        return False
    def stop_pod(self, pod_id: str) -> bool:
        pod = self._pods.get(pod_id)
        if pod:
            return pod.stop()
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Registry Client
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RegistryAuth:
    """Authentication credentials for a container registry."""
    registry: str
    username: str = ""
    password: str = ""
    token: str = ""
    email: str = ""
    def __repr__(self) -> str:
        return f"<RegistryAuth {self.registry} user={self.username}>"

@dataclass
class Manifest:
    """OCI Image Manifest v2."""
    schema_version: int = 2
    media_type: str = "application/vnd.oci.image.manifest.v1+json"
    config: Dict[str, Any] = field(default_factory=dict)
    layers: List[Dict[str, Any]] = field(default_factory=list)
    annotations: Dict[str, str] = field(default_factory=dict)
    def __repr__(self) -> str:
        return f"<Manifest layers={len(self.layers)}>"
    def to_dict(self) -> Dict[str, Any]:
        return {"schemaVersion": self.schema_version, "mediaType": self.media_type,
                "config": self.config, "layers": self.layers, "annotations": self.annotations}

class RegistryClient:
    """Simulated OCI registry client for push/pull."""
    def __init__(self, registry_url: str, auth: Optional[RegistryAuth] = None) -> None:
        self.registry_url = registry_url.rstrip("/")
        self.auth = auth
        self._blobs: Dict[str, bytes] = {}
        self._manifests: Dict[str, Manifest] = {}
    def __repr__(self) -> str:
        return f"<RegistryClient {self.registry_url} blobs={len(self._blobs)}>"
    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json", "Accept": "application/vnd.oci.image.manifest.v1+json"}
        if self.auth and self.auth.token:
            h["Authorization"] = f"Bearer {self.auth.token}"
        return h
    def push_blob(self, name: str, digest: str, data: bytes) -> bool:
        self._blobs[digest] = data
        return True
    def pull_blob(self, digest: str) -> Optional[bytes]:
        return self._blobs.get(digest)
    def push_manifest(self, name: str, tag: str, manifest: Manifest) -> bool:
        self._manifests[f"{name}:{tag}"] = manifest
        return True
    def pull_manifest(self, name: str, tag: str) -> Optional[Manifest]:
        return self._manifests.get(f"{name}:{tag}")
    def list_tags(self, name: str) -> List[str]:
        return [k.split(":", 1)[1] for k in self._manifests.keys() if k.startswith(f"{name}:")]

class ImagePuller:
    """Orchestrate image pull from a registry."""
    def __init__(self, client: RegistryClient, image_store: ImageStore) -> None:
        self.client = client
        self.image_store = image_store
    def __repr__(self) -> str:
        return f"<ImagePuller client={self.client.registry_url}>"
    def pull(self, name: str, tag: str = "latest") -> Optional[Image]:
        manifest = self.client.pull_manifest(name, tag)
        if not manifest:
            return None
        layer_ids: List[str] = []
        for layer in manifest.layers:
            digest = layer.get("digest", "")
            data = self.client.pull_blob(digest)
            if data is not None:
                layer_id = hashlib.sha256(data).hexdigest()[:16]
                new_layer = ImageLayer(id=layer_id, digest=digest, size=len(data), files=[])
                self.image_store.layer_store().add(new_layer)
                layer_ids.append(layer_id)
        config = manifest.config
        image_id = hashlib.sha256(f"{name}:{tag}:{':'.join(layer_ids)}".encode()).hexdigest()[:16]
        img = Image(id=image_id, tags=[f"{name}:{tag}"], layers=layer_ids,
                    config=parse_config_dict(config))
        self.image_store.add(img)
        return img

class ImagePusher:
    """Orchestrate image push to a registry."""
    def __init__(self, client: RegistryClient, image_store: ImageStore) -> None:
        self.client = client
        self.image_store = image_store
    def __repr__(self) -> str:
        return f"<ImagePusher client={self.client.registry_url}>"
    def push(self, image_id: str, name: str, tag: str) -> bool:
        image = self.image_store.get(image_id)
        if not image:
            return False
        manifest = Manifest()
        manifest.config = {"mediaType": "application/vnd.oci.image.config.v1+json", "size": 1024,
                           "digest": hashlib.sha256(json.dumps(image.config.__dict__, default=str).encode()).hexdigest()}
        for layer_id in image.layers:
            layer = self.image_store.layer_store().get(layer_id)
            if layer:
                blob_data = json.dumps({"layer_id": layer_id, "files": layer.files}).encode()
                digest = f"sha256:{hashlib.sha256(blob_data).hexdigest()}"
                self.client.push_blob(name, digest, blob_data)
                manifest.layers.append({"mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                                        "size": layer.size or len(blob_data), "digest": digest})
        return self.client.push_manifest(name, tag, manifest)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Volume Manager
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Volume:
    """A container volume."""
    name: str
    driver: str = "local"
    mountpoint: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    options: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    in_use_by: List[str] = field(default_factory=list)
    def __repr__(self) -> str:
        return f"<Volume {self.name} driver={self.driver}>"

class VolumeDriver(ABC):
    """Abstract volume driver."""
    @abstractmethod
    def create(self, name: str, options: Dict[str, str]) -> Volume:
        raise NotImplementedError
    @abstractmethod
    def remove(self, volume: Volume) -> bool:
        raise NotImplementedError
    def __repr__(self) -> str:
        return f"<VolumeDriver>"

class LocalDriver(VolumeDriver):
    """Local filesystem volume driver."""
    def create(self, name: str, options: Dict[str, str]) -> Volume:
        mountpoint = options.get("mountpoint", f"/var/lib/volumes/{name}")
        return Volume(name=name, driver="local", mountpoint=mountpoint, options=options)
    def remove(self, volume: Volume) -> bool:
        return True

@dataclass
class BindMount:
    """Bind mount mapping host path to container path."""
    source: str
    target: str
    read_only: bool = False
    propagation: str = "rprivate"
    def __repr__(self) -> str:
        return f"<BindMount {self.source}:{self.target} ro={self.read_only}>"

@dataclass
class TmpfsMount:
    """In-memory tmpfs mount."""
    target: str
    size: str = "64m"
    mode: int = 1777
    def __repr__(self) -> str:
        return f"<TmpfsMount {self.target} size={self.size}>"

class VolumeManager:
    """Manage container volumes and mounts."""
    def __init__(self, db_path: Optional[str] = None) -> None:
        self._volumes: Dict[str, Volume] = {}
        self._drivers: Dict[str, VolumeDriver] = {"local": LocalDriver()}
        self._bind_mounts: Dict[str, List[BindMount]] = {}
        self._tmpfs_mounts: Dict[str, List[TmpfsMount]] = {}
        self._db_path = db_path
        if db_path:
            self._init_db()
    def __repr__(self) -> str:
        return f"<VolumeManager volumes={len(self._volumes)} drivers={len(self._drivers)}>"
    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS volumes (name TEXT PRIMARY KEY, driver TEXT, mountpoint TEXT, labels TEXT, options TEXT, created_at TEXT)")
        conn.commit()
        conn.close()
    def create(self, name: str, driver: str = "local", options: Optional[Dict[str, str]] = None) -> Volume:
        driver_impl = self._drivers.get(driver, LocalDriver())
        vol = driver_impl.create(name, options or {})
        self._volumes[name] = vol
        if self._db_path:
            conn = sqlite3.connect(self._db_path)
            conn.execute("INSERT OR REPLACE INTO volumes VALUES (?,?,?,?,?,?)",
                         (vol.name, vol.driver, vol.mountpoint, json.dumps(vol.labels),
                          json.dumps(vol.options), vol.created_at.isoformat()))
            conn.commit()
            conn.close()
        return vol
    def remove(self, name: str, force: bool = False) -> bool:
        vol = self._volumes.get(name)
        if not vol:
            return False
        if vol.in_use_by and not force:
            return False
        driver_impl = self._drivers.get(vol.driver, LocalDriver())
        if driver_impl.remove(vol):
            del self._volumes[name]
            return True
        return False
    def get(self, name: str) -> Optional[Volume]:
        return self._volumes.get(name)
    def list_volumes(self) -> List[Volume]:
        return list(self._volumes.values())
    def add_bind_mount(self, container_id: str, bind: BindMount) -> None:
        self._bind_mounts.setdefault(container_id, []).append(bind)
    def get_bind_mounts(self, container_id: str) -> List[BindMount]:
        return self._bind_mounts.get(container_id, [])
    def add_tmpfs_mount(self, container_id: str, tmpfs: TmpfsMount) -> None:
        self._tmpfs_mounts.setdefault(container_id, []).append(tmpfs)
    def get_tmpfs_mounts(self, container_id: str) -> List[TmpfsMount]:
        return self._tmpfs_mounts.get(container_id, [])

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Container Network
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Network:
    """A container network."""
    id: str
    name: str
    driver: str = "bridge"
    subnet: str = "10.88.0.0/16"
    gateway: str = "10.88.0.1"
    ip_range: str = "10.88.0.0/24"
    internal: bool = False
    dns_enabled: bool = True
    labels: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    containers: List[str] = field(default_factory=list)
    def __repr__(self) -> str:
        return f"<Network {self.name} {self.subnet} containers={len(self.containers)}>"

@dataclass
class PortMapping:
    """Host port to container port mapping."""
    host_port: int
    container_port: int
    protocol: str = "tcp"
    host_ip: str = "0.0.0.0"
    def __repr__(self) -> str:
        return f"<PortMapping {self.host_ip}:{self.host_port}->{self.container_port}/{self.protocol}>"

@dataclass
class DNSConfig:
    """DNS configuration for containers."""
    nameservers: List[str] = field(default_factory=lambda: ["8.8.8.8", "8.8.4.4"])
    search: List[str] = field(default_factory=list)
    options: List[str] = field(default_factory=list)
    def __repr__(self) -> str:
        return f"<DNSConfig nameservers={self.nameservers}>"

class NetworkManager:
    """Manage container networks."""
    def __init__(self) -> None:
        self._networks: Dict[str, Network] = {}
        self._port_mappings: Dict[str, List[PortMapping]] = {}
        self._dns: Dict[str, DNSConfig] = {}
        self._next_ip_counter = 2
    def __repr__(self) -> str:
        return f"<NetworkManager networks={len(self._networks)}>"
    def _allocate_ip(self, subnet: str) -> str:
        ip = f"10.88.0.{self._next_ip_counter}"
        self._next_ip_counter += 1
        return ip
    def create(self, name: str, driver: str = "bridge", subnet: str = "10.88.0.0/16",
               gateway: str = "10.88.0.1") -> Network:
        net_id = hashlib.sha256(name.encode()).hexdigest()[:12]
        net = Network(id=net_id, name=name, driver=driver, subnet=subnet, gateway=gateway)
        self._networks[net_id] = net
        return net
    def remove(self, network_id: str) -> bool:
        net = self._networks.get(network_id)
        if not net:
            return False
        if net.containers:
            return False
        del self._networks[network_id]
        return True
    def get(self, network_id: str) -> Optional[Network]:
        return self._networks.get(network_id)
    def list_networks(self) -> List[Network]:
        return list(self._networks.values())
    def connect(self, network_id: str, container_id: str) -> bool:
        net = self._networks.get(network_id)
        if not net:
            return False
        if container_id not in net.containers:
            net.containers.append(container_id)
        return True
    def disconnect(self, network_id: str, container_id: str) -> bool:
        net = self._networks.get(network_id)
        if not net:
            return False
        if container_id in net.containers:
            net.containers.remove(container_id)
        return True
    def add_port_mapping(self, container_id: str, mapping: PortMapping) -> None:
        self._port_mappings.setdefault(container_id, []).append(mapping)
    def get_port_mappings(self, container_id: str) -> List[PortMapping]:
        return self._port_mappings.get(container_id, [])
    def set_dns(self, container_id: str, dns: DNSConfig) -> None:
        self._dns[container_id] = dns
    def get_dns(self, container_id: str) -> DNSConfig:
        return self._dns.get(container_id, DNSConfig())

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — CLI / Demo
# ═══════════════════════════════════════════════════════════════════════════════

class PodmanCLI:
    """Simulated podman CLI interface."""
    def __init__(self, runtime: ContainerRuntime, image_store: ImageStore,
                 pod_manager: PodManager, volume_manager: VolumeManager,
                 network_manager: NetworkManager) -> None:
        self.runtime = runtime
        self.image_store = image_store
        self.pod_manager = pod_manager
        self.volume_manager = volume_manager
        self.network_manager = network_manager
    def __repr__(self) -> str:
        return "<PodmanCLI>"
    def run(self, args: List[str]) -> Dict[str, Any]:
        if not args:
            return {"error": "no command"}
        cmd = args[0]
        if cmd == "run":
            return self._cmd_run(args[1:])
        elif cmd == "build":
            return self._cmd_build(args[1:])
        elif cmd == "pod":
            return self._cmd_pod(args[1:])
        elif cmd == "image":
            return self._cmd_image(args[1:])
        elif cmd == "volume":
            return self._cmd_volume(args[1:])
        elif cmd == "network":
            return self._cmd_network(args[1:])
        elif cmd == "ps":
            return {"containers": self.runtime.list_containers(all_containers="-a" in args)}
        elif cmd == "inspect":
            return self.runtime.inspect(args[1]) if len(args) > 1 else {"error": "missing ID"}
        return {"error": f"unknown command: {cmd}"}
    def _cmd_run(self, args: List[str]) -> Dict[str, Any]:
        image_tag = args[0] if args else "latest"
        image = self.image_store.resolve(image_tag)
        if not image:
            return {"error": f"image not found: {image_tag}"}
        spec = ContainerSpec(id=f"c-{hashlib.sha256(image_tag.encode()).hexdigest()[:8]}",
                             rootfs=f"/var/lib/containers/{image_tag}",
                             args=image.config.cmd or ["sh"], env=image.config.env,
                             cwd=image.config.working_dir or "/", user=image.config.user,
                             labels=image.config.labels, hostname=image_tag.replace(":", "-"))
        proc = self.runtime.create(spec)
        self.runtime.start(spec.id)
        return {"created": spec.id, "status": proc.status}
    def _cmd_build(self, args: List[str]) -> Dict[str, Any]:
        tag = "latest"
        for i, a in enumerate(args):
            if a == "-t" and i + 1 < len(args):
                tag = args[i + 1]
        return {"built": tag, "log": ["STEP 1/1: stub build"]}
    def _cmd_pod(self, args: List[str]) -> Dict[str, Any]:
        if not args:
            return {"pods": self.pod_manager.list_pods()}
        sub = args[0]
        if sub == "create":
            name = args[1] if len(args) > 1 else "pod"
            pod_id = hashlib.sha256(name.encode()).hexdigest()[:12]
            spec = PodSpec(id=pod_id, name=name)
            pod = self.pod_manager.create(spec)
            return {"pod_id": pod_id, "name": name}
        elif sub == "start":
            return {"started": self.pod_manager.start_pod(args[1])} if len(args) > 1 else {"error": "missing ID"}
        elif sub == "stop":
            return {"stopped": self.pod_manager.stop_pod(args[1])} if len(args) > 1 else {"error": "missing ID"}
        elif sub == "rm":
            return {"removed": self.pod_manager.remove(args[1])} if len(args) > 1 else {"error": "missing ID"}
        return {"error": f"unknown pod subcommand: {sub}"}
    def _cmd_image(self, args: List[str]) -> Dict[str, Any]:
        if not args:
            return {"images": [img.__dict__ for img in self.image_store.list_images()]}
        sub = args[0]
        if sub == "ls":
            return {"images": [i.tags for i in self.image_store.list_images()]}
        elif sub == "rm":
            return {"removed": self.image_store.remove(args[1])} if len(args) > 1 else {"error": "missing ID"}
        return {"error": f"unknown image subcommand: {sub}"}
    def _cmd_volume(self, args: List[str]) -> Dict[str, Any]:
        if not args:
            return {"volumes": [v.name for v in self.volume_manager.list_volumes()]}
        sub = args[0]
        if sub == "create":
            name = args[1] if len(args) > 1 else "vol"
            vol = self.volume_manager.create(name)
            return {"volume": vol.name}
        elif sub == "rm":
            return {"removed": self.volume_manager.remove(args[1])} if len(args) > 1 else {"error": "missing name"}
        return {"error": f"unknown volume subcommand: {sub}"}
    def _cmd_network(self, args: List[str]) -> Dict[str, Any]:
        if not args:
            return {"networks": [n.name for n in self.network_manager.list_networks()]}
        sub = args[0]
        if sub == "create":
            name = args[1] if len(args) > 1 else "net"
            net = self.network_manager.create(name)
            return {"network": net.name, "id": net.id}
        elif sub == "rm":
            return {"removed": self.network_manager.remove(args[1])} if len(args) > 1 else {"error": "missing ID"}
        return {"error": f"unknown network subcommand: {sub}"}

# ═══════════════════════════════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════════════════════════════

def random_size() -> int:
    return random.randint(1024, 10485760)

def simulate_files(instruction: DockerfileInstruction) -> List[str]:
    if instruction.command == "COPY":
        return [instruction.arguments.split()[0]]
    elif instruction.command == "RUN":
        return [f"/usr/bin/{hashlib.sha256(instruction.arguments.encode()).hexdigest()[:8]}"]
    return []

def parse_json_or_split(value: str) -> List[str]:
    value = value.strip()
    if value.startswith("["):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [str(parsed)]
        except json.JSONDecodeError:
            pass
    return value.split()

def parse_config_dict(config_dict: Dict[str, Any]) -> ImageConfig:
    cfg = ImageConfig()
    if "Env" in config_dict:
        for env in config_dict["Env"]:
            if "=" in env:
                k, v = env.split("=", 1)
                cfg.env[k] = v
    if "Cmd" in config_dict:
        cfg.cmd = config_dict["Cmd"]
    if "Entrypoint" in config_dict:
        cfg.entrypoint = config_dict["Entrypoint"]
    if "WorkingDir" in config_dict:
        cfg.working_dir = config_dict["WorkingDir"]
    if "User" in config_dict:
        cfg.user = config_dict["User"]
    if "ExposedPorts" in config_dict:
        cfg.exposed_ports = list(config_dict["ExposedPorts"].keys())
    return cfg

def demo() -> None:
    print("=" * 60)
    print("PODMAN NATIVE — Full System Demo")
    print("=" * 60)
    runtime = ContainerRuntime()
    image_store = ImageStore()
    pod_manager = PodManager(runtime)
    volume_manager = VolumeManager()
    network_manager = NetworkManager()
    cli = PodmanCLI(runtime, image_store, pod_manager, volume_manager, network_manager)

    # 1. Build image
    print("\n[1] Build Image from Dockerfile:")
    dockerfile = """FROM alpine:latest
RUN apk add --no-cache python3
COPY app.py /app/
WORKDIR /app
ENV APP_ENV=production
EXPOSE 8080
CMD ["python3", "app.py"]"""
    builder = ImageBuilder(image_store)
    context = BuildContext(path=".", files={"app.py": "print('hello')"})
    image = builder.build(dockerfile, context, tag="myapp:latest")
    print(f"  Built: {image}")
    print(f"  Layers: {[l[:12] for l in image.layers]}")
    print(f"  Config: entrypoint={image.config.entrypoint} cmd={image.config.cmd}")
    print(f"  Size: {image.size} bytes")
    for line in builder.get_log():
        print(f"    {line}")

    # 2. Create pod
    print("\n[2] Create Pod:")
    pod_spec = PodSpec(id="pod-001", name="web-services",
                       labels={"app": "web", "tier": "frontend"}, hostname="web-services")
    pod = pod_manager.create(pod_spec)
    print(f"  Created: {pod}")

    # 3. Run container in pod
    print("\n[3] Run Container in Pod:")
    spec = ContainerSpec(id="web-01", rootfs="/var/lib/containers/web-01",
                         args=["python3", "app.py"],
                         env={"APP_ENV": "production", "PORT": "8080"},
                         cwd="/app", user="appuser",
                         labels={"app": "web", "pod": "web-services"},
                         hostname="web-services",
                         cgroups=[CgroupLimit("memory", 536870912, "bytes"),
                                  CgroupLimit("cpu", 100000, "us")])
    proc = runtime.create(spec)
    runtime.start(spec.id)
    pod.add_container(spec.id)
    print(f"  Container: {spec.id} status={proc.status} pid={proc.pid}")
    print(f"  Inspect: {runtime.inspect(spec.id)}")

    # 4. Registry push/pull
    print("\n[4] Registry Push/Pull:")
    auth = RegistryAuth(registry="localhost:5000", username="admin", password="secret")
    client = RegistryClient("http://localhost:5000", auth)
    pusher = ImagePusher(client, image_store)
    push_ok = pusher.push(image.id, "myapp", "latest")
    print(f"  Push: {'OK' if push_ok else 'FAIL'}")
    puller = ImagePuller(client, image_store)
    pulled = puller.pull("myapp", "latest")
    print(f"  Pulled: {pulled}")

    # 5. Volume management
    print("\n[5] Volume Management:")
    vol1 = volume_manager.create("web-data", driver="local",
                                  options={"mountpoint": "/var/lib/volumes/web-data"})
    vol2 = volume_manager.create("cache", driver="local")
    print(f"  Created: {vol1}")
    print(f"  Created: {vol2}")
    print(f"  All: {[v.name for v in volume_manager.list_volumes()]}")
    volume_manager.add_bind_mount(spec.id, BindMount("/host/web", "/app/data"))
    print(f"  Bind mounts: {volume_manager.get_bind_mounts(spec.id)}")

    # 6. Network management
    print("\n[6] Network Management:")
    net = network_manager.create("web-net", driver="bridge",
                                  subnet="10.88.10.0/24", gateway="10.88.10.1")
    print(f"  Created: {net}")
    network_manager.connect(net.id, spec.id)
    network_manager.add_port_mapping(spec.id, PortMapping(8080, 80, "tcp"))
    print(f"  Connected {spec.id} to {net.name}")
    print(f"  Port mappings: {network_manager.get_port_mappings(spec.id)}")
    dns = DNSConfig(nameservers=["10.88.10.1"], search=["web-net.local"])
    network_manager.set_dns(spec.id, dns)
    print(f"  DNS: {network_manager.get_dns(spec.id)}")

    # 7. Pod lifecycle
    print("\n[7] Pod Lifecycle:")
    pod.start()
    print(f"  Started: {pod.inspect()}")
    pod.stop()
    print(f"  Stopped: status={pod._status}")

    # 8. CLI commands
    print("\n[8] CLI Commands:")
    print(f"  ps: {cli.run(['ps'])}")
    print(f"  inspect: {cli.run(['inspect', spec.id])}")
    print(f"  pod: {cli.run(['pod'])}")
    print(f"  volume: {cli.run(['volume'])}")
    print(f"  network: {cli.run(['network'])}")
    print(f"  image ls: {cli.run(['image', 'ls'])}")

    # 9. System stats
    print("\n[9] System Stats:")
    print(f"  {runtime}")
    print(f"  {image_store}")
    print(f"  {pod_manager}")
    print(f"  {volume_manager}")
    print(f"  {network_manager}")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)

if __name__ == "__main__":
    demo()
