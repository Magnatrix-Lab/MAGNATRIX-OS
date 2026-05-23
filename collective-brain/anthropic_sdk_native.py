#!/usr/bin/env python3
"""
Anthropic SDK — Native Pure-Python Reimplementation
====================================================
Zero-dependency, stdlib-only client mirroring the C# SDK patterns:
builder, resource-oriented API, streaming, async parity, typed errors,
rate-limiting, retry logic, tool use, vision, system prompts, token counting.

Dependencies: Python 3.8+ (stdlib only)
"""

from __future__ import annotations

import asyncio
import base64
import dataclasses
import http.client
import json
import mimetypes
import os
import random
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Literal,
    Optional,
    TypeVar,
    Union,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_BASE_URL: str = "https://api.anthropic.com"
DEFAULT_API_VERSION: str = "2023-06-01"
DEFAULT_TIMEOUT: float = 60.0
DEFAULT_MAX_RETRIES: int = 2

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AnthropicError(Exception):
    """Base exception for all Anthropic SDK errors."""

    def __init__(self, message: str, *, body: Optional[Any] = None) -> None:
        super().__init__(message)
        self.message = message
        self.body = body

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, body={self.body!r})"


class APIConnectionError(AnthropicError):
    """Failed to connect to the Anthropic API."""


class APITimeoutError(APIConnectionError):
    """Request timed out."""


class APIStatusError(AnthropicError):
    """The Anthropic API returned a non-2xx status code."""

    def __init__(self, message: str, *, response: Any, status_code: int, body: Optional[Any] = None) -> None:
        super().__init__(message, body=body)
        self.response = response
        self.status_code = status_code

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status_code={self.status_code}, message={self.message!r}, body={self.body!r})"


class BadRequestError(APIStatusError):
    """400 — Bad request."""


class AuthenticationError(APIStatusError):
    """401 — Invalid API key."""


class PermissionError(APIStatusError):
    """403 — Permission denied."""


class NotFoundError(APIStatusError):
    """404 — Resource not found."""


class RateLimitError(APIStatusError):
    """429 — Rate limit exceeded."""


class ConflictError(APIStatusError):
    """409 — Conflict."""


class UnprocessableEntityError(APIStatusError):
    """422 — Unprocessable entity."""


class InternalServerError(APIStatusError):
    """500+ — Server error."""


def _status_error_class(status_code: int) -> type[APIStatusError]:
    mapping: Dict[int, type[APIStatusError]] = {
        400: BadRequestError, 401: AuthenticationError, 403: PermissionError,
        404: NotFoundError, 409: ConflictError, 422: UnprocessableEntityError, 429: RateLimitError,
    }
    if status_code >= 500:
        return InternalServerError
    return mapping.get(status_code, APIStatusError)


# ---------------------------------------------------------------------------
# Core Types
# ---------------------------------------------------------------------------

T = TypeVar("T")


class StopReason(str, Enum):
    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    TOOL_USE = "tool_use"


@dataclass
class ImageSource:
    type: Literal["base64"] = "base64"
    media_type: Literal["image/jpeg", "image/png", "image/gif", "image/webp"] = "image/jpeg"
    data: str = ""

    def __repr__(self) -> str:
        return f"ImageSource(media_type={self.media_type!r}, data=<{len(self.data)} chars>)"


@dataclass
class ToolUse:
    type: Literal["tool_use"] = "tool_use"
    id: str = ""
    name: str = ""
    input: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"ToolUse(id={self.id!r}, name={self.name!r}, input={self.input!r})"


@dataclass
class ToolResult:
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str = ""
    content: Union[str, List[Dict[str, Any]]] = ""
    is_error: bool = False

    def __repr__(self) -> str:
        clen = len(self.content) if isinstance(self.content, str) else "blocks"
        return f"ToolResult(tool_use_id={self.tool_use_id!r}, content=<{clen}>, is_error={self.is_error!r})"


@dataclass
class TextBlock:
    type: Literal["text"] = "text"
    text: str = ""

    def __repr__(self) -> str:
        return f"TextBlock(text={self.text[:60]!r}{'...' if len(self.text) > 60 else ''})"


ContentBlock = Union[TextBlock, ImageSource, ToolUse, ToolResult, Dict[str, Any]]


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def __repr__(self) -> str:
        return f"Usage(input={self.input_tokens}, output={self.output_tokens})"


@dataclass
class SystemPrompt:
    type: Literal["text"] = "text"
    text: str = ""
    cache_control: Optional[Dict[str, str]] = None

    def __repr__(self) -> str:
        return f"SystemPrompt(text={self.text[:60]!r}{'...' if len(self.text) > 60 else ''})"


@dataclass
class Message:
    role: Literal["user", "assistant"] = "user"
    content: Union[str, List[ContentBlock]] = field(default_factory=list)

    def __repr__(self) -> str:
        cr = self.content if isinstance(self.content, str) else f"[{len(self.content)} blocks]"
        return f"Message(role={self.role!r}, content={cr!r})"


@dataclass
class ToolDefinition:
    name: str = ""
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"ToolDefinition(name={self.name!r}, description={self.description[:40]!r}{'...' if len(self.description) > 40 else ''})"


@dataclass
class MessageResponse:
    id: str = ""
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    model: str = ""
    content: List[ContentBlock] = field(default_factory=list)
    stop_reason: Optional[StopReason] = None
    stop_sequence: Optional[str] = None
    usage: Usage = field(default_factory=Usage)

    def __repr__(self) -> str:
        return f"MessageResponse(id={self.id!r}, model={self.model!r}, content=[{len(self.content)}], stop_reason={self.stop_reason!r}, usage={self.usage!r})"


@dataclass
class CountTokensResponse:
    input_tokens: int = 0

    def __repr__(self) -> str:
        return f"CountTokensResponse(input_tokens={self.input_tokens})"


# ---------------------------------------------------------------------------
# Streaming Types
# ---------------------------------------------------------------------------


@dataclass
class MessageStartEvent:
    type: Literal["message_start"] = "message_start"
    message: MessageResponse = field(default_factory=MessageResponse)

    def __repr__(self) -> str:
        return f"MessageStartEvent(message={self.message!r})"


@dataclass
class ContentBlockStartEvent:
    type: Literal["content_block_start"] = "content_block_start"
    index: int = 0
    content_block: ContentBlock = field(default_factory=lambda: TextBlock())

    def __repr__(self) -> str:
        return f"ContentBlockStartEvent(index={self.index}, block={self.content_block!r})"


@dataclass
class ContentBlockDeltaEvent:
    type: Literal["content_block_delta"] = "content_block_delta"
    index: int = 0
    delta: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"ContentBlockDeltaEvent(index={self.index}, delta={self.delta!r})"


@dataclass
class ContentBlockStopEvent:
    type: Literal["content_block_stop"] = "content_block_stop"
    index: int = 0

    def __repr__(self) -> str:
        return f"ContentBlockStopEvent(index={self.index})"


@dataclass
class MessageDeltaEvent:
    type: Literal["message_delta"] = "message_delta"
    delta: Dict[str, Any] = field(default_factory=dict)
    usage: Optional[Usage] = None

    def __repr__(self) -> str:
        return f"MessageDeltaEvent(delta={self.delta!r}, usage={self.usage!r})"


@dataclass
class MessageStopEvent:
    type: Literal["message_stop"] = "message_stop"

    def __repr__(self) -> str:
        return "MessageStopEvent()"


@dataclass
class PingEvent:
    type: Literal["ping"] = "ping"

    def __repr__(self) -> str:
        return "PingEvent()"


StreamEvent = Union[
    MessageStartEvent, ContentBlockStartEvent, ContentBlockDeltaEvent,
    ContentBlockStopEvent, MessageDeltaEvent, MessageStopEvent, PingEvent,
]


# ---------------------------------------------------------------------------
# JSON (de)serialization helpers
# ---------------------------------------------------------------------------


def _to_dict(obj: Any) -> Any:
    """Recursively serialize a dataclass / list / dict / primitive tree."""
    if obj is None:
        return None
    if isinstance(obj, Enum):
        return obj.value
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        result: Dict[str, Any] = {}
        for fi in dataclasses.fields(obj):
            val = getattr(obj, fi.name)
            if val is None and fi.default is None:
                continue
            result[fi.name] = _to_dict(val)
        return result
    if isinstance(obj, (list, tuple)):
        return [_to_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    return obj


def _coerce_content_block(raw: Dict[str, Any]) -> ContentBlock:
    bt = raw.get("type", "text")
    if bt == "text":
        return TextBlock(type="text", text=raw.get("text", ""))
    if bt == "image":
        src = raw.get("source", {})
        return ImageSource(type="base64", media_type=src.get("media_type", "image/jpeg"), data=src.get("data", ""))
    if bt == "tool_use":
        return ToolUse(type="tool_use", id=raw.get("id", ""), name=raw.get("name", ""), input=raw.get("input", {}))
    if bt == "tool_result":
        return ToolResult(type="tool_result", tool_use_id=raw.get("tool_use_id", ""), content=raw.get("content", ""), is_error=raw.get("is_error", False))
    return raw


def _coerce_usage(raw: Optional[Dict[str, int]]) -> Usage:
    return Usage(input_tokens=raw.get("input_tokens", 0), output_tokens=raw.get("output_tokens", 0)) if raw else Usage()


def _coerce_message_response(raw: Dict[str, Any]) -> MessageResponse:
    return MessageResponse(
        id=raw.get("id", ""), type="message", role="assistant", model=raw.get("model", ""),
        content=[_coerce_content_block(c) for c in raw.get("content", [])],
        stop_reason=StopReason(raw["stop_reason"]) if raw.get("stop_reason") else None,
        stop_sequence=raw.get("stop_sequence"),
        usage=_coerce_usage(raw.get("usage")),
    )


def _coerce_message(raw: Dict[str, Any]) -> Message:
    content = raw.get("content", [])
    if isinstance(content, str):
        return Message(role=raw.get("role", "user"), content=content)
    return Message(role=raw.get("role", "user"), content=[_coerce_content_block(c) for c in content])


def _coerce_stream_event(raw: Dict[str, Any]) -> StreamEvent:
    et = raw.get("type", "")
    if et == "message_start":
        return MessageStartEvent(type="message_start", message=_coerce_message_response(raw.get("message", {})))
    if et == "content_block_start":
        return ContentBlockStartEvent(type="content_block_start", index=raw.get("index", 0), content_block=_coerce_content_block(raw.get("content_block", {})))
    if et == "content_block_delta":
        return ContentBlockDeltaEvent(type="content_block_delta", index=raw.get("index", 0), delta=raw.get("delta", {}))
    if et == "content_block_stop":
        return ContentBlockStopEvent(type="content_block_stop", index=raw.get("index", 0))
    if et == "message_delta":
        return MessageDeltaEvent(type="message_delta", delta=raw.get("delta", {}), usage=_coerce_usage(raw.get("usage")))
    if et == "message_stop":
        return MessageStopEvent(type="message_stop")
    if et == "ping":
        return PingEvent(type="ping")
    raise AnthropicError(f"Unknown stream event type: {et}")


# ---------------------------------------------------------------------------
# Retry / Rate-limiting
# ---------------------------------------------------------------------------


def _retry_delay(attempt: int, *, max_retries: int = DEFAULT_MAX_RETRIES, base_delay: float = 1.0, max_delay: float = 8.0) -> float:
    """Exponential backoff with full jitter."""
    if attempt >= max_retries:
        return 0.0
    return min(base_delay * (2 ** attempt), max_delay) * random.random()


# ---------------------------------------------------------------------------
# HTTP Transport (sync)
# ---------------------------------------------------------------------------


class HTTPTransport:
    """Synchronous HTTP transport using only `urllib.request`."""

    def __init__(self, *, api_key: str, base_url: str = DEFAULT_BASE_URL, timeout: float = DEFAULT_TIMEOUT, max_retries: int = DEFAULT_MAX_RETRIES) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._version = DEFAULT_API_VERSION

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json", "Accept": "application/json",
            "X-Api-Key": self.api_key, "Anthropic-Version": self._version,
            "User-Agent": "anthropic-sdk-native-python/1.0.0",
        }

    def _request(self, method: str, path: str, *, body: Optional[bytes] = None, stream: bool = False, extra_headers: Optional[Dict[str, str]] = None) -> Any:
        url = f"{self.base_url}{path}"
        headers = self._headers()
        if extra_headers:
            headers.update(extra_headers)
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            try:
                resp = urllib.request.urlopen(req, timeout=self.timeout)
                if stream:
                    return resp
                with resp:
                    data = resp.read()
                return json.loads(data.decode("utf-8")) if data else None
            except urllib.error.HTTPError as e:
                status = e.code
                try:
                    with e:
                        err_body = json.loads(e.read().decode("utf-8"))
                except Exception:
                    err_body = None
                msg = err_body.get("error", {}).get("message", f"HTTP {status}") if isinstance(err_body, dict) else f"HTTP {status}"
                last_error = _status_error_class(status)(msg, response=e, status_code=status, body=err_body)
                if (status == 429 or status >= 500) and attempt < self.max_retries:
                    time.sleep(_retry_delay(attempt, max_retries=self.max_retries))
                    continue
                raise last_error
            except (urllib.error.URLError, socket.timeout) as e:
                is_to = isinstance(e, socket.timeout) or (isinstance(e, urllib.error.URLError) and isinstance(e.reason, socket.timeout))
                last_error = APITimeoutError(str(e)) if is_to else APIConnectionError(str(e))
                if attempt < self.max_retries:
                    time.sleep(_retry_delay(attempt, max_retries=self.max_retries))
                    continue
                raise last_error
        if last_error is not None:
            raise last_error
        raise AnthropicError("Retry loop exhausted without a concrete error.")

    def get(self, path: str) -> Any:
        return self._request("GET", path)

    def post(self, path: str, *, json_data: Optional[Dict[str, Any]] = None, stream: bool = False, extra_headers: Optional[Dict[str, str]] = None) -> Any:
        body = json.dumps(json_data, default=_to_dict).encode("utf-8") if json_data is not None else None
        return self._request("POST", path, body=body, stream=stream, extra_headers=extra_headers)


# ---------------------------------------------------------------------------
# HTTP Transport (async)
# ---------------------------------------------------------------------------


class AsyncHTTPTransport:
    """Asynchronous HTTP transport using `asyncio` + `urllib.request` via executor."""

    def __init__(self, *, api_key: str, base_url: str = DEFAULT_BASE_URL, timeout: float = DEFAULT_TIMEOUT, max_retries: int = DEFAULT_MAX_RETRIES) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._version = DEFAULT_API_VERSION

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json", "Accept": "application/json",
            "X-Api-Key": self.api_key, "Anthropic-Version": self._version,
            "User-Agent": "anthropic-sdk-native-python/1.0.0",
        }

    async def _request(self, method: str, path: str, *, body: Optional[bytes] = None, stream: bool = False, extra_headers: Optional[Dict[str, str]] = None) -> Any:
        url = f"{self.base_url}{path}"
        headers = self._headers()
        if extra_headers:
            headers.update(extra_headers)
        last_error: Optional[Exception] = None
        loop = asyncio.get_event_loop()
        for attempt in range(self.max_retries + 1):
            try:
                def _do():
                    req = urllib.request.Request(url, data=body, headers=headers, method=method)
                    return urllib.request.urlopen(req, timeout=self.timeout)
                resp = await asyncio.wait_for(loop.run_in_executor(None, _do), timeout=self.timeout)
                if stream:
                    return resp
                data = await loop.run_in_executor(None, resp.read)
                resp.close()
                return json.loads(data.decode("utf-8")) if data else None
            except urllib.error.HTTPError as e:
                status = e.code
                try:
                    with e:
                        err_body = json.loads(e.read().decode("utf-8"))
                except Exception:
                    err_body = None
                msg = err_body.get("error", {}).get("message", f"HTTP {status}") if isinstance(err_body, dict) else f"HTTP {status}"
                last_error = _status_error_class(status)(msg, response=e, status_code=status, body=err_body)
                if (status == 429 or status >= 500) and attempt < self.max_retries:
                    await asyncio.sleep(_retry_delay(attempt, max_retries=self.max_retries))
                    continue
                raise last_error
            except (urllib.error.URLError, socket.timeout) as e:
                is_to = isinstance(e, socket.timeout) or (isinstance(e, urllib.error.URLError) and isinstance(e.reason, socket.timeout))
                last_error = APITimeoutError(str(e)) if is_to else APIConnectionError(str(e))
                if attempt < self.max_retries:
                    await asyncio.sleep(_retry_delay(attempt, max_retries=self.max_retries))
                    continue
                raise last_error
            except asyncio.TimeoutError:
                last_error = APITimeoutError("Request timed out.")
                if attempt < self.max_retries:
                    await asyncio.sleep(_retry_delay(attempt, max_retries=self.max_retries))
                    continue
                raise last_error
        if last_error is not None:
            raise last_error
        raise AnthropicError("Retry loop exhausted without a concrete error.")

    async def get(self, path: str) -> Any:
        return await self._request("GET", path)

    async def post(self, path: str, *, json_data: Optional[Dict[str, Any]] = None, stream: bool = False, extra_headers: Optional[Dict[str, str]] = None) -> Any:
        body = json.dumps(json_data, default=_to_dict).encode("utf-8") if json_data is not None else None
        return await self._request("POST", path, body=body, stream=stream, extra_headers=extra_headers)


# ---------------------------------------------------------------------------
# SSE Streaming Parser
# ---------------------------------------------------------------------------


def _iter_sse_lines(response: Any) -> Iterator[str]:
    buffer = b""
    while True:
        chunk = response.read(1024)
        if not chunk:
            break
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            yield line.decode("utf-8")
    if buffer:
        yield buffer.decode("utf-8")


def _parse_sse_stream(response: Any) -> Iterator[StreamEvent]:
    for line in _iter_sse_lines(response):
        line = line.strip()
        if line.startswith("data:"):
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                continue
            try:
                yield _coerce_stream_event(json.loads(data))
            except json.JSONDecodeError:
                continue


async def _async_iter_sse_lines(response: Any) -> AsyncIterator[str]:
    loop = asyncio.get_event_loop()
    buffer = b""
    while True:
        chunk = await loop.run_in_executor(None, response.read, 1024)
        if not chunk:
            break
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            yield line.decode("utf-8")
    if buffer:
        yield buffer.decode("utf-8")


async def _async_parse_sse_stream(response: Any) -> AsyncIterator[StreamEvent]:
    async for line in _async_iter_sse_lines(response):
        line = line.strip()
        if line.startswith("data:"):
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                continue
            try:
                yield _coerce_stream_event(json.loads(data))
            except json.JSONDecodeError:
                continue


# ---------------------------------------------------------------------------
# Client Builder
# ---------------------------------------------------------------------------


class AnthropicClientBuilder:
    """Fluent builder for configuring an AnthropicClient."""

    def __init__(self) -> None:
        self._api_key: Optional[str] = None
        self._base_url: str = DEFAULT_BASE_URL
        self._timeout: float = DEFAULT_TIMEOUT
        self._max_retries: int = DEFAULT_MAX_RETRIES

    def with_api_key(self, api_key: str) -> AnthropicClientBuilder:
        self._api_key = api_key
        return self

    def with_base_url(self, base_url: str) -> AnthropicClientBuilder:
        self._base_url = base_url
        return self

    def with_timeout(self, timeout: float) -> AnthropicClientBuilder:
        self._timeout = timeout
        return self

    def with_max_retries(self, max_retries: int) -> AnthropicClientBuilder:
        self._max_retries = max_retries
        return self

    def build(self) -> AnthropicClient:
        if not self._api_key:
            raise AnthropicError("API key is required. Set it via with_api_key() or ANTHROPIC_API_KEY env var.")
        return AnthropicClient(api_key=self._api_key, base_url=self._base_url, timeout=self._timeout, max_retries=self._max_retries)

    def build_async(self) -> AsyncAnthropicClient:
        if not self._api_key:
            raise AnthropicError("API key is required. Set it via with_api_key() or ANTHROPIC_API_KEY env var.")
        return AsyncAnthropicClient(api_key=self._api_key, base_url=self._base_url, timeout=self._timeout, max_retries=self._max_retries)


# ---------------------------------------------------------------------------
# Shared payload builder
# ---------------------------------------------------------------------------


def _build_messages_payload(
    *,
    model: str,
    max_tokens: int,
    messages: List[Message],
    system: Optional[Union[str, List[SystemPrompt]]] = None,
    tools: Optional[List[ToolDefinition]] = None,
    tool_choice: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, str]] = None,
    stop_sequences: Optional[List[str]] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    top_k: Optional[int] = None,
    stream: bool = False,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": model, "max_tokens": max_tokens,
        "messages": [_to_dict(m) for m in messages], "stream": stream,
    }
    if system is not None:
        payload["system"] = _to_dict(system)
    if tools is not None:
        payload["tools"] = [_to_dict(t) for t in tools]
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    if metadata is not None:
        payload["metadata"] = metadata
    if stop_sequences is not None:
        payload["stop_sequences"] = stop_sequences
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p
    if top_k is not None:
        payload["top_k"] = top_k
    return payload


# ---------------------------------------------------------------------------
# Messages Resource (sync)
# ---------------------------------------------------------------------------


class MessagesResource:
    """Resource-oriented accessor for the Messages API."""

    def __init__(self, transport: HTTPTransport) -> None:
        self._transport = transport

    def create(
        self, *, model: str, max_tokens: int, messages: List[Message],
        system: Optional[Union[str, List[SystemPrompt]]] = None,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, str]] = None,
        stop_sequences: Optional[List[str]] = None,
        temperature: Optional[float] = None, top_p: Optional[float] = None, top_k: Optional[int] = None,
        stream: bool = False,
    ) -> MessageResponse:
        """Create a non-streaming message."""
        raw = self._transport.post("/v1/messages", json_data=_build_messages_payload(
            model=model, max_tokens=max_tokens, messages=messages, system=system,
            tools=tools, tool_choice=tool_choice, metadata=metadata, stop_sequences=stop_sequences,
            temperature=temperature, top_p=top_p, top_k=top_k, stream=stream,
        ))
        return _coerce_message_response(raw)

    def stream(
        self, *, model: str, max_tokens: int, messages: List[Message],
        system: Optional[Union[str, List[SystemPrompt]]] = None,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, str]] = None,
        stop_sequences: Optional[List[str]] = None,
        temperature: Optional[float] = None, top_p: Optional[float] = None, top_k: Optional[int] = None,
    ) -> Iterator[StreamEvent]:
        """Create a streaming message and yield SSE events."""
        response = self._transport.post(
            "/v1/messages",
            json_data=_build_messages_payload(
                model=model, max_tokens=max_tokens, messages=messages, system=system,
                tools=tools, tool_choice=tool_choice, metadata=metadata, stop_sequences=stop_sequences,
                temperature=temperature, top_p=top_p, top_k=top_k, stream=True,
            ),
            stream=True,
            extra_headers={"Accept": "text/event-stream"},
        )
        try:
            yield from _parse_sse_stream(response)
        finally:
            response.close()

    def count_tokens(
        self, *, model: str, messages: List[Message],
        system: Optional[Union[str, List[SystemPrompt]]] = None,
        tools: Optional[List[ToolDefinition]] = None,
    ) -> CountTokensResponse:
        """Count tokens for a prospective message request."""
        payload: Dict[str, Any] = {"model": model, "messages": [_to_dict(m) for m in messages]}
        if system is not None:
            payload["system"] = _to_dict(system)
        if tools is not None:
            payload["tools"] = [_to_dict(t) for t in tools]
        raw = self._transport.post("/v1/messages/count_tokens", json_data=payload)
        return CountTokensResponse(input_tokens=raw.get("input_tokens", 0))


# ---------------------------------------------------------------------------
# Messages Resource (async)
# ---------------------------------------------------------------------------


class AsyncMessagesResource:
    """Asynchronous resource-oriented accessor for the Messages API."""

    def __init__(self, transport: AsyncHTTPTransport) -> None:
        self._transport = transport

    async def create(
        self, *, model: str, max_tokens: int, messages: List[Message],
        system: Optional[Union[str, List[SystemPrompt]]] = None,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, str]] = None,
        stop_sequences: Optional[List[str]] = None,
        temperature: Optional[float] = None, top_p: Optional[float] = None, top_k: Optional[int] = None,
        stream: bool = False,
    ) -> MessageResponse:
        """Create a non-streaming message (async)."""
        raw = await self._transport.post("/v1/messages", json_data=_build_messages_payload(
            model=model, max_tokens=max_tokens, messages=messages, system=system,
            tools=tools, tool_choice=tool_choice, metadata=metadata, stop_sequences=stop_sequences,
            temperature=temperature, top_p=top_p, top_k=top_k, stream=stream,
        ))
        return _coerce_message_response(raw)

    async def stream(
        self, *, model: str, max_tokens: int, messages: List[Message],
        system: Optional[Union[str, List[SystemPrompt]]] = None,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, str]] = None,
        stop_sequences: Optional[List[str]] = None,
        temperature: Optional[float] = None, top_p: Optional[float] = None, top_k: Optional[int] = None,
    ) -> AsyncIterator[StreamEvent]:
        """Create a streaming message and yield SSE events (async)."""
        response = await self._transport.post(
            "/v1/messages",
            json_data=_build_messages_payload(
                model=model, max_tokens=max_tokens, messages=messages, system=system,
                tools=tools, tool_choice=tool_choice, metadata=metadata, stop_sequences=stop_sequences,
                temperature=temperature, top_p=top_p, top_k=top_k, stream=True,
            ),
            stream=True,
            extra_headers={"Accept": "text/event-stream"},
        )
        try:
            async for event in _async_parse_sse_stream(response):
                yield event
        finally:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, response.close)

    async def count_tokens(
        self, *, model: str, messages: List[Message],
        system: Optional[Union[str, List[SystemPrompt]]] = None,
        tools: Optional[List[ToolDefinition]] = None,
    ) -> CountTokensResponse:
        """Count tokens for a prospective message request (async)."""
        payload: Dict[str, Any] = {"model": model, "messages": [_to_dict(m) for m in messages]}
        if system is not None:
            payload["system"] = _to_dict(system)
        if tools is not None:
            payload["tools"] = [_to_dict(t) for t in tools]
        raw = await self._transport.post("/v1/messages/count_tokens", json_data=payload)
        return CountTokensResponse(input_tokens=raw.get("input_tokens", 0))


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class AnthropicClient:
    """Synchronous Anthropic API client."""

    def __init__(self, *, api_key: Optional[str] = None, base_url: str = DEFAULT_BASE_URL, timeout: float = DEFAULT_TIMEOUT, max_retries: int = DEFAULT_MAX_RETRIES) -> None:
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise AnthropicError("API key is required. Pass api_key=... or set ANTHROPIC_API_KEY environment variable.")
        self._transport = HTTPTransport(api_key=resolved_key, base_url=base_url, timeout=timeout, max_retries=max_retries)
        self.messages = MessagesResource(self._transport)

    @staticmethod
    def builder() -> AnthropicClientBuilder:
        builder = AnthropicClientBuilder()
        env_key = os.environ.get("ANTHROPIC_API_KEY")
        if env_key:
            builder.with_api_key(env_key)
        return builder

    def __repr__(self) -> str:
        return f"AnthropicClient(base_url={self._transport.base_url!r}, timeout={self._transport.timeout})"


class AsyncAnthropicClient:
    """Asynchronous Anthropic API client."""

    def __init__(self, *, api_key: Optional[str] = None, base_url: str = DEFAULT_BASE_URL, timeout: float = DEFAULT_TIMEOUT, max_retries: int = DEFAULT_MAX_RETRIES) -> None:
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise AnthropicError("API key is required. Pass api_key=... or set ANTHROPIC_API_KEY environment variable.")
        self._transport = AsyncHTTPTransport(api_key=resolved_key, base_url=base_url, timeout=timeout, max_retries=max_retries)
        self.messages = AsyncMessagesResource(self._transport)

    @staticmethod
    def builder() -> AnthropicClientBuilder:
        builder = AnthropicClientBuilder()
        env_key = os.environ.get("ANTHROPIC_API_KEY")
        if env_key:
            builder.with_api_key(env_key)
        return builder

    def __repr__(self) -> str:
        return f"AsyncAnthropicClient(base_url={self._transport.base_url!r}, timeout={self._transport.timeout})"


# ---------------------------------------------------------------------------
# Convenience Helpers
# ---------------------------------------------------------------------------


def create_image_block(image_path: str, media_type: Optional[str] = None) -> Dict[str, Any]:
    """Load an image from disk and return an Anthropic image content block dict."""
    if media_type is None:
        media_type, _ = mimetypes.guess_type(image_path)
        if media_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
            media_type = "image/jpeg"
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}}


def create_text_block(text: str) -> TextBlock:
    """Create a text content block."""
    return TextBlock(type="text", text=text)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def main() -> None:
    """Run compact demos showcasing all SDK features."""
    print("\n" + "=" * 60)
    print("Anthropic SDK Native Python — Demo Suite")
    print("=" * 60 + "\n")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "sk-demo")

    # 1. Builder pattern
    print("--- Builder Pattern ---")
    client = AnthropicClient.builder().with_api_key(api_key).with_timeout(30.0).with_max_retries(3).build()
    print(f"Built: {client}\n")

    # 2. Sync messages.create
    print("--- Sync messages.create ---")
    msg = Message(role="user", content="Hello, Claude! What is 2 + 2?")
    try:
        resp = client.messages.create(
            model="claude-3-5-sonnet-20241022", max_tokens=256, messages=[msg],
            system="You are a helpful math tutor.", temperature=0.7,
        )
        print(f"Response: {resp}")
    except AnthropicError as exc:
        print(f"Expected error (demo key): {exc}")
    print()

    # 3. Sync streaming
    print("--- Sync messages.stream ---")
    try:
        for event in client.messages.stream(model="claude-3-5-sonnet-20241022", max_tokens=256, messages=[Message(role="user", content="Count from 1 to 5.")]):
            print(f"  Event: {event}")
    except AnthropicError as exc:
        print(f"Expected error (demo key): {exc}")
    print()

    # 4. Tool use
    print("--- Tool Use ---")
    weather_tool = ToolDefinition(
        name="get_weather", description="Retrieve current weather for a location.",
        input_schema={"type": "object", "properties": {"location": {"type": "string"}, "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}}, "required": ["location"]},
    )
    print(f"Tool: {weather_tool}")
    try:
        resp = client.messages.create(
            model="claude-3-5-sonnet-20241022", max_tokens=512,
            messages=[Message(role="user", content="What's the weather in Jakarta?")],
            tools=[weather_tool],
        )
        print(f"Response: {resp}")
    except AnthropicError as exc:
        print(f"Expected error (demo key): {exc}")
    print()

    # 5. Vision / image input
    print("--- Vision ---")
    img = ImageSource(type="base64", media_type="image/png", data="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
    vision_msg = Message(role="user", content=[TextBlock(type="text", text="Describe this image."), {"type": "image", "source": _to_dict(img)}])
    print(f"Vision message: {vision_msg}")
    try:
        resp = client.messages.create(model="claude-3-5-sonnet-20241022", max_tokens=512, messages=[vision_msg])
        print(f"Response: {resp}")
    except AnthropicError as exc:
        print(f"Expected error (demo key): {exc}")
    print()

    # 6. Token counting
    print("--- Token Count ---")
    try:
        count = client.messages.count_tokens(model="claude-3-5-sonnet-20241022", messages=[Message(role="user", content="How many tokens is this?")])
        print(f"Token count result: {count}")
    except AnthropicError as exc:
        print(f"Expected error (demo key): {exc}")
    print()

    # 7. Async client
    print("--- Async Client ---")
    async def _async_demo():
        async_client = AsyncAnthropicClient(api_key=api_key)
        print(f"Async client: {async_client}")
        try:
            resp = await async_client.messages.create(model="claude-3-5-sonnet-20241022", max_tokens=256, messages=[Message(role="user", content="Tell me a short joke.")])
            print(f"Async response: {resp}")
        except AnthropicError as exc:
            print(f"Expected error (demo key): {exc}")
    try:
        asyncio.run(_async_demo())
    except AnthropicError as exc:
        print(f"Expected error (demo key): {exc}")

    print("\n" + "=" * 60)
    print("Demo suite complete.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
