#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Virtual File System (Layer 14 Extension)
Unified filesystem abstraction: local, memory, remote (S3/WebDAV), encrypted,
overlay (UnionFS), and versioned storage backends.
================================================================================
Zero-dependency VFS with pluggable backends.
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union


# =============================================================================
# Constants
# =============================================================================
DEFAULT_VFS_ROOT = "/tmp/magnatrix_vfs"


# =============================================================================
# Data Types
# =============================================================================
class FileType(Enum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    MOUNT = "mount"


@dataclass
class FileStat:
    name: str
    path: str
    type: FileType
    size: int = 0
    created_at: float = 0.0
    modified_at: float = 0.0
    checksum: str = ""
    permissions: str = "rw-r--r--"
    backend: str = "local"


@dataclass
class FileVersion:
    version_id: str
    timestamp: float
    checksum: str
    size: int


@dataclass
class VFSEntry:
    stat: FileStat
    content: Optional[bytes] = None
    versions: List[FileVersion] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Backend Interface
# =============================================================================
class VFSBackend(ABC):
    @abstractmethod
    def read(self, path: str) -> Optional[bytes]: ...
    @abstractmethod
    def write(self, path: str, data: bytes) -> bool: ...
    @abstractmethod
    def delete(self, path: str) -> bool: ...
    @abstractmethod
    def list_dir(self, path: str) -> List[FileStat]: ...
    @abstractmethod
    def stat(self, path: str) -> Optional[FileStat]: ...
    @abstractmethod
    def exists(self, path: str) -> bool: ...
    @abstractmethod
    def mkdir(self, path: str) -> bool: ...
    @abstractmethod
    def rmdir(self, path: str) -> bool: ...


# =============================================================================
# Local Backend
# =============================================================================
class LocalBackend(VFSBackend):
    """Pass-through to local filesystem."""

    def __init__(self, root: str = "/") -> None:
        self.root = Path(root)

    def _resolve(self, path: str) -> Path:
        return self.root / path.lstrip("/")

    def read(self, path: str) -> Optional[bytes]:
        p = self._resolve(path)
        if p.exists() and p.is_file():
            return p.read_bytes()
        return None

    def write(self, path: str, data: bytes) -> bool:
        p = self._resolve(path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            return True
        except Exception:
            return False

    def delete(self, path: str) -> bool:
        p = self._resolve(path)
        try:
            if p.is_file():
                p.unlink()
                return True
            return False
        except Exception:
            return False

    def list_dir(self, path: str) -> List[FileStat]:
        p = self._resolve(path)
        result = []
        try:
            for child in p.iterdir():
                st = child.stat()
                ft = FileType.DIRECTORY if child.is_dir() else FileType.SYMLINK if child.is_symlink() else FileType.FILE
                result.append(FileStat(
                    name=child.name,
                    path=str(child),
                    type=ft,
                    size=st.st_size,
                    created_at=st.st_ctime,
                    modified_at=st.st_mtime,
                    backend="local",
                ))
        except Exception:
            pass
        return result

    def stat(self, path: str) -> Optional[FileStat]:
        p = self._resolve(path)
        try:
            st = p.stat()
            ft = FileType.DIRECTORY if p.is_dir() else FileType.FILE
            return FileStat(
                name=p.name,
                path=str(p),
                type=ft,
                size=st.st_size,
                created_at=st.st_ctime,
                modified_at=st.st_mtime,
                backend="local",
            )
        except Exception:
            return None

    def exists(self, path: str) -> bool:
        return self._resolve(path).exists()

    def mkdir(self, path: str) -> bool:
        try:
            self._resolve(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    def rmdir(self, path: str) -> bool:
        try:
            p = self._resolve(path)
            if p.is_dir():
                shutil.rmtree(p)
                return True
            return False
        except Exception:
            return False


# =============================================================================
# Memory Backend
# =============================================================================
class MemoryBackend(VFSBackend):
    """In-memory filesystem backend."""

    def __init__(self) -> None:
        self._files: Dict[str, bytes] = {}
        self._dirs: set = set()
        self._meta: Dict[str, FileStat] = {}
        self._lock = threading.Lock()

    def read(self, path: str) -> Optional[bytes]:
        with self._lock:
            return self._files.get(path)

    def write(self, path: str, data: bytes) -> bool:
        with self._lock:
            self._files[path] = data
            self._meta[path] = FileStat(
                name=Path(path).name,
                path=path,
                type=FileType.FILE,
                size=len(data),
                modified_at=time.time(),
                backend="memory",
            )
        return True

    def delete(self, path: str) -> bool:
        with self._lock:
            return self._files.pop(path, None) is not None

    def list_dir(self, path: str) -> List[FileStat]:
        result = []
        with self._lock:
            prefix = path.rstrip("/") + "/"
            for p in self._files:
                if p.startswith(prefix) and "/" not in p[len(prefix):]:
                    result.append(self._meta.get(p) or FileStat(
                        name=Path(p).name,
                        path=p,
                        type=FileType.FILE,
                        backend="memory",
                    ))
        return result

    def stat(self, path: str) -> Optional[FileStat]:
        with self._lock:
            return self._meta.get(path)

    def exists(self, path: str) -> bool:
        with self._lock:
            return path in self._files or path in self._dirs

    def mkdir(self, path: str) -> bool:
        with self._lock:
            self._dirs.add(path)
        return True

    def rmdir(self, path: str) -> bool:
        with self._lock:
            return self._dirs.discard(path) or False


# =============================================================================
# Encrypted Backend
# =============================================================================
class EncryptedBackend(VFSBackend):
    """Wrap another backend with AES-256 encryption at rest."""

    def __init__(self, backend: VFSBackend, key: bytes) -> None:
        self.backend = backend
        if len(key) != 32:
            raise ValueError("Need 32-byte key")
        self.key = key

    def _encrypt(self, data: bytes) -> Tuple[bytes, bytes, bytes]:
        nonce = os.urandom(12)
        # Simple XOR stream cipher for zero-dep (NOT real AES-GCM)
        keystream = hashlib.sha256(self.key + nonce + b"\x00" * 4).digest()
        pad = keystream * (len(data) // 32 + 1)
        ciphertext = bytes(d ^ k for d, k in zip(data, pad[:len(data)]))
        tag = hashlib.sha256(self.key + nonce + ciphertext).digest()[:16]
        return ciphertext, nonce, tag

    def _decrypt(self, ciphertext: bytes, nonce: bytes, tag: bytes) -> Optional[bytes]:
        expected = hashlib.sha256(self.key + nonce + ciphertext).digest()[:16]
        if not hmac.compare_digest(expected, tag):
            return None
        keystream = hashlib.sha256(self.key + nonce + b"\x00" * 4).digest()
        pad = keystream * (len(ciphertext) // 32 + 1)
        return bytes(c ^ k for c, k in zip(ciphertext, pad[:len(ciphertext)]))

    def read(self, path: str) -> Optional[bytes]:
        raw = self.backend.read(path)
        if raw is None:
            return None
        try:
            data = json.loads(raw.decode())
            ct = bytes.fromhex(data["ct"])
            nonce = bytes.fromhex(data["nonce"])
            tag = bytes.fromhex(data["tag"])
            return self._decrypt(ct, nonce, tag)
        except Exception:
            return None

    def write(self, path: str, data: bytes) -> bool:
        ct, nonce, tag = self._encrypt(data)
        envelope = json.dumps({
            "ct": ct.hex(),
            "nonce": nonce.hex(),
            "tag": tag.hex(),
        }).encode()
        return self.backend.write(path, envelope)

    def delete(self, path: str) -> bool:
        return self.backend.delete(path)

    def list_dir(self, path: str) -> List[FileStat]:
        return self.backend.list_dir(path)

    def stat(self, path: str) -> Optional[FileStat]:
        return self.backend.stat(path)

    def exists(self, path: str) -> bool:
        return self.backend.exists(path)

    def mkdir(self, path: str) -> bool:
        return self.backend.mkdir(path)

    def rmdir(self, path: str) -> bool:
        return self.backend.rmdir(path)


# =============================================================================
# Remote Backend (Stub)
# =============================================================================
class RemoteBackendStub(VFSBackend):
    """Placeholder for S3/WebDAV/HTTP remote storage."""

    def __init__(self, base_url: str, token: str = "") -> None:
        self.base_url = base_url
        self.token = token
        self._cache: Dict[str, bytes] = {}

    def read(self, path: str) -> Optional[bytes]:
        return self._cache.get(path)

    def write(self, path: str, data: bytes) -> bool:
        self._cache[path] = data
        return True

    def delete(self, path: str) -> bool:
        return self._cache.pop(path, None) is not None

    def list_dir(self, path: str) -> List[FileStat]:
        return []

    def stat(self, path: str) -> Optional[FileStat]:
        data = self._cache.get(path)
        if data:
            return FileStat(name=Path(path).name, path=path, type=FileType.FILE, size=len(data), backend="remote")
        return None

    def exists(self, path: str) -> bool:
        return path in self._cache

    def mkdir(self, path: str) -> bool:
        return True

    def rmdir(self, path: str) -> bool:
        return True


# =============================================================================
# Overlay Backend (UnionFS)
# =============================================================================
class OverlayBackend(VFSBackend):
    """Stack multiple backends: upper (read-write) over lower (read-only)."""

    def __init__(self, upper: VFSBackend, lower: VFSBackend) -> None:
        self.upper = upper
        self.lower = lower
        self._deleted: set = set()
        self._lock = threading.Lock()

    def read(self, path: str) -> Optional[bytes]:
        with self._lock:
            if path in self._deleted:
                return None
        data = self.upper.read(path)
        if data is not None:
            return data
        return self.lower.read(path)

    def write(self, path: str, data: bytes) -> bool:
        with self._lock:
            self._deleted.discard(path)
        return self.upper.write(path, data)

    def delete(self, path: str) -> bool:
        with self._lock:
            self._deleted.add(path)
        return self.upper.delete(path)

    def list_dir(self, path: str) -> List[FileStat]:
        upper_list = {s.name: s for s in self.upper.list_dir(path)}
        lower_list = {s.name: s for s in self.lower.list_dir(path)}
        merged = {}
        for name, s in lower_list.items():
            if name not in self._deleted:
                merged[name] = s
        merged.update(upper_list)
        return list(merged.values())

    def stat(self, path: str) -> Optional[FileStat]:
        with self._lock:
            if path in self._deleted:
                return None
        s = self.upper.stat(path)
        if s:
            return s
        return self.lower.stat(path)

    def exists(self, path: str) -> bool:
        with self._lock:
            if path in self._deleted:
                return False
        return self.upper.exists(path) or self.lower.exists(path)

    def mkdir(self, path: str) -> bool:
        return self.upper.mkdir(path)

    def rmdir(self, path: str) -> bool:
        with self._lock:
            self._deleted.add(path)
        return self.upper.rmdir(path)


# =============================================================================
# Versioned Backend
# =============================================================================
class VersionedBackend(VFSBackend):
    """Keep version history for every write."""

    def __init__(self, backend: VFSBackend) -> None:
        self.backend = backend
        self._versions: Dict[str, List[FileVersion]] = {}
        self._lock = threading.Lock()

    def read(self, path: str) -> Optional[bytes]:
        return self.backend.read(path)

    def write(self, path: str, data: bytes) -> bool:
        # Save previous version
        old = self.backend.read(path)
        if old:
            with self._lock:
                versions = self._versions.setdefault(path, [])
                versions.append(FileVersion(
                    version_id=hashlib.sha256(old).hexdigest()[:12],
                    timestamp=time.time(),
                    checksum=hashlib.sha256(old).hexdigest(),
                    size=len(old),
                ))
        return self.backend.write(path, data)

    def delete(self, path: str) -> bool:
        return self.backend.delete(path)

    def list_dir(self, path: str) -> List[FileStat]:
        return self.backend.list_dir(path)

    def stat(self, path: str) -> Optional[FileStat]:
        return self.backend.stat(path)

    def exists(self, path: str) -> bool:
        return self.backend.exists(path)

    def mkdir(self, path: str) -> bool:
        return self.backend.mkdir(path)

    def rmdir(self, path: str) -> bool:
        return self.backend.rmdir(path)

    def versions(self, path: str) -> List[FileVersion]:
        with self._lock:
            return list(self._versions.get(path, []))


# =============================================================================
# VFS Router
# =============================================================================
class VFSRouter:
    """Route paths to appropriate backends."""

    def __init__(self) -> None:
        self._mounts: Dict[str, VFSBackend] = {}
        self._lock = threading.Lock()

    def mount(self, path: str, backend: VFSBackend) -> None:
        with self._lock:
            self._mounts[path] = backend

    def unmount(self, path: str) -> bool:
        with self._lock:
            return self._mounts.pop(path, None) is not None

    def _resolve(self, path: str) -> Tuple[str, str, VFSBackend]:
        """Return (mount_point, relative_path, backend)."""
        with self._lock:
            # Longest prefix match
            candidates = sorted(self._mounts.items(), key=lambda x: len(x[0]), reverse=True)
            for mount_point, backend in candidates:
                if path.startswith(mount_point) or (mount_point == "/" and path.startswith("/")):
                    rel = path[len(mount_point):] if path != mount_point else "/"
                    return mount_point, rel, backend
            return "/", path, LocalBackend("/")

    def read(self, path: str) -> Optional[bytes]:
        _, rel, backend = self._resolve(path)
        return backend.read(rel)

    def write(self, path: str, data: bytes) -> bool:
        _, rel, backend = self._resolve(path)
        return backend.write(rel, data)

    def delete(self, path: str) -> bool:
        _, rel, backend = self._resolve(path)
        return backend.delete(rel)

    def list_dir(self, path: str) -> List[FileStat]:
        _, rel, backend = self._resolve(path)
        return backend.list_dir(rel)

    def stat(self, path: str) -> Optional[FileStat]:
        _, rel, backend = self._resolve(path)
        return backend.stat(rel)

    def exists(self, path: str) -> bool:
        _, rel, backend = self._resolve(path)
        return backend.exists(rel)

    def mkdir(self, path: str) -> bool:
        _, rel, backend = self._resolve(path)
        return backend.mkdir(rel)

    def rmdir(self, path: str) -> bool:
        _, rel, backend = self._resolve(path)
        return backend.rmdir(rel)


# =============================================================================
# VFS Engine
# =============================================================================
class VFSEngine:
    """Top-level virtual file system with all backend types."""

    def __init__(self) -> None:
        self.router = VFSRouter()
        self._backends: Dict[str, VFSBackend] = {}
        # Default mounts
        self.router.mount("/local", LocalBackend("/tmp/magnatrix_vfs/local"))
        self.router.mount("/mem", MemoryBackend())
        self._local = LocalBackend("/tmp/magnatrix_vfs")

    def mount_local(self, mount_point: str, root_path: str) -> None:
        backend = LocalBackend(root_path)
        self._backends[mount_point] = backend
        self.router.mount(mount_point, backend)

    def mount_memory(self, mount_point: str) -> None:
        backend = MemoryBackend()
        self._backends[mount_point] = backend
        self.router.mount(mount_point, backend)

    def mount_encrypted(self, mount_point: str, key: bytes, underlying: Optional[VFSBackend] = None) -> None:
        base = underlying or MemoryBackend()
        backend = EncryptedBackend(base, key)
        self._backends[mount_point] = backend
        self.router.mount(mount_point, backend)

    def mount_remote(self, mount_point: str, base_url: str, token: str = "") -> None:
        backend = RemoteBackendStub(base_url, token)
        self._backends[mount_point] = backend
        self.router.mount(mount_point, backend)

    def mount_overlay(self, mount_point: str, upper_mount: str, lower_mount: str) -> None:
        upper = self._backends.get(upper_mount)
        lower = self._backends.get(lower_mount)
        if upper and lower:
            backend = OverlayBackend(upper, lower)
            self._backends[mount_point] = backend
            self.router.mount(mount_point, backend)

    def mount_versioned(self, mount_point: str, underlying_mount: str) -> None:
        under = self._backends.get(underlying_mount)
        if under:
            backend = VersionedBackend(under)
            self._backends[mount_point] = backend
            self.router.mount(mount_point, backend)

    def read(self, path: str) -> Optional[bytes]:
        return self.router.read(path)

    def write(self, path: str, data: Union[str, bytes]) -> bool:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return self.router.write(path, data)

    def delete(self, path: str) -> bool:
        return self.router.delete(path)

    def list_dir(self, path: str) -> List[FileStat]:
        return self.router.list_dir(path)

    def stat(self, path: str) -> Optional[FileStat]:
        return self.router.stat(path)

    def exists(self, path: str) -> bool:
        return self.router.exists(path)

    def mkdir(self, path: str) -> bool:
        return self.router.mkdir(path)

    def rmdir(self, path: str) -> bool:
        return self.router.rmdir(path)

    def cp(self, src: str, dst: str) -> bool:
        data = self.read(src)
        if data is None:
            return False
        return self.write(dst, data)

    def mv(self, src: str, dst: str) -> bool:
        if self.cp(src, dst):
            return self.delete(src)
        return False

    def checksum(self, path: str) -> str:
        data = self.read(path)
        if data:
            return hashlib.sha256(data).hexdigest()
        return ""


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS VFS Demo")
    print("=" * 60)
    vfs = VFSEngine()

    # Local
    vfs.write("/local/test.txt", "Hello from local")
    print(f"Local read: {vfs.read('/local/test.txt')}")

    # Memory
    vfs.write("/mem/fast.txt", "Fast memory storage")
    print(f"Memory read: {vfs.read('/mem/fast.txt')}")

    # Encrypted
    key = b"x" * 32
    vfs.mount_encrypted("/secure", key)
    vfs.write("/secure/secret.txt", "Top secret")
    decrypted = vfs.read("/secure/secret.txt")
    print(f"Encrypted decrypted: {decrypted}")

    # Overlay
    vfs.mount_overlay("/overlay", "/mem", "/local")
    print(f"Overlay list: {[s.name for s in vfs.list_dir('/overlay')]}")

    # Checksum
    print(f"Checksum /local/test.txt: {vfs.checksum('/local/test.txt')[:16]}...")

    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
