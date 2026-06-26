#!/usr/bin/env python3
"""
gRPC Transport Layer for MAGNATRIX-OS
======================================
Lightweight gRPC-style protocol implementation using pure Python stdlib.
No external grpc library. HTTP/2 semantics simulated via HTTP/1.1 + SSE.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import json, math, struct, threading, time, urllib.request, urllib.parse, urllib.error
from dataclasses import dataclass, field, asdict
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union


class WireType(Enum):
    VARINT = 0
    I64 = 1
    LEN = 2
    I32 = 5


class ProtobufCodec:
    """Simple protobuf-like binary codec."""

    TYPE_MAP = {
        "int32": ("i", WireType.VARINT, int),
        "int64": ("q", WireType.VARINT, int),
        "uint32": ("I", WireType.VARINT, int),
        "uint64": ("Q", WireType.VARINT, int),
        "sint32": ("i", WireType.VARINT, int),
        "sint64": ("q", WireType.VARINT, int),
        "bool": ("?", WireType.VARINT, bool),
        "enum": ("i", WireType.VARINT, int),
        "fixed64": ("Q", WireType.I64, int),
        "sfixed64": ("q", WireType.I64, int),
        "double": ("d", WireType.I64, float),
        "string": ("s", WireType.LEN, str),
        "bytes": ("b", WireType.LEN, bytes),
        "fixed32": ("I", WireType.I32, int),
        "sfixed32": ("i", WireType.I32, int),
        "float": ("f", WireType.I32, float),
    }

    @staticmethod
    def _encode_varint(value: int) -> bytes:
        result = []
        while value > 0x7F:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value)
        return bytes(result)

    @staticmethod
    def _decode_varint(data: bytes, pos: int) -> Tuple[int, int]:
        result = 0
        shift = 0
        while True:
            if pos >= len(data):
                raise ValueError("Incomplete varint")
            byte = data[pos]
            result |= (byte & 0x7F) << shift
            pos += 1
            if not (byte & 0x80):
                break
            shift += 7
        return result, pos

    @staticmethod
    def _encode_tag(field_number: int, wire_type: WireType) -> bytes:
        return ProtobufCodec._encode_varint((field_number << 3) | wire_type.value)

    @staticmethod
    def _decode_tag(data: bytes, pos: int) -> Tuple[int, WireType, int]:
        tag, pos = ProtobufCodec._decode_varint(data, pos)
        field_number = tag >> 3
        wire_type = WireType(tag & 0x07)
        return field_number, wire_type, pos

    @staticmethod
    def encode(obj: Dict[str, Any], schema: Dict[str, Tuple[str, int]]) -> bytes:
        """Encode object using schema: field_name -> (type_name, field_number)."""
        result = bytearray()
        for field_name, (type_name, field_number) in schema.items():
            if field_name not in obj:
                continue
            value = obj[field_name]
            type_info = ProtobufCodec.TYPE_MAP.get(type_name)
            if type_info is None:
                if type_name.endswith("[]"):
                    elem_type = type_name[:-2]
                    elem_info = ProtobufCodec.TYPE_MAP.get(elem_type)
                    if elem_info is not None and isinstance(value, list):
                        for item in value:
                            result.extend(ProtobufCodec._encode_tag(field_number, WireType.LEN))
                            encoded_item = ProtobufCodec._encode_single(elem_type, item)
                            result.extend(ProtobufCodec._encode_varint(len(encoded_item)))
                            result.extend(encoded_item)
                    continue
                elif type_name.startswith("{"):
                    if isinstance(value, dict):
                        result.extend(ProtobufCodec._encode_tag(field_number, WireType.LEN))
                        encoded_nested = ProtobufCodec.encode(value, schema.get(field_name, {})[2] if len(schema.get(field_name, ())) > 2 else {})
                        result.extend(ProtobufCodec._encode_varint(len(encoded_nested)))
                        result.extend(encoded_nested)
                    continue
                continue
            _, wire_type, _ = type_info
            if isinstance(value, list):
                for item in value:
                    encoded = ProtobufCodec._encode_single(type_name, item)
                    result.extend(ProtobufCodec._encode_tag(field_number, wire_type))
                    if wire_type == WireType.LEN:
                        result.extend(ProtobufCodec._encode_varint(len(encoded)))
                    result.extend(encoded)
            else:
                encoded = ProtobufCodec._encode_single(type_name, value)
                result.extend(ProtobufCodec._encode_tag(field_number, wire_type))
                if wire_type == WireType.LEN:
                    result.extend(ProtobufCodec._encode_varint(len(encoded)))
                result.extend(encoded)
        return bytes(result)

    @staticmethod
    def _encode_single(type_name: str, value: Any) -> bytes:
        type_info = ProtobufCodec.TYPE_MAP.get(type_name)
        if type_info is None:
            return b""
        fmt, wire_type, py_type = type_info
        if wire_type == WireType.VARINT:
            if isinstance(value, bool):
                return ProtobufCodec._encode_varint(1 if value else 0)
            return ProtobufCodec._encode_varint(value)
        elif wire_type == WireType.I64:
            return struct.pack(f"!{fmt}", value)
        elif wire_type == WireType.I32:
            return struct.pack(f"!{fmt}", value)
        elif wire_type == WireType.LEN:
            if isinstance(value, str):
                return value.encode("utf-8")
            elif isinstance(value, bytes):
                return value
        return b""

    @staticmethod
    def decode(data: bytes, schema: Dict[str, Tuple[str, int]]) -> Dict[str, Any]:
        """Decode bytes to object using schema."""
        result: Dict[str, Any] = {}
        pos = 0
        while pos < len(data):
            field_number, wire_type, pos = ProtobufCodec._decode_tag(data, pos)
            for field_name, (type_name, fn) in schema.items():
                if fn == field_number:
                    if type_name.endswith("[]"):
                        elem_type = type_name[:-2]
                        if field_name not in result:
                            result[field_name] = []
                        if wire_type == WireType.LEN:
                            length, pos = ProtobufCodec._decode_varint(data, pos)
                            item_data = data[pos:pos + length]
                            pos += length
                            item = ProtobufCodec._decode_single(elem_type, item_data, WireType.LEN)
                            result[field_name].append(item)
                        else:
                            item = ProtobufCodec._decode_single(elem_type, data, wire_type, pos)
                            if isinstance(item, tuple):
                                pos = item[1]
                                result[field_name].append(item[0])
                    elif type_name.startswith("{"):
                        if field_name not in result:
                            result[field_name] = {}
                        length, pos = ProtobufCodec._decode_varint(data, pos)
                        nested_data = data[pos:pos + length]
                        pos += length
                        nested_schema = schema.get(field_name, ({},))[2] if len(schema.get(field_name, ())) > 2 else {}
                        result[field_name] = ProtobufCodec.decode(nested_data, nested_schema)
                    else:
                        if wire_type == WireType.LEN:
                            length, pos = ProtobufCodec._decode_varint(data, pos)
                            item_data = data[pos:pos + length]
                            pos += length
                            result[field_name] = ProtobufCodec._decode_single(type_name, item_data, WireType.LEN)
                        else:
                            decoded = ProtobufCodec._decode_single(type_name, data, wire_type, pos)
                            if isinstance(decoded, tuple):
                                result[field_name] = decoded[0]
                                pos = decoded[1]
                            else:
                                result[field_name] = decoded
                    break
            else:
                if wire_type == WireType.LEN:
                    length, pos = ProtobufCodec._decode_varint(data, pos)
                    pos += length
                elif wire_type == WireType.VARINT:
                    _, pos = ProtobufCodec._decode_varint(data, pos)
                elif wire_type == WireType.I64:
                    pos += 8
                elif wire_type == WireType.I32:
                    pos += 4
        return result

    @staticmethod
    def _decode_single(type_name: str, data: bytes, wire_type: WireType, pos: int = 0) -> Union[Any, Tuple[Any, int]]:
        type_info = ProtobufCodec.TYPE_MAP.get(type_name)
        if type_info is None:
            return b"", pos
        fmt, _, py_type = type_info
        if wire_type == WireType.VARINT:
            val, new_pos = ProtobufCodec._decode_varint(data, pos)
            if py_type == bool:
                return bool(val), new_pos
            return val, new_pos
        elif wire_type == WireType.I64:
            val = struct.unpack(f"!{fmt}", data[pos:pos+8])[0]
            return val, pos + 8
        elif wire_type == WireType.I32:
            val = struct.unpack(f"!{fmt}", data[pos:pos+4])[0]
            return val, pos + 4
        elif wire_type == WireType.LEN:
            if py_type == str:
                return data.decode("utf-8"), pos + len(data)
            elif py_type == bytes:
                return data, pos + len(data)
        return None, pos


@dataclass
class GRPCMessage:
    """gRPC message envelope."""
    header: Dict[str, Any] = field(default_factory=dict)
    body: bytes = b""

    def serialize(self) -> bytes:
        header_bytes = json.dumps(self.header, ensure_ascii=False).encode("utf-8")
        length = len(header_bytes) + len(self.body)
        return struct.pack("!I", length) + struct.pack("!I", len(header_bytes)) + header_bytes + self.body

    @staticmethod
    def deserialize(data: bytes) -> "GRPCMessage":
        if len(data) < 8:
            return GRPCMessage()
        length = struct.unpack("!I", data[:4])[0]
        header_len = struct.unpack("!I", data[4:8])[0]
        header = json.loads(data[8:8+header_len])
        body = data[8+header_len:]
        return GRPCMessage(header=header, body=body)


@dataclass
class GRPCMethod:
    """RPC method descriptor."""
    name: str
    request_type: str = "dict"
    response_type: str = "dict"
    streaming_mode: str = "unary-unary"
    handler: Optional[Callable] = None


@dataclass
class GRPCService:
    """gRPC service descriptor."""
    name: str
    methods: Dict[str, GRPCMethod] = field(default_factory=dict)

    def register(self, method: GRPCMethod) -> None:
        self.methods[method.name] = method

    def resolve(self, method_name: str) -> Optional[GRPCMethod]:
        return self.methods.get(method_name)

    def list_methods(self) -> List[str]:
        return list(self.methods.keys())


class HealthStatus(Enum):
    SERVING = "SERVING"
    NOT_SERVING = "NOT_SERVING"
    UNKNOWN = "UNKNOWN"


class HealthCheck:
    """gRPC health check protocol."""

    def __init__(self) -> None:
        self._status: Dict[str, HealthStatus] = {}
        self._watchers: Dict[str, List[Callable]] = {}

    def set_status(self, service: str, status: HealthStatus) -> None:
        self._status[service] = status
        for cb in self._watchers.get(service, []):
            try:
                cb(status)
            except Exception:
                pass

    def check(self, service: str) -> HealthStatus:
        return self._status.get(service, HealthStatus.UNKNOWN)

    def watch(self, service: str, callback: Callable) -> None:
        if service not in self._watchers:
            self._watchers[service] = []
        self._watchers[service].append(callback)

    def get_all(self) -> Dict[str, str]:
        return {k: v.value for k, v in self._status.items()}


class GRPCServer:
    """HTTP server simulating gRPC over HTTP/1.1 + SSE."""

    def __init__(self, host: str = "0.0.0.0", port: int = 50051) -> None:
        self.host = host
        self.port = port
        self.services: Dict[str, GRPCService] = {}
        self.health = HealthCheck()
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def register_service(self, service: GRPCService) -> None:
        self.services[service.name] = service
        self.health.set_status(service.name, HealthStatus.SERVING)

    def _handler_class(self) -> type:
        server = self

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_POST(self):
                path = self.path.strip("/")
                if not path.startswith("grpc/"):
                    self.send_error(404)
                    return
                parts = path.split("/")
                if len(parts) < 3:
                    self.send_error(400)
                    return
                service_name = parts[1]
                method_name = parts[2]
                service = server.services.get(service_name)
                if not service:
                    self.send_error(404)
                    return
                method = service.resolve(method_name)
                if not method or not method.handler:
                    self.send_error(404)
                    return
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length) if content_length > 0 else b"{}"
                try:
                    request = json.loads(body.decode("utf-8"))
                except Exception:
                    request = {}
                try:
                    response = method.handler(request)
                    if method.streaming_mode.endswith("-stream"):
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Cache-Control", "no-cache")
                        self.end_headers()
                        if isinstance(response, Iterator):
                            for chunk in response:
                                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                        else:
                            self.wfile.write(f"data: {json.dumps(response)}\n\n".encode())
                    else:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
                except Exception as e:
                    self.send_error(500, str(e))

            def do_GET(self):
                if self.path == "/health":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(server.health.get_all(), ensure_ascii=False).encode())
                else:
                    self.send_error(404)

        return _Handler

    def start(self) -> None:
        handler = self._handler_class()
        self._server = HTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()


class GRPCClient:
    """gRPC client with connection pooling and retry."""

    def __init__(self, base_url: str = "http://localhost:50051") -> None:
        self.base_url = base_url
        self._timeout = 10.0

    def call(self, service: str, method: str, request: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/grpc/{service}/{method}"
        data = json.dumps(request, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                return {"error": f"HTTP {e.code}", "message": e.read().decode()}
            except Exception as e:
                if attempt == 2:
                    return {"error": str(e)}
                time.sleep(0.1 * (2 ** attempt))
        return {"error": "max retries exceeded"}

    def stream_call(self, service: str, method: str, request: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        url = f"{self.base_url}/grpc/{service}/{method}"
        data = json.dumps(request, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "Accept": "text/event-stream"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                for line in resp:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        yield json.loads(line[6:])
        except Exception as e:
            yield {"error": str(e)}

    def health_check(self, service: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/health"
        try:
            with urllib.request.urlopen(url, timeout=5.0) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}


class LoadBalancer:
    """Round-robin + least-connections load balancer."""

    def __init__(self, strategy: str = "round_robin") -> None:
        self.strategy = strategy
        self.endpoints: List[str] = []
        self.connections: Dict[str, int] = {}
        self._index = 0
        self._lock = threading.Lock()

    def add_endpoint(self, endpoint: str) -> None:
        with self._lock:
            if endpoint not in self.endpoints:
                self.endpoints.append(endpoint)
                self.connections[endpoint] = 0

    def remove_endpoint(self, endpoint: str) -> None:
        with self._lock:
            if endpoint in self.endpoints:
                self.endpoints.remove(endpoint)
                self.connections.pop(endpoint, None)

    def next(self) -> Optional[str]:
        with self._lock:
            if not self.endpoints:
                return None
            if self.strategy == "round_robin":
                ep = self.endpoints[self._index % len(self.endpoints)]
                self._index += 1
                return ep
            elif self.strategy == "least_connections":
                return min(self.endpoints, key=lambda e: self.connections.get(e, 0))
            return self.endpoints[0]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "endpoints": self.endpoints.copy(),
                "connections": self.connections.copy(),
                "strategy": self.strategy,
            }


class GRPCTransport:
    """Top-level gRPC transport orchestrator."""

    def __init__(self, host: str = "0.0.0.0", port: int = 50051) -> None:
        self.server = GRPCServer(host, port)
        self.client = GRPCClient(f"http://{host}:{port}")
        self.load_balancer = LoadBalancer()
        self.codec = ProtobufCodec()
        self._running = False

    def register_service(self, service: GRPCService) -> None:
        self.server.register_service(service)

    def start_server(self) -> None:
        self.server.start()
        self._running = True

    def stop_server(self) -> None:
        self.server.stop()
        self._running = False

    def connect(self, endpoint: str) -> GRPCClient:
        self.load_balancer.add_endpoint(endpoint)
        return GRPCClient(endpoint)

    def get_health(self) -> Dict[str, Any]:
        return self.server.health.get_all()

    def is_running(self) -> bool:
        return self._running
