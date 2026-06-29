
"""
ioctl_dispatch_extractor_native.py
MAGNATRIX-OS — IOCTL Dispatch Extractor

Extract IOCTL dispatch routines from Windows kernel drivers.
Identifies reachable IOCTL codes and their handlers.
Inspired by DriverScope.

Pure Python standard library.
"""

import struct
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class IOCTLHandler:
    ioctl_code: str
    handler_offset: int
    handler_name: str
    device_name: str
    access_type: str = "ANY"
    description: str = ""


class IOCTLDispatchExtractor:
    """Extract IOCTL dispatch surfaces from Windows drivers."""

    # Common IOCTL access patterns
    IOCTL_METHODS = {
        "METHOD_BUFFERED": 0,
        "METHOD_IN_DIRECT": 1,
        "METHOD_OUT_DIRECT": 2,
        "METHOD_NEITHER": 3,
    }

    def __init__(self):
        self.handlers: List[IOCTLHandler] = []
        self.extracted_ioctl_codes: Set[str] = set()

    def extract_from_binary(self, filepath: str) -> List[IOCTLHandler]:
        """Extract IOCTL dispatch from driver binary."""
        handlers = []
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            # Look for IOCTL device type signatures (common Windows device types)
            device_types = {
                0x00000022: "FILE_DEVICE_UNKNOWN",
                0x00000001: "FILE_DEVICE_BEEP",
                0x00000002: "FILE_DEVICE_CD_ROM",
                0x00000003: "FILE_DEVICE_CD_ROM_FILE_SYSTEM",
                0x00000004: "FILE_DEVICE_CONTROLLER",
                0x00000005: "FILE_DEVICE_DATALINK",
                0x00000006: "FILE_DEVICE_DFS",
                0x00000007: "FILE_DEVICE_DISK",
                0x00000008: "FILE_DEVICE_DISK_FILE_SYSTEM",
                0x00000009: "FILE_DEVICE_FILE_SYSTEM",
                0x0000000a: "FILE_DEVICE_INPORT_PORT",
                0x0000000b: "FILE_DEVICE_KEYBOARD",
                0x0000000c: "FILE_DEVICE_MAILSLOT",
                0x0000000d: "FILE_DEVICE_MIDI_IN",
                0x0000000e: "FILE_DEVICE_MIDI_OUT",
                0x0000000f: "FILE_DEVICE_MOUSE",
                0x00000010: "FILE_DEVICE_MULTI_UNC_PROVIDER",
                0x00000011: "FILE_DEVICE_NAMED_PIPE",
                0x00000012: "FILE_DEVICE_NETWORK",
                0x00000013: "FILE_DEVICE_NETWORK_BROWSER",
                0x00000014: "FILE_DEVICE_NETWORK_FILE_SYSTEM",
                0x00000015: "FILE_DEVICE_NULL",
                0x00000016: "FILE_DEVICE_PARALLEL_PORT",
                0x00000017: "FILE_DEVICE_PHYSICAL_NETCARD",
                0x00000018: "FILE_DEVICE_PRINTER",
                0x00000019: "FILE_DEVICE_SCANNER",
                0x0000001a: "FILE_DEVICE_SERIAL_MOUSE_PORT",
                0x0000001b: "FILE_DEVICE_SERIAL_PORT",
                0x0000001c: "FILE_DEVICE_SCREEN",
                0x0000001d: "FILE_DEVICE_SOUND",
                0x0000001e: "FILE_DEVICE_STREAMS",
                0x0000001f: "FILE_DEVICE_TAPE",
                0x00000020: "FILE_DEVICE_TAPE_FILE_SYSTEM",
                0x00000021: "FILE_DEVICE_TRANSPORT",
                0x00000023: "FILE_DEVICE_VIDEO",
                0x00000024: "FILE_DEVICE_VIRTUAL_DISK",
                0x00000025: "FILE_DEVICE_WAVE_IN",
                0x00000026: "FILE_DEVICE_WAVE_OUT",
                0x00000027: "FILE_DEVICE_8042_PORT",
                0x00000028: "FILE_DEVICE_NETWORK_REDIRECTOR",
                0x00000029: "FILE_DEVICE_BATTERY",
                0x0000002a: "FILE_DEVICE_BUS_EXTENDER",
                0x0000002b: "FILE_DEVICE_MODEM",
                0x0000002c: "FILE_DEVICE_VDM",
                0x0000002d: "FILE_DEVICE_MASS_STORAGE",
                0x0000002e: "FILE_DEVICE_SMB",
                0x0000002f: "FILE_DEVICE_KS",
                0x00000030: "FILE_DEVICE_CHANGER",
                0x00000031: "FILE_DEVICE_SMARTCARD",
                0x00000032: "FILE_DEVICE_ACPI",
                0x00000033: "FILE_DEVICE_DVD",
                0x00000034: "FILE_DEVICE_FULLSCREEN_VIDEO",
                0x00000035: "FILE_DEVICE_DFS_FILE_SYSTEM",
                0x00000036: "FILE_DEVICE_DFS_VOLUME",
                0x00000037: "FILE_DEVICE_SERENUM",
                0x00000038: "FILE_DEVICE_TERMSRV",
                0x00000039: "FILE_DEVICE_KSEC",
                0x0000003a: "FILE_DEVICE_FIPS",
                0x0000003b: "FILE_DEVICE_INFINIBAND",
                0x0000003c: "FILE_DEVICE_VMBUS",
                0x0000003d: "FILE_DEVICE_CRYPT_PROVIDER",
                0x0000003e: "FILE_DEVICE_WPD",
                0x0000003f: "FILE_DEVICE_BLUETOOTH",
                0x00000040: "FILE_DEVICE_MT_COMPOSITE",
                0x00000041: "FILE_DEVICE_MT_TRANSPORT",
                0x00000042: "FILE_DEVICE_BIOMETRIC",
                0x00000043: "FILE_DEVICE_PMI",
                0x00000044: "FILE_DEVICE_EHSTOR",
                0x00000045: "FILE_DEVICE_DEVAPI",
                0x00000046: "FILE_DEVICE_GPIO",
                0x00000047: "FILE_DEVICE_USBEX",
                0x00000048: "FILE_DEVICE_CONSOLE",
                0x00000049: "FILE_DEVICE_NFP",
                0x0000004a: "FILE_DEVICE_SYSENV",
                0x0000004b: "FILE_DEVICE_VIRTUAL_BLOCK",
                0x0000004c: "FILE_DEVICE_POINT_OF_SERVICE",
                0x0000004d: "FILE_DEVICE_STORAGE_REPLICATION",
                0x0000004e: "FILE_DEVICE_TRUST_ENV",
                0x0000004f: "FILE_DEVICE_UCM",
                0x00000050: "FILE_DEVICE_UCMTCPCI",
                0x00000051: "FILE_DEVICE_PRM",
                0x00000052: "FILE_DEVICE_EVENT_COLLECTOR",
                0x00000053: "FILE_DEVICE_USB",
                0x00000054: "FILE_DEVICE_SDFXRAW",
                0x00000055: "FILE_DEVICE_UCMUCSI",
                0x00000056: "FILE_DEVICE_PERSISTENT_MEMORY",
                0x00000057: "FILE_DEVICE_GENERIC_USB_BUS",
                0x00000058: "FILE_DEVICE_CONSOLE",
            }
            # Search for potential IOCTL codes in binary
            for i in range(0, len(data) - 4, 4):
                val = struct.unpack("<I", data[i:i+4])[0]
                # IOCTL code format: device_type (16 bits) | access (2 bits) | function (12 bits) | method (2 bits)
                device_type = (val >> 16) & 0xFFFF
                if device_type in device_types:
                    function = (val >> 2) & 0xFFF
                    access = (val >> 14) & 0x3
                    method = val & 0x3
                    ioctl_hex = f"0x{val:08X}"
                    if ioctl_hex not in self.extracted_ioctl_codes:
                        self.extracted_ioctl_codes.add(ioctl_hex)
                        handlers.append(IOCTLHandler(
                            ioctl_code=ioctl_hex,
                            handler_offset=i,
                            handler_name=f"IOCTL_{device_types[device_type]}_{function:04X}",
                            device_name=device_types[device_type],
                            access_type=self._access_type(access),
                            description=f"Function: {function}, Method: {self._method_name(method)}",
                        ))
            # Also try string-based extraction
            text = data.decode("latin-1", errors="ignore")
            for match in re.finditer(r"Device\\[A-Za-z0-9_]+", text):
                device_name = match.group(0)
                # Look for nearby IOCTL codes
                pos = match.start()
                for j in range(pos, min(pos + 200, len(data) - 4), 4):
                    val = struct.unpack("<I", data[j:j+4])[0]
                    if (val >> 16) & 0xFFFF in device_types:
                        ioctl_hex = f"0x{val:08X}"
                        if ioctl_hex not in self.extracted_ioctl_codes:
                            self.extracted_ioctl_codes.add(ioctl_hex)
                            handlers.append(IOCTLHandler(
                                ioctl_code=ioctl_hex,
                                handler_offset=j,
                                handler_name=f"IOCTL_{device_name.replace('Device\\\\', '')}",
                                device_name=device_name,
                            ))
        except Exception:
            pass
        self.handlers.extend(handlers)
        return handlers

    def _access_type(self, access: int) -> str:
        return {0: "FILE_ANY_ACCESS", 1: "FILE_READ_ACCESS", 2: "FILE_WRITE_ACCESS", 3: "FILE_READ_WRITE_ACCESS"}.get(access, "UNKNOWN")

    def _method_name(self, method: int) -> str:
        return {0: "METHOD_BUFFERED", 1: "METHOD_IN_DIRECT", 2: "METHOD_OUT_DIRECT", 3: "METHOD_NEITHER"}.get(method, "UNKNOWN")

    def get_attack_surface(self) -> Dict[str, Any]:
        """Analyze the extracted IOCTL surface for attack vectors."""
        methods = {}
        access_types = {}
        for h in self.handlers:
            method = h.description.split("Method: ")[-1] if "Method:" in h.description else "UNKNOWN"
            methods[method] = methods.get(method, 0) + 1
            access_types[h.access_type] = access_types.get(h.access_type, 0) + 1
        return {
            "total_ioctl_codes": len(self.handlers),
            "method_breakdown": methods,
            "access_breakdown": access_types,
            "high_risk_methods": methods.get("METHOD_NEITHER", 0),  # METHOD_NEITHER is highest risk
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_attack_surface()


__all__ = ["IOCTLDispatchExtractor", "IOCTLHandler"]
