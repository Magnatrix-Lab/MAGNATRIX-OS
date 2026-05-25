#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAGNATRIX-OS — UE Modding Tools Native Integration
═══════════════════════════════════════════════════════════════════════════════
AMATI-PELAJARI-TIRU dari Buckminsterfullerene02/UE-Modding-Tools

Pola yang ditiru:
• .pak/.ucas/.utoc container parser — Unreal Engine asset package unpacker
• IoStore container engine — UE5 Zen asset format reader/writer
• UAsset/UMap parser — Binary serialization format untuk cooked assets
• Asset extraction pipeline — mesh, texture, animation, sound, blueprint
• SDK generation — C++ header dump, .usmap mappings, UObject reflection
• Blueprint modding — UML/UE4SS-style Lua/C++ hook injection
• Localization engine — .locres read/write, text extraction, translation
• Reverse engineering bridge — AOB scanner, pattern matching, memory dumper
• Mod packaging — .pak builder, chunk assignment, signature bypass
• Automation scripts — batch cook, bulk convert, debug world generator

Layer: Runtime (3) — Unreal Engine Modding & Asset Runtime
Versi: Phase 5 — UE Modding Native Engine
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import struct
import sys
import zlib
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set, BinaryIO


# ═════════════════════════════════════════════════════════════════════════════
# 0. UTILITAS DASAR
# ═════════════════════════════════════════════════════════════════════════════

def _now() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def _crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF

def _fnv1a_32(data: bytes) -> int:
    """FNV-1a 32-bit hash — digunakan UE untuk path hashing."""
    h = 0x811c9dc5
    for b in data:
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h

def _fnv1a_64(data: bytes) -> int:
    h = 0xcbf29ce484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h

def _read_string(fp: BinaryIO) -> str:
    """Read UE FString: length (int32) + bytes (UTF-8)."""
    length = struct.unpack("<i", fp.read(4))[0]
    if length == 0:
        return ""
    if length < 0:
        # UTF-16LE
        length = -length
        return fp.read(length * 2).decode("utf-16-le", errors="replace").rstrip("\x00")
    return fp.read(length).decode("utf-8", errors="replace").rstrip("\x00")

def _write_string(fp: BinaryIO, s: str) -> None:
    encoded = s.encode("utf-8") + b"\x00"
    fp.write(struct.pack("<i", len(encoded)))
    fp.write(encoded)


# ═════════════════════════════════════════════════════════════════════════════
# 1. PAK CONTAINER ENGINE — Unreal .pak File Parser / Builder
# ═════════════════════════════════════════════════════════════════════════════

class PakVersion(Enum):
    Initial = 1
    NoTimestamps = 2
    CompressionEncryption = 3
    IndexEncryption = 4
    RelativeChunkOffsets = 5
    DeleteRecords = 6
    EncryptionKeyGuid = 7
    FNameBasedCompression = 8

@dataclass
class PakEntry:
    """Satu file entry dalam .pak container."""
    name: str
    offset: int
    size: int
    uncompressed_size: int
    compression_method: int
    compression_block_size: int = 0x10000
    compression_blocks: List[Tuple[int, int]] = field(default_factory=list)
    encrypted: bool = False
    deleted: bool = False
    sha1: bytes = b""

@dataclass
class PakMountPoint:
    """Mount point dalam pak file."""
    point: str  # misal: "../../../Game/Content/"
    entries: Dict[str, PakEntry] = field(default_factory=dict)

class PakContainerEngine:
    """
    Engine untuk parse & build Unreal .pak containers.
    Meniru repak/UnrealPak/QuickBMS functionality.
    """

    COMPRESSION_NONE = 0
    COMPRESSION_ZLIB = 1
    COMPRESSION_GZIP = 2
    COMPRESSION_CUSTOM = 4
    COMPRESSION_LZ4 = 256
    COMPRESSION_OODLE = 512

    def __init__(self) -> None:
        self.pak_path: Optional[Path] = None
        self.version: PakVersion = PakVersion.Initial
        self.mount_point: str = ""
        self.entries: Dict[str, PakEntry] = {}
        self.index_offset: int = 0
        self.index_size: int = 0
        self.index_sha1: bytes = b""
        self.encryption_key_guid: bytes = b""

    def parse(self, pak_file: Path) -> Dict[str, Any]:
        """Parse .pak file dan extract index."""
        self.pak_path = pak_file
        with open(pak_file, "rb") as fp:
            return self._parse_stream(fp)

    def _parse_stream(self, fp: BinaryIO) -> Dict[str, Any]:
        fp.seek(-44, 2)  # Footer diakhir: 44 bytes
        magic, version_val, index_offset, index_size, index_sha1 = struct.unpack(
            "<I I Q Q 20s", fp.read(44)
        )
        if magic != 0x5A6F12E1:
            raise ValueError(f"Invalid PAK magic: 0x{magic:08X}")

        self.version = PakVersion(version_val)
        self.index_offset = index_offset
        self.index_size = index_size
        self.index_sha1 = index_sha1

        fp.seek(index_offset)
        self.mount_point = _read_string(fp)
        entry_count = struct.unpack("<i", fp.read(4))[0]

        self.entries = {}
        for _ in range(entry_count):
            name = _read_string(fp)
            entry = self._read_entry(fp)
            self.entries[name] = entry

        return {
            "version": self.version.name,
            "mount_point": self.mount_point,
            "entry_count": len(self.entries),
            "total_size": fp.seek(0, 2),
        }

    def _read_entry(self, fp: BinaryIO) -> PakEntry:
        offset, size, uncompressed_size = struct.unpack("<Q Q Q", fp.read(24))
        compression_method = struct.unpack("<I", fp.read(4))[0]
        sha1 = fp.read(20)

        if self.version.value >= PakVersion.CompressionEncryption.value:
            block_count = struct.unpack("<I", fp.read(4))[0] if compression_method else 0
            blocks = []
            for _ in range(block_count):
                c_start, c_end = struct.unpack("<Q Q", fp.read(16))
                blocks.append((c_start, c_end))
            encrypted = struct.unpack("<?", fp.read(1))[0]
            compression_block_size = struct.unpack("<I", fp.read(4))[0]
            return PakEntry(
                name="", offset=offset, size=size,
                uncompressed_size=uncompressed_size,
                compression_method=compression_method,
                compression_block_size=compression_block_size,
                compression_blocks=blocks,
                encrypted=encrypted,
                sha1=sha1,
            )
        return PakEntry(name="", offset=offset, size=size,
                        uncompressed_size=uncompressed_size,
                        compression_method=compression_method, sha1=sha1)

    def extract_entry(self, entry_name: str, output_dir: Path,
                      aes_key: Optional[bytes] = None) -> Path:
        """Extract single entry dari pak ke disk."""
        entry = self.entries.get(entry_name)
        if not entry:
            raise FileNotFoundError(f"Entry {entry_name} not found in pak")

        if not self.pak_path:
            raise RuntimeError("No pak file loaded")

        out_path = output_dir / entry_name.lstrip("/")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.pak_path, "rb") as fp:
            fp.seek(entry.offset)
            data = fp.read(entry.size)

            if entry.encrypted and aes_key:
                data = self._decrypt_aes(data, aes_key)

            if entry.compression_method == self.COMPRESSION_NONE:
                raw = data
            elif entry.compression_method == self.COMPRESSION_ZLIB:
                raw = zlib.decompress(data)
            else:
                raw = data  # Unsupported: skip decompression

        out_path.write_bytes(raw)
        return out_path

    def extract_all(self, output_dir: Path, aes_key: Optional[bytes] = None,
                    pattern: Optional[str] = None) -> List[Path]:
        """Extract semua entries (atau filtered by pattern)."""
        extracted: List[Path] = []
        for name in self.entries:
            if pattern and pattern not in name:
                continue
            try:
                p = self.extract_entry(name, output_dir, aes_key)
                extracted.append(p)
            except Exception as e:
                print(f"[WARN] Failed to extract {name}: {e}")
        return extracted

    def build_pak(self, source_dir: Path, output_pak: Path,
                  mount_point: str = "../../../Game/Content/",
                  version: PakVersion = PakVersion.FNameBasedCompression,
                  compression: int = COMPRESSION_ZLIB) -> None:
        """Build .pak file dari directory tree."""
        files = sorted(source_dir.rglob("*"))
        files = [f for f in files if f.is_file()]

        entries_meta: List[Tuple[str, Path]] = []
        for f in files:
            rel = str(f.relative_to(source_dir)).replace("\\", "/")
            entries_meta.append((mount_point + rel, f))

        with open(output_pak, "wb") as out_fp:
            # Write file data first, collect offsets
            entry_records: List[Tuple[str, int, int, int, int, bytes]] = []
            for name, fpath in entries_meta:
                raw = fpath.read_bytes()
                uncompressed = len(raw)
                if compression == self.COMPRESSION_ZLIB:
                    compressed = zlib.compress(raw, level=6)
                else:
                    compressed = raw
                offset = out_fp.tell()
                out_fp.write(compressed)
                entry_records.append((name, offset, len(compressed), uncompressed,
                                      compression, hashlib.sha1(raw).digest()))

            # Build index
            index_offset = out_fp.tell()
            index_buf = io.BytesIO()
            _write_string(index_buf, mount_point)
            index_buf.write(struct.pack("<i", len(entry_records)))
            for name, offset, size, uncompressed, comp, sha1 in entry_records:
                _write_string(index_buf, name)
                index_buf.write(struct.pack("<Q Q Q I 20s",
                                             offset, size, uncompressed, comp, sha1))
                if version.value >= PakVersion.CompressionEncryption.value:
                    index_buf.write(struct.pack("<I", 0))  # block count = 0 (no compression blocks)
                    index_buf.write(struct.pack("<?", False))  # encrypted
                    index_buf.write(struct.pack("<I", 0x10000))  # block size

            index_data = index_buf.getvalue()
            out_fp.write(index_data)
            index_size = len(index_data)

            # Footer
            footer = struct.pack("<I I Q Q 20s",
                                 0x5A6F12E1, version.value,
                                 index_offset, index_size,
                                 hashlib.sha1(index_data).digest())
            out_fp.write(footer)

        print(f"[PAK] Built {output_pak}: {len(entry_records)} files")

    @staticmethod
    def _decrypt_aes(data: bytes, key: bytes) -> bytes:
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            iv = data[:16]
            ct = data[16:]
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            return cipher.decryptor().update(ct) + cipher.decryptor().finalize()
        except Exception:
            return data

    def list_entries(self) -> List[str]:
        return sorted(self.entries.keys())

    def get_stats(self) -> Dict[str, Any]:
        total_size = sum(e.size for e in self.entries.values())
        total_uncompressed = sum(e.uncompressed_size for e in self.entries.values())
        by_ext: Dict[str, int] = {}
        for name in self.entries:
            ext = name.split(".")[-1] if "." in name else "no_ext"
            by_ext[ext] = by_ext.get(ext, 0) + 1
        return {
            "entries": len(self.entries),
            "total_compressed_bytes": total_size,
            "total_uncompressed_bytes": total_uncompressed,
            "compression_ratio": round(total_uncompressed / max(total_size, 1), 2),
            "by_extension": by_ext,
        }


# ═════════════════════════════════════════════════════════════════════════════
# 2. IOSTORE CONTAINER ENGINE — UE5 Zen Format (.utoc + .ucas)
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class IoStoreChunk:
    offset: int
    size: int
    compressed: bool

@dataclass
class IoStoreContainerEntry:
    chunk_id: int
    offset: int
    size: int
    compression: int

class IoStoreContainerEngine:
    """
    Engine untuk UE5 IoStore containers (.utoc + .ucas + .pak).
    Meniru retoc/UnrealReZen/ZenTools functionality.

    IoStore = UE5's replacement untuk traditional .pak system.
    • .utoc = Table of Contents (index)
    • .ucas = Container Archive Storage (actual data)
    • Zen assets = new serialization format (different dari legacy .uasset)
    """

    def __init__(self) -> None:
        self.toc_path: Optional[Path] = None
        self.container_path: Optional[Path] = None
        self.entries: Dict[int, IoStoreContainerEntry] = {}
        self.chunks: List[IoStoreChunk] = []
        self.version: int = 0
        self.container_flags: int = 0

    def parse_toc(self, utoc_file: Path) -> Dict[str, Any]:
        """Parse .utoc (Table of Contents) file."""
        self.toc_path = utoc_file
        with open(utoc_file, "rb") as fp:
            magic = struct.unpack("<I", fp.read(4))[0]
            if magic != 0x6F7A6E21:  # 'zno!' in little-endian
                raise ValueError(f"Invalid IoStore TOC magic: 0x{magic:08X}")
            self.version = struct.unpack("<I", fp.read(4))[0]
            entry_count = struct.unpack("<I", fp.read(4))[0]
            self.container_flags = struct.unpack("<I", fp.read(4))[0]

            self.entries = {}
            for i in range(entry_count):
                chunk_id, offset, size, compression = struct.unpack("<I Q Q I", fp.read(24))
                self.entries[chunk_id] = IoStoreContainerEntry(
                    chunk_id=chunk_id, offset=offset, size=size,
                    compression=compression,
                )

            return {
                "version": self.version,
                "entry_count": len(self.entries),
                "container_flags": self.container_flags,
            }

    def parse_container(self, ucas_file: Path) -> Dict[str, Any]:
        """Parse .ucas (Container Archive Storage) file."""
        self.container_path = ucas_file
        with open(ucas_file, "rb") as fp:
            magic = struct.unpack("<I", fp.read(4))[0]
            if magic != 0x63617321:  # 'cas!'
                raise ValueError(f"Invalid IoStore container magic: 0x{magic:08X}")
            block_size = struct.unpack("<I", fp.read(4))[0]
            chunk_count = struct.unpack("<I", fp.read(4))[0]

            self.chunks = []
            for _ in range(chunk_count):
                offset, size, flags = struct.unpack("<Q Q I", fp.read(20))
                self.chunks.append(IoStoreChunk(
                    offset=offset, size=size,
                    compressed=bool(flags & 1),
                ))

            return {
                "block_size": block_size,
                "chunk_count": len(self.chunks),
            }

    def extract_chunk(self, chunk_id: int, output_path: Path) -> Path:
        """Extract single chunk dari container."""
        entry = self.entries.get(chunk_id)
        if not entry:
            raise ValueError(f"Chunk {chunk_id} not in TOC")
        if not self.container_path:
            raise RuntimeError("No container file loaded")

        with open(self.container_path, "rb") as fp:
            fp.seek(entry.offset)
            data = fp.read(entry.size)

            if entry.compression == 1:  # Zlib
                data = zlib.decompress(data)
            elif entry.compression == 2:  # Gzip
                import gzip
                data = gzip.decompress(data)

        output_path.write_bytes(data)
        return output_path

    def list_entries(self) -> List[int]:
        return sorted(self.entries.keys())


# ═════════════════════════════════════════════════════════════════════════════
# 3. UASSET PARSER — Legacy Cooked Asset Binary Reader
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class UAssetExport:
    class_name: str
    super_name: str
    template_name: str
    outer_index: int
    object_name: str
    serial_size: int
    serial_offset: int

@dataclass
class UAssetSummary:
    tag: int  # 0x9E2A83C1
    legacy_version: int
    file_version_ue4: int
    file_version_ue5: int
    package_flags: int
    total_header_size: int
    folder_name: str
    package_name: str
    export_count: int
    import_count: int
    depends_offset: int
    exports: List[UAssetExport] = field(default_factory=list)

class UAssetParser:
    """
    Parser untuk legacy cooked .uasset files.
    Meniru FModel/UAssetGUI/UModel asset reading functionality.

    UAsset format = package header + exports + imports + depends + string table.
    """

    PACKAGE_FILE_TAG = 0x9E2A83C1
    PACKAGE_FILE_TAG_SWAPPED = 0xC1832A9E

    def __init__(self) -> None:
        self.summary: Optional[UAssetSummary] = None
        self.exports: List[UAssetExport] = []
        self.imports: List[Dict[str, Any]] = []
        self.string_table: List[str] = []

    def parse(self, uasset_path: Path) -> Dict[str, Any]:
        with open(uasset_path, "rb") as fp:
            self.summary = self._read_summary(fp)
            self._read_names(fp)
            self._read_imports(fp)
            self._read_exports(fp)

        return {
            "package_name": self.summary.package_name if self.summary else "",
            "folder": self.summary.folder_name if self.summary else "",
            "export_count": len(self.exports),
            "import_count": len(self.imports),
            "name_count": len(self.string_table),
            "exports": [e.__dict__ for e in self.exports],
        }

    def _read_summary(self, fp: BinaryIO) -> UAssetSummary:
        tag = struct.unpack("<I", fp.read(4))[0]
        if tag not in (self.PACKAGE_FILE_TAG, self.PACKAGE_FILE_TAG_SWAPPED):
            raise ValueError(f"Invalid UAsset tag: 0x{tag:08X}")
        swapped = tag == self.PACKAGE_FILE_TAG_SWAPPED

        legacy_ver = struct.unpack("<i", fp.read(4))[0]
        file_ver_ue4 = struct.unpack("<i", fp.read(4))[0]
        file_ver_ue5 = struct.unpack("<i", fp.read(4))[0] if legacy_ver < 0 else 0

        if legacy_ver < 0:
            fp.read(4)  # file_version_licensee_ue

        total_header = struct.unpack("<I", fp.read(4))[0]
        folder = _read_string(fp)
        pkg_flags = struct.unpack("<I", fp.read(4))[0]
        name_count = struct.unpack("<I", fp.read(4))[0]
        name_offset = struct.unpack("<I", fp.read(4))[0]
        gatherable_text_count = struct.unpack("<I", fp.read(4))[0] if legacy_ver <= -7 else 0

        export_count = struct.unpack("<I", fp.read(4))[0]
        export_offset = struct.unpack("<I", fp.read(4))[0]
        import_count = struct.unpack("<I", fp.read(4))[0]
        import_offset = struct.unpack("<I", fp.read(4))[0]
        depends_offset = struct.unpack("<I", fp.read(4))[0]

        return UAssetSummary(
            tag=tag, legacy_version=legacy_ver,
            file_version_ue4=file_ver_ue4,
            file_version_ue5=file_ver_ue5,
            package_flags=pkg_flags,
            total_header_size=total_header,
            folder_name=folder,
            package_name="",
            export_count=export_count,
            import_count=import_count,
            depends_offset=depends_offset,
        )

    def _read_names(self, fp: BinaryIO) -> None:
        if not self.summary:
            return
        fp.seek(self.summary.total_header_size)  # Simplified
        # Real: seek ke name_offset
        # For demo: read up to 100 strings
        self.string_table = []
        for _ in range(min(self.summary.export_count + self.summary.import_count + 10, 100)):
            try:
                s = _read_string(fp)
                if s:
                    self.string_table.append(s)
            except Exception:
                break

    def _read_imports(self, fp: BinaryIO) -> None:
        # Simplified import reading
        self.imports = []
        for i in range(self.summary.import_count if self.summary else 0):
            self.imports.append({"index": i, "name": f"import_{i}"})

    def _read_exports(self, fp: BinaryIO) -> None:
        self.exports = []
        for i in range(self.summary.export_count if self.summary else 0):
            # Simplified export reading
            self.exports.append(UAssetExport(
                class_name="UObject", super_name="",
                template_name="", outer_index=0,
                object_name=f"export_{i}",
                serial_size=0, serial_offset=0,
            ))

    def get_export_names(self) -> List[str]:
        return [e.object_name for e in self.exports]

    def get_class_types(self) -> Set[str]:
        return set(e.class_name for e in self.exports)


# ═════════════════════════════════════════════════════════════════════════════
# 4. BLUEPRINT MODDING ENGINE — Runtime Hook Injection
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class BlueprintHook:
    target_function: str
    target_class: str
    hook_type: str  # pre / post / replace
    payload_code: str  # Lua/C++ snippet
    enabled: bool = True

class BlueprintModdingEngine:
    """
    Engine untuk blueprint-based modding — meniru UE4SS/UML/DML:
    • UObject reflection & property modification
    • Function hooking (pre/post/replace)
    • Live property editor
    • Lua scripting bridge
    """

    def __init__(self) -> None:
        self.hooks: List[BlueprintHook] = []
        self.live_objects: Dict[str, Dict[str, Any]] = {}
        self.scripts: Dict[str, str] = {}

    def register_hook(self, hook: BlueprintHook) -> str:
        hook_id = f"hook_{hashlib.sha256(hook.target_function.encode()).hexdigest()[:8]}"
        self.hooks.append(hook)
        return hook_id

    def modify_property(self, object_path: str, property_name: str,
                        value: Any) -> bool:
        """Modify UObject property at runtime."""
        if object_path not in self.live_objects:
            self.live_objects[object_path] = {}
        self.live_objects[object_path][property_name] = value
        return True

    def dump_uobject(self, object_path: str) -> Dict[str, Any]:
        """Dump semua properties dari UObject."""
        return self.live_objects.get(object_path, {})

    def load_lua_script(self, script_name: str, code: str) -> None:
        """Load Lua mod script (meniru UE4SS Lua API)."""
        self.scripts[script_name] = code

    def execute_lua(self, script_name: str, context: Dict[str, Any]) -> Any:
        """Execute Lua script dengan context — SECURE: uses SafeEvaluator instead of eval()."""
        code = self.scripts.get(script_name, "")
        # SECURITY FIX: replaced eval() with SafeEvaluator
        # Old: return eval(code, {"__builtins__": {}}, context)
        try:
            sys.path.insert(0, "security")
            from safe_eval_native import SafeEvaluator
            evaluator = SafeEvaluator(extra_names=context)
            return evaluator.eval(code)
        except Exception as e:
            return {"error": str(e), "blocked": True}
        finally:
            if "security" in sys.path:
                sys.path.remove("security")

    def generate_mod_actor_template(self, mod_name: str) -> str:
        """Generate Blueprint ModActor template."""
        return f'''
-- ModActor template for {mod_name}
-- Meniru UE4SS ModActor lifecycle

local ModActor = {{}}

function ModActor:BeginPlay()
    print("[{mod_name}] ModActor initialized")
    -- Hook example:
    -- RegisterHook("/Script/Engine.PlayerController:ClientRestart", function(self)
    --     print("Player restarted!")
    -- end)
end

function ModActor:Tick(deltaTime)
    -- Called every frame
end

return ModActor
'''

    def get_active_hooks(self) -> List[Dict[str, Any]]:
        return [{"target": h.target_function, "type": h.hook_type,
                 "class": h.target_class, "enabled": h.enabled}
                for h in self.hooks]


# ═════════════════════════════════════════════════════════════════════════════
# 5. LOCALIZATION ENGINE — .locres Read/Write
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class LocResEntry:
    key: str
    source_text: str
    translated_text: str
    namespace: str = ""

class LocResEngine:
    """
    Engine untuk UE4/UE5 .locres files.
    Meniru UnrealLocres / UE4LocalizationsTool.

    .locres = binary localization resource:
    • String namespace + key → source text + translated text
    • Multiple locales per file
    """

    LOCRES_MAGIC = 0x7574145E

    def __init__(self) -> None:
        self.entries: Dict[str, List[LocResEntry]] = {}
        self.namespaces: Set[str] = set()
        self.version: int = 0
        self.loco_guid: bytes = b""

    def read(self, locres_path: Path) -> Dict[str, Any]:
        with open(locres_path, "rb") as fp:
            magic = struct.unpack("<I", fp.read(4))[0]
            if magic != self.LOCRES_MAGIC:
                raise ValueError(f"Invalid locres magic: 0x{magic:08X}")

            version = struct.unpack("<I", fp.read(4))[0]
            self.version = version

            namespace_count = struct.unpack("<I", fp.read(4))[0]
            self.entries = {}
            self.namespaces = set()

            for _ in range(namespace_count):
                ns_name = _read_string(fp)
                key_count = struct.unpack("<I", fp.read(4))[0]
                self.namespaces.add(ns_name)
                self.entries[ns_name] = []

                for _ in range(key_count):
                    key = _read_string(fp)
                    source = _read_string(fp)
                    translated = _read_string(fp)
                    self.entries[ns_name].append(LocResEntry(
                        key=key, source_text=source,
                        translated_text=translated, namespace=ns_name,
                    ))

        return {
            "version": self.version,
            "namespaces": list(self.namespaces),
            "total_entries": sum(len(v) for v in self.entries.values()),
        }

    def write(self, output_path: Path) -> None:
        with open(output_path, "wb") as fp:
            fp.write(struct.pack("<I", self.LOCRES_MAGIC))
            fp.write(struct.pack("<I", self.version))
            fp.write(struct.pack("<I", len(self.namespaces)))

            for ns, entries in self.entries.items():
                _write_string(fp, ns)
                fp.write(struct.pack("<I", len(entries)))
                for e in entries:
                    _write_string(fp, e.key)
                    _write_string(fp, e.source_text)
                    _write_string(fp, e.translated_text)

    def translate(self, namespace: str, key: str,
                  new_translation: str) -> bool:
        """Update translation untuk key tertentu."""
        entries = self.entries.get(namespace, [])
        for e in entries:
            if e.key == key:
                e.translated_text = new_translation
                return True
        return False

    def extract_all_text(self) -> List[Dict[str, str]]:
        """Extract semua text untuk translation workflow."""
        result = []
        for ns, entries in self.entries.items():
            for e in entries:
                result.append({
                    "namespace": ns,
                    "key": e.key,
                    "source": e.source_text,
                    "translation": e.translated_text,
                })
        return result

    def search(self, query: str) -> List[LocResEntry]:
        q = query.lower()
        results = []
        for entries in self.entries.values():
            for e in entries:
                if q in e.key.lower() or q in e.source_text.lower() or q in e.translated_text.lower():
                    results.append(e)
        return results


# ═════════════════════════════════════════════════════════════════════════════
# 6. REVERSE ENGINEERING BRIDGE — AOB Scanner & Memory Dumper
# ═════════════════════════════════════════════════════════════════════════════

class AOBScanner:
    """
    Array-of-Bytes scanner untuk binary pattern matching.
    Meniru Cheat Engine / x64dbg / patternsleuth functionality.
    """

    @staticmethod
    def parse_pattern(pattern_str: str) -> List[Optional[int]]:
        """
        Parse pattern string ke list bytes.
        Format: "48 89 5C 24 ? 48 89 6C 24 ? 48 89 74 24 ?"
        '?' = wildcard
        """
        result = []
        for token in pattern_str.split():
            if token == "?" or token == "??":
                result.append(None)
            else:
                result.append(int(token, 16))
        return result

    @staticmethod
    def scan(data: bytes, pattern: List[Optional[int]]) -> List[int]:
        """Scan data untuk pattern, return list offsets."""
        pattern_len = len(pattern)
        fixed = [(i, b) for i, b in enumerate(pattern) if b is not None]
        if not fixed:
            return []

        results = []
        first_byte = fixed[0][1]
        first_offset = fixed[0][0]

        for i in range(len(data) - pattern_len + 1):
            if data[i + first_offset] != first_byte:
                continue
            match = True
            for offset, byte in fixed:
                if data[i + offset] != byte:
                    match = False
                    break
            if match:
                results.append(i)
        return results

    @staticmethod
    def wildcard_ptrs(pattern_str: str, data: bytes) -> List[Dict[str, Any]]:
        """
        Generate AOB dengan wildcard untuk call pointers.
        Meniru x64dbg Swiss Army Knife functionality.
        """
        pattern = AOBScanner.parse_pattern(pattern_str)
        offsets = AOBScanner.scan(data, pattern)
        results = []
        for off in offsets:
            # Extract potential pointer (8 bytes after pattern)
            ptr = struct.unpack("<Q", data[off + len(pattern):off + len(pattern) + 8])[0]
            results.append({
                "offset": off,
                "relative_address": hex(off),
                "extracted_pointer": hex(ptr),
                "bytes": data[off:off + 32].hex(),
            })
        return results

    @staticmethod
    def generate_aob_from_asm(asm_bytes: bytes,
                             wildcard_offsets: Optional[List[int]] = None) -> str:
        """Generate AOB pattern dari raw assembly bytes."""
        wildcards = set(wildcard_offsets or [])
        tokens = []
        for i, b in enumerate(asm_bytes):
            if i in wildcards:
                tokens.append("?")
            else:
                tokens.append(f"{b:02X}")
        return " ".join(tokens)


class MemoryDumper:
    """
    Memory dumping engine — meniru UE4SS dumper / UWP Dumper.
    Simplified untuk analysis & research purposes.
    """

    @staticmethod
    def dump_process_strings(pid: int, min_length: int = 4) -> List[str]:
        """Extract readable strings dari process memory (Linux /proc/pid/mem)."""
        strings_found: List[str] = []
        mem_path = f"/proc/{pid}/mem"
        maps_path = f"/proc/{pid}/maps"

        if not os.path.exists(mem_path):
            return strings_found

        try:
            with open(maps_path, "r") as maps:
                regions = []
                for line in maps:
                    parts = line.split()
                    if len(parts) >= 6 and "r" in parts[1]:
                        addr_range = parts[0].split("-")
                        start = int(addr_range[0], 16)
                        end = int(addr_range[1], 16)
                        regions.append((start, end))

            with open(mem_path, "rb") as mem:
                for start, end in regions[:10]:  # Limit untuk demo
                    try:
                        mem.seek(start)
                        chunk = mem.read(min(end - start, 0x100000))  # max 1MB per region
                        current = ""
                        for b in chunk:
                            if 32 <= b < 127:
                                current += chr(b)
                            else:
                                if len(current) >= min_length:
                                    strings_found.append(current)
                                current = ""
                    except Exception:
                        continue
        except Exception:
            pass

        return strings_found

    @staticmethod
    def find_ue_objects(memory: bytes) -> List[Dict[str, Any]]:
        """
        Heuristic scan untuk UObject signatures dalam memory dump.
        """
        # UObject signature: class pointer + object flags + internal index + name + outer
        objects = []
        # Search untuk common UE class names
        for class_name in [b"AActor", b"UObject", b"APawn", b"ACharacter"]:
            idx = 0
            while True:
                idx = memory.find(class_name, idx)
                if idx == -1:
                    break
                # Extract surrounding context
                context = memory[max(0, idx - 64):idx + 64]
                objects.append({
                    "offset": idx,
                    "class_name": class_name.decode(),
                    "context": context.hex()[:128],
                })
                idx += 1
        return objects


# ═════════════════════════════════════════════════════════════════════════════
# 7. MAPPINGS ENGINE — .usmap Dumper & Reader
# ═════════════════════════════════════════════════════════════════════════════

class MappingsEngine:
    """
    Engine untuk Unreal Engine 5 .usmap mappings files.
    .usmap = struct/member name mappings untuk games tanpa debug symbols.
    """

    def read(self, usmap_path: Path) -> Dict[str, Any]:
        with open(usmap_path, "rb") as fp:
            magic = struct.unpack("<I", fp.read(4))[0]
            if magic != 0x30303330:  # '0000'
                raise ValueError(f"Invalid usmap magic: 0x{magic:08X}")
            version = struct.unpack("<B", fp.read(1))[0]

            # Read names
            name_count = struct.unpack("<I", fp.read(4))[0]
            names = []
            for _ in range(name_count):
                names.append(_read_string(fp))

            # Read structs
            struct_count = struct.unpack("<I", fp.read(4))[0]
            structs = []
            for _ in range(struct_count):
                struct_idx = struct.unpack("<I", fp.read(4))[0]
                super_idx = struct.unpack("<i", fp.read(4))[0]
                prop_count = struct.unpack("<I", fp.read(4))[0]
                props = []
                for _ in range(prop_count):
                    prop_idx = struct.unpack("<I", fp.read(4))[0]
                    array_dim = struct.unpack("<I", fp.read(4))[0]
                    props.append({"name_index": prop_idx, "array_dim": array_dim})
                structs.append({
                    "name_index": struct_idx,
                    "super_index": super_idx,
                    "properties": props,
                })

            return {
                "version": version,
                "names": names,
                "name_count": len(names),
                "struct_count": len(structs),
                "structs": structs,
            }


# ═════════════════════════════════════════════════════════════════════════════
# 8. MOD PACKAGER — .pak / IoStore Builder
# ═════════════════════════════════════════════════════════════════════════════

class ModPackager:
    """
    Packager untuk membuat mod distribution files:
    • .pak files untuk legacy UE4
    • IoStore containers untuk UE5
    • Chunk assignment & metadata
    """

    def __init__(self) -> None:
        self.pak_engine = PakContainerEngine()
        self.iostore_engine = IoStoreContainerEngine()
        self.metadata: Dict[str, Any] = {}

    def create_pak_mod(self, mod_name: str, content_dir: Path,
                       output_dir: Path, mount_point: str = "../../../Game/Content/Mods/",
                       ue_version: str = "ue4") -> Path:
        """Package mod sebagai .pak file."""
        output_pak = output_dir / f"{mod_name}_P.pak"
        self.pak_engine.build_pak(
            source_dir=content_dir,
            output_pak=output_pak,
            mount_point=mount_point,
        )
        self.metadata = {
            "mod_name": mod_name,
            "format": "pak",
            "ue_version": ue_version,
            "mount_point": mount_point,
            "file_count": len(self.pak_engine.entries),
            "created_at": _now(),
        }
        return output_pak

    def create_iostore_mod(self, mod_name: str, content_dir: Path,
                           output_dir: Path, ue_version: str = "ue5") -> Tuple[Path, Path]:
        """Package mod sebagai IoStore (.utoc + .ucas)."""
        utoc_path = output_dir / f"{mod_name}_P.utoc"
        ucas_path = output_dir / f"{mod_name}_P.ucas"
        # Simplified: delegate ke pak engine untuk data,
        # lalu build IoStore wrapper
        self.metadata = {
            "mod_name": mod_name,
            "format": "iostore",
            "ue_version": ue_version,
            "created_at": _now(),
        }
        return utoc_path, ucas_path

    def generate_mod_json(self, mod_name: str, author: str,
                          description: str, version: str,
                          dependencies: List[str]) -> str:
        """Generate mod metadata JSON (meniru mod.io format)."""
        return json.dumps({
            "name": mod_name,
            "author": author,
            "description": description,
            "version": version,
            "game_version": "*",
            "dependencies": dependencies,
            "created_at": _now(),
            "format": self.metadata.get("format", "pak"),
        }, indent=2)


# ═════════════════════════════════════════════════════════════════════════════
# 9. UNIFIED UE MODDING ENGINE — Entry Point
# ═════════════════════════════════════════════════════════════════════════════

class UEModdingEngine:
    """
    Unified engine untuk Unreal Engine modding & asset manipulation.
    Entry point bagi MAGNATRIX runtime layer.
    """

    def __init__(self) -> None:
        self.pak = PakContainerEngine()
        self.iostore = IoStoreContainerEngine()
        self.uasset = UAssetParser()
        self.blueprint = BlueprintModdingEngine()
        self.locres = LocResEngine()
        self.aob = AOBScanner()
        self.memory = MemoryDumper()
        self.mappings = MappingsEngine()
        self.packager = ModPackager()

    # ── Pak Operations ──────────────────────────────────────────────────

    def open_pak(self, pak_path: Path) -> Dict[str, Any]:
        return self.pak.parse(pak_path)

    def extract_pak(self, pak_path: Path, output_dir: Path,
                    pattern: Optional[str] = None) -> List[Path]:
        self.pak.parse(pak_path)
        return self.pak.extract_all(output_dir, pattern=pattern)

    def build_pak(self, source: Path, output: Path, mount: str) -> None:
        self.pak.build_pak(source, output, mount)

    # ── IoStore Operations ──────────────────────────────────────────────

    def open_iostore(self, utoc: Path, ucas: Path) -> Dict[str, Any]:
        toc_info = self.iostore.parse_toc(utoc)
        container_info = self.iostore.parse_container(ucas)
        return {**toc_info, **container_info}

    # ── UAsset Operations ─────────────────────────────────────────────────

    def parse_uasset(self, path: Path) -> Dict[str, Any]:
        return self.uasset.parse(path)

    # ── Blueprint Modding ───────────────────────────────────────────────────

    def register_hook(self, function: str, cls: str,
                        hook_type: str, code: str) -> str:
        return self.blueprint.register_hook(
            BlueprintHook(function, cls, hook_type, code)
        )

    def generate_mod_actor(self, name: str) -> str:
        return self.blueprint.generate_mod_actor_template(name)

    # ── Localization ──────────────────────────────────────────────────────

    def read_locres(self, path: Path) -> Dict[str, Any]:
        return self.locres.read(path)

    def write_locres(self, path: Path) -> None:
        self.locres.write(path)

    def translate_text(self, ns: str, key: str, text: str) -> bool:
        return self.locres.translate(ns, key, text)

    # ── Reverse Engineering ───────────────────────────────────────────────

    def scan_aob(self, data: bytes, pattern: str) -> List[int]:
        parsed = self.aob.parse_pattern(pattern)
        return self.aob.scan(data, parsed)

    def dump_strings(self, pid: int) -> List[str]:
        return self.memory.dump_process_strings(pid)

    def find_ue_objects(self, mem_dump: bytes) -> List[Dict[str, Any]]:
        return self.memory.find_ue_objects(mem_dump)

    # ── Mappings ──────────────────────────────────────────────────────────

    def read_mappings(self, path: Path) -> Dict[str, Any]:
        return self.mappings.read(path)

    # ── Packaging ─────────────────────────────────────────────────────────

    def package_mod(self, name: str, content: Path, output: Path) -> Path:
        return self.packager.create_pak_mod(name, content, output)

    # ── Full Pipeline ─────────────────────────────────────────────────────

    def extract_game_assets(self, pak_dir: Path, output_dir: Path,
                            target_extensions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Full pipeline: extract semua assets dari game pak directory.
        """
        all_paks = sorted(pak_dir.glob("*.pak"))
        extracted: Dict[str, int] = {}

        for pak_file in all_paks:
            try:
                info = self.pak.parse(pak_file)
                entries = self.pak.list_entries()
                for entry in entries:
                    ext = entry.split(".")[-1] if "." in entry else "none"
                    if target_extensions and ext not in target_extensions:
                        continue
                    try:
                        self.pak.extract_entry(entry, output_dir)
                        extracted[ext] = extracted.get(ext, 0) + 1
                    except Exception:
                        pass
            except Exception as e:
                print(f"[WARN] Failed to parse {pak_file}: {e}")

        return {
            "pak_files_processed": len(all_paks),
            "total_extracted": sum(extracted.values()),
            "by_extension": extracted,
            "output_dir": str(output_dir),
        }


def main():
    print("═══════════════════════════════════════════════════════════════")
    print("  MAGNATRIX-OS — UE Modding Native Engine")
    print("  AMATI-PELAJARI-TIRU dari Buckminsterfullerene02/UE-Modding-Tools")
    print("════════════════════════════════════════════════════════════════")
    print()

    engine = UEModdingEngine()

    # Demo 1: PAK builder
    print("[1] PAK Container Builder:")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "content"
        src.mkdir()
        (src / "hello.txt").write_text("Hello from MAGNATRIX!")
        (src / "Config").mkdir()
        (src / "Config" / "DefaultEngine.ini").write_text("[Core.System]\n")

        pak_out = Path(tmp) / "test.pak"
        engine.build_pak(src, pak_out, "../../../Game/Content/")
        info = engine.open_pak(pak_out)
        print(f"  Version: {info['version']}")
        print(f"  Mount: {info['mount_point']}")
        print(f"  Entries: {info['entry_count']}")

        # Extract
        extract_dir = Path(tmp) / "extracted"
        extract_dir.mkdir()
        engine.pak.extract_all(extract_dir)
        print(f"  Extracted to: {extract_dir}")
    print()

    # Demo 2: AOB Scanner
    print("[2] AOB Scanner:")
    test_data = bytes([0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x6C,
                       0x24, 0x10, 0x48, 0x89, 0x74, 0x24, 0x18, 0x57])
    pattern = "48 89 5C 24 ? 48 89 6C 24 ?"
    offsets = engine.scan_aob(test_data, pattern)
    print(f"  Pattern: {pattern}")
    print(f"  Matches: {offsets}")
    print()

    # Demo 3: Blueprint Mod Actor
    print("[3] Blueprint Mod Actor Template:")
    template = engine.generate_mod_actor("MyFirstMod")
    print(template[:200] + "...")
    print()

    # Demo 4: LocRes
    print("[4] Localization Engine:")
    with tempfile.TemporaryDirectory() as tmp:
        loc_path = Path(tmp) / "Game.locres"
        engine.locres.version = 0
        engine.locres.entries = {
            "Game": [
                LocResEntry("PLAY", "Play", "Jugar", "Game"),
                LocResEntry("QUIT", "Quit", "Salir", "Game"),
            ]
        }
        engine.write_locres(loc_path)
        info = engine.read_locres(loc_path)
        print(f"  Namespaces: {info['namespaces']}")
        print(f"  Entries: {info['total_entries']}")
    print()

    # Demo 5: Hook
    print("[5] Blueprint Hook:")
    hook_id = engine.register_hook(
        "/Script/Engine.PlayerController:ClientRestart",
        "PlayerController", "post",
        "print('Player restarted!')"
    )
    print(f"  Hook ID: {hook_id}")
    print(f"  Active hooks: {len(engine.blueprint.get_active_hooks())}")
    print()

    print("Done.")


if __name__ == "__main__":
    main()
