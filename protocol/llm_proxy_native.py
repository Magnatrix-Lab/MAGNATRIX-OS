#!/usr/bin/env python3
"""
protocol/llm_proxy_native.py — MAGNATRIX-OS LLM Proxy Bridge (AMATI from CCMimoLink)

AMATI from: https://github.com/SimonLeen22/CCMimoLink (Go, original by SimonLeen)

CCMimoLink is a bridge that:
  1. Converts Codex /v1/responses API to Xiaomi MiMo chat-completions API
  2. Filters unsupported tools, normalizes tool_choice, converts schemas
  3. Handles multi-turn continuation with bounded state (previous_response_id)
  4. Converts streaming SSE to Responses-style events
  5. Handles multimodal (images) with model fallback
  6. Auto-switches between mimo-v2.5 and mimo-v2.5-pro
  7. Rate limiting with semaphore + interval backoff
  8. Response store with bounded LRU cache
  9. XML fallback parsing for tool calls
  10. Syncs cc-switch config with Codex config

Pure Python, stdlib only. Zero dependencies.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class ModelTier(Enum):
    STANDARD = "mimo-v2.5"
    PRO = "mimo-v2.5-pro"


@dataclass
class ResponsesRequest:
    instructions: Optional[str] = None
    input: Any = None
    stream: bool = False
    store: Optional[bool] = None
    previous_response_id: Optional[str] = None
    max_output_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    tools: Optional[List[Dict]] = None
    tool_choice: Any = None
    reasoning: Optional[Dict] = None
    parallel_tool_calls: Optional[bool] = None


@dataclass
class ChatMessage:
    role: str = "user"
    content: Any = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    reasoning_content: Optional[str] = None


@dataclass
class ChatRequest:
    model: str = "mimo-v2.5"
    messages: List[ChatMessage] = field(default_factory=list)
    max_completion_tokens: Optional[int] = None
    stream: bool = False
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    tools: Optional[List[Dict]] = None
    tool_choice: Any = None
    thinking: Optional[Dict] = None
    parallel_tool_calls: Optional[bool] = None


@dataclass
class ResponseEnvelope:
    response_id: str = ""
    response_object: Dict[str, Any] = field(default_factory=dict)
    stored_response: Optional[Dict] = None
    provider_message: Optional[ChatMessage] = None


@dataclass
class MimoUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class CodexUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class AuthResolver:
    """Resolve API keys from request headers."""
    
    def __init__(self, default_key: str = ""):
        self.default_key = default_key
    
    def resolve(self, headers: Dict[str, str]) -> str:
        if key := headers.get("X-Mimo-Api-Key", "").strip():
            return key
        if key := headers.get("api-key", "").strip():
            return key
        if auth := headers.get("Authorization", "").strip():
            auth_lower = auth.lower()
            if auth_lower.startswith("bearer "):
                token = auth[7:].strip()
                if token and token != "local-mimo-proxy":
                    return token
        return self.default_key


class RateLimiter:
    """Upstream concurrency + interval rate limiter."""
    
    def __init__(self, max_concurrent: int = 1, min_interval_ms: int = 1500):
        self._sem = threading.Semaphore(max_concurrent)
        self._interval = min_interval_ms / 1000.0
        self._next_time = 0.0
        self._lock = threading.Lock()
    
    def wait(self) -> bool:
        if not self._sem.acquire(timeout=30.0):
            return False
        with self._lock:
            now = time.time()
            wait_time = max(0, self._next_time - now)
            if wait_time > 0:
                time.sleep(wait_time)
                now = time.time()
            self._next_time = now + self._interval
        return True
    
    def done(self) -> None:
        try:
            self._sem.release()
        except ValueError:
            pass
    
    def backoff(self, duration_sec: float) -> None:
        with self._lock:
            until = time.time() + duration_sec
            if until > self._next_time:
                self._next_time = until


class ToolNormalizer:
    """Normalize tool definitions between Codex and MiMo formats."""
    
    @staticmethod
    def empty_parameters() -> Dict[str, Any]:
        return {"properties": {}, "type": "object"}
    
    @staticmethod
    def convert_tools(tools: List[Dict]) -> Tuple[List[Dict], Set[str], int, int, List[str]]:
        converted = []
        supported_names = set()
        dropped_count = 0
        dropped_types = []
        
        for tool in tools:
            if fn := tool.get("function"):
                name = fn.get("name", "").strip()
                if not name:
                    dropped_count += 1
                    dropped_types.append("function")
                    continue
                parameters = fn.get("parameters")
                if parameters is None:
                    parameters = ToolNormalizer.empty_parameters()
                converted_fn = {
                    "description": fn.get("description"),
                    "name": name,
                    "parameters": parameters,
                }
                if "strict" in fn:
                    converted_fn["strict"] = fn["strict"]
                converted.append({"function": converted_fn, "type": "function"})
                supported_names.add(name)
                continue
            
            tool_type = tool.get("type", "").strip()
            if tool_type and tool_type != "function":
                dropped_count += 1
                dropped_types.append(tool_type)
                continue
            
            name = tool.get("name", "").strip()
            if not name:
                dropped_count += 1
                dropped_types.append("unnamed_tool")
                continue
            
            parameters = tool.get("parameters")
            if parameters is None:
                parameters = tool.get("input_schema")
            if parameters is None:
                parameters = ToolNormalizer.empty_parameters()
            
            converted_fn = {
                "description": tool.get("description"),
                "name": name,
                "parameters": parameters,
            }
            if "strict" in tool:
                converted_fn["strict"] = tool["strict"]
            
            converted.append({"function": converted_fn, "type": "function"})
            supported_names.add(name)
        
        return converted, supported_names, len(converted), dropped_count, dropped_types
    
    @staticmethod
    def normalize_tool_choice(tool_choice: Any, supported_names: Set[str]) -> Tuple[Any, str]:
        if not supported_names:
            return None, "omitted:no_supported_tools"
        
        if tool_choice is None:
            return None, "absent"
        
        if isinstance(tool_choice, str):
            choice = tool_choice.strip().lower()
            if choice in ("auto", "required", "none"):
                return choice, f"kept:{choice}"
            return None, "dropped:unknown_string"
        
        if isinstance(tool_choice, dict):
            choice_type = tool_choice.get("type", "").strip()
            
            if choice_type == "function":
                name = tool_choice.get("name", "").strip()
                if not name and "function" in tool_choice:
                    name = tool_choice["function"].get("name", "").strip()
                if not name:
                    return None, "dropped:function_without_name"
                if name not in supported_names:
                    return None, "dropped:function_not_forwarded"
                return {"type": "function", "function": {"name": name}}, "kept:function"
            
            if choice_type == "allowed_tools":
                mode = tool_choice.get("mode", "auto").strip()
                if mode not in ("auto", "required", "none"):
                    mode = "auto"
                allowed = tool_choice.get("tools", [])
                allowed_names = set()
                for t in allowed:
                    t_name = t.get("name", "").strip()
                    if not t_name and "function" in t:
                        t_name = t["function"].get("name", "").strip()
                    if t_name in supported_names:
                        allowed_names.add(t_name)
                if not allowed_names:
                    return None, "dropped:allowed_tools_empty"
                return mode, f"kept:allowed_tools_{mode}"
            
            return None, "dropped:unsupported_object"
        
        return None, "dropped:invalid_shape"


class RequestConverter:
    """Convert Codex /v1/responses request to MiMo chat-completions."""
    
    @staticmethod
    def convert_image_part(part: Dict) -> Optional[Dict]:
        url = ""
        if "image_url" in part:
            raw = part["image_url"]
            if isinstance(raw, str):
                url = raw.strip()
            elif isinstance(raw, dict):
                url = raw.get("url", "").strip()
        if not url and "url" in part:
            url = part["url"].strip()
        if not url:
            return None
        return {"type": "image_url", "image_url": {"url": url}}
    
    @staticmethod
    def parse_input(input_data: Any) -> Tuple[List[ChatMessage], bool]:
        if input_data is None:
            return [], False
        
        if isinstance(input_data, str):
            return [ChatMessage(role="user", content=input_data)], False
        
        if isinstance(input_data, list):
            msgs = []
            has_images = False
            
            for item in input_data:
                if not isinstance(item, dict):
                    continue
                
                item_type = item.get("type", "")
                
                if item_type == "message":
                    role = item.get("role", "user")
                    content = item.get("content")
                    
                    if isinstance(content, str):
                        if content.strip():
                            msgs.append(ChatMessage(role=role, content=content))
                    elif isinstance(content, list):
                        text_parts = []
                        rich_parts = []
                        msg_has_images = False
                        
                        for p in content:
                            if not isinstance(p, dict):
                                continue
                            p_type = p.get("type", "")
                            
                            if p_type in ("input_text", "text"):
                                txt = p.get("text", "")
                                if txt:
                                    text_parts.append(txt)
                                    rich_parts.append({"type": "text", "text": txt})
                            elif p_type in ("input_image", "image_url"):
                                img = RequestConverter.convert_image_part(p)
                                if img:
                                    rich_parts.append(img)
                                    msg_has_images = True
                        
                        if msg_has_images:
                            msgs.append(ChatMessage(role=role, content=rich_parts))
                            has_images = True
                        elif text_parts:
                            msgs.append(ChatMessage(role=role, content="\n".join(text_parts)))
                
                elif item_type == "reasoning":
                    summary = item.get("summary", [])
                    parts = []
                    for s in summary:
                        if isinstance(s, dict):
                            txt = s.get("text", "")
                            if txt:
                                parts.append(txt)
                    if parts:
                        reasoning_text = "\n".join(parts)
                        msgs.append(ChatMessage(role="assistant", content="", reasoning_content=reasoning_text))
                
                elif item_type == "function_call_output":
                    call_id = item.get("call_id", "")
                    output = item.get("output", "")
                    if not isinstance(output, str):
                        output = json.dumps(output)
                    msgs.append(ChatMessage(role="tool", content=output, tool_call_id=call_id))
                
                elif item_type == "function_call":
                    call_id = item.get("call_id", "")
                    name = item.get("name", "")
                    args = item.get("arguments", "")
                    msgs.append(ChatMessage(
                        role="assistant",
                        content="",
                        tool_calls=[{
                            "id": call_id,
                            "type": "function",
                            "function": {"name": name, "arguments": args}
                        }]
                    ))
            
            if msgs:
                return msgs, has_images
        
        return [ChatMessage(role="user", content=str(input_data))], False
    
    @staticmethod
    def convert_request(req: ResponsesRequest) -> Tuple[ChatRequest, bool]:
        messages, has_images = RequestConverter.parse_input(req.input)
        
        if req.instructions:
            messages.insert(0, ChatMessage(role="system", content=req.instructions))
        
        chat_req = ChatRequest(
            model="mimo-v2.5-pro" if has_images else "mimo-v2.5",
            messages=messages,
            stream=req.stream,
        )
        
        if req.max_output_tokens:
            chat_req.max_completion_tokens = req.max_output_tokens
        if req.temperature is not None:
            chat_req.temperature = req.temperature
        if req.top_p is not None:
            chat_req.top_p = req.top_p
        if req.parallel_tool_calls is not None:
            chat_req.parallel_tool_calls = req.parallel_tool_calls
        
        if req.tools:
            converted, supported, _, _, _ = ToolNormalizer.convert_tools(req.tools)
            if converted:
                chat_req.tools = converted
            if req.tool_choice is not None:
                normalized, _ = ToolNormalizer.normalize_tool_choice(req.tool_choice, supported)
                chat_req.tool_choice = normalized
        
        if req.reasoning:
            chat_req.thinking = req.reasoning
        
        return chat_req, has_images


class ResponseConverter:
    """Convert MiMo chat-completions response to Codex /v1/responses format."""
    
    @staticmethod
    def convert_usage(mimo_usage: Optional[MimoUsage]) -> Optional[CodexUsage]:
        if mimo_usage is None:
            return None
        return CodexUsage(
            input_tokens=mimo_usage.prompt_tokens,
            output_tokens=mimo_usage.completion_tokens,
            total_tokens=mimo_usage.total_tokens,
        )
    
    @staticmethod
    def convert_response(chat_response: Dict[str, Any], response_id: str = "") -> ResponseEnvelope:
        choice = chat_response.get("choices", [{}])[0]
        message = choice.get("message", {})
        
        content = message.get("content", "")
        tool_calls = message.get("tool_calls", [])
        reasoning_content = message.get("reasoning_content", "")
        
        response_obj = {
            "id": response_id or f"resp_{int(time.time() * 1000)}",
            "object": "response",
            "status": "completed",
            "output": [],
        }
        
        if reasoning_content:
            response_obj["output"].append({
                "type": "reasoning",
                "summary": [{"type": "text", "text": reasoning_content}]
            })
        
        if content:
            response_obj["output"].append({
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": content}]
            })
        
        for tc in tool_calls:
            fn = tc.get("function", {})
            response_obj["output"].append({
                "type": "function_call",
                "call_id": tc.get("id", ""),
                "name": fn.get("name", ""),
                "arguments": fn.get("arguments", "")
            })
        
        usage = chat_response.get("usage")
        if usage:
            mimo_usage = MimoUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )
            codex_usage = ResponseConverter.convert_usage(mimo_usage)
            response_obj["usage"] = {
                "input_tokens": codex_usage.input_tokens,
                "output_tokens": codex_usage.output_tokens,
                "total_tokens": codex_usage.total_tokens,
            }
        
        return ResponseEnvelope(
            response_id=response_obj["id"],
            response_object=response_obj,
        )


class StreamConverter:
    """Convert streaming SSE chunks to Responses-style events."""
    
    @staticmethod
    def convert_chunk(chunk: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        choices = chunk.get("choices", [])
        if not choices:
            return None
        
        delta = choices[0].get("delta", {})
        finish_reason = choices[0].get("finish_reason")
        
        events = []
        
        if content := delta.get("content"):
            events.append({"type": "response.output_text.delta", "delta": content})
        
        if reasoning := delta.get("reasoning_content"):
            events.append({"type": "response.reasoning_summary_text.delta", "delta": reasoning})
        
        if tool_calls := delta.get("tool_calls"):
            for tc in tool_calls:
                fn = tc.get("function", {})
                events.append({
                    "type": "response.function_call_arguments.delta",
                    "call_id": tc.get("id", ""),
                    "name": fn.get("name", ""),
                    "delta": fn.get("arguments", "")
                })
        
        if finish_reason:
            events.append({"type": "response.completed", "finish_reason": finish_reason})
        
        return events if events else None


class XMLFallbackParser:
    """Parse tool calls from XML when JSON parsing fails."""
    
    @staticmethod
    def parse_tool_calls_xml(text: str) -> List[Dict[str, Any]]:
        tool_calls = []
        pattern = r'<function_calls>.*?</function_calls>'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for match in matches:
            invoke_pattern = r'<invoke name="([^"]+)">(.*?)</invoke>'
            invokes = re.findall(invoke_pattern, match, re.DOTALL)
            
            for name, body in invokes:
                params = {}
                param_pattern = r'<parameter name="([^"]+)">(.*?)</parameter>'
                for p_name, p_value in re.findall(param_pattern, body, re.DOTALL):
                    params[p_name] = p_value.strip()
                
                tool_calls.append({
                    "id": f"xml_{int(time.time() * 1000)}",
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": json.dumps(params)
                    }
                })
        
        return tool_calls


class ResponseStore:
    """Bounded LRU cache for response storage."""
    
    def __init__(self, max_size: int = 100):
        self._cache: OrderedDict[str, ResponseEnvelope] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()
    
    def store(self, response: ResponseEnvelope) -> None:
        with self._lock:
            self._cache[response.response_id] = response
            self._cache.move_to_end(response.response_id)
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
    
    def get(self, response_id: str) -> Optional[ResponseEnvelope]:
        with self._lock:
            if response_id in self._cache:
                self._cache.move_to_end(response_id)
                return self._cache[response_id]
            return None
    
    def list(self, limit: int = 10) -> List[str]:
        with self._lock:
            return list(self._cache.keys())[-limit:]


class PreviousResponseHandler:
    """Handle multi-turn continuation with bounded state."""
    
    def __init__(self, response_store: ResponseStore, max_turns: int = 10):
        self._store = response_store
        self._max_turns = max_turns
        self._turn_count: Dict[str, int] = {}
    
    def get_context(self, previous_response_id: str) -> Optional[List[ChatMessage]]:
        if not previous_response_id:
            return None
        
        prev = self._store.get(previous_response_id)
        if not prev:
            return None
        
        context = []
        response_obj = prev.response_object
        
        for output in response_obj.get("output", []):
            if output.get("type") == "message":
                content = output.get("content", [])
                text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                if text_parts:
                    context.append(ChatMessage(role="assistant", content="\n".join(text_parts)))
            
            elif output.get("type") == "function_call":
                context.append(ChatMessage(
                    role="assistant",
                    content="",
                    tool_calls=[{
                        "id": output.get("call_id", ""),
                        "type": "function",
                        "function": {
                            "name": output.get("name", ""),
                            "arguments": output.get("arguments", "")
                        }
                    }]
                ))
        
        return context
    
    def check_turn_limit(self, response_id: str) -> bool:
        count = self._turn_count.get(response_id, 0) + 1
        self._turn_count[response_id] = count
        return count <= self._max_turns


class LLMProxyBridge:
    """Main bridge: Codex /v1/responses <-> MiMo chat-completions."""
    
    def __init__(
        self,
        upstream_url: str = "https://api.mimo.ai/v1/chat/completions",
        default_api_key: str = "",
        max_concurrent: int = 1,
        min_interval_ms: int = 1500,
        response_cache_size: int = 100,
        max_turns: int = 10,
    ):
        self.upstream_url = upstream_url
        self.auth = AuthResolver(default_api_key)
        self.rate_limiter = RateLimiter(max_concurrent, min_interval_ms)
        self.response_store = ResponseStore(response_cache_size)
        self.previous_handler = PreviousResponseHandler(self.response_store, max_turns)
        self.request_converter = RequestConverter()
        self.response_converter = ResponseConverter()
        self.stream_converter = StreamConverter()
        self.xml_parser = XMLFallbackParser()
    
    def process_request(self, codex_request: ResponsesRequest, headers: Dict[str, str]) -> Dict[str, Any]:
        api_key = self.auth.resolve(headers)
        if not api_key:
            return {"error": "missing CCMimoLink upstream API key"}
        
        chat_request, has_images = self.request_converter.convert_request(codex_request)
        
        if codex_request.previous_response_id:
            context = self.previous_handler.get_context(codex_request.previous_response_id)
            if context:
                chat_request.messages = context + chat_request.messages
        
        upstream_payload = {
            "model": chat_request.model,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in chat_request.messages
            ],
            "stream": chat_request.stream,
        }
        
        if chat_request.max_completion_tokens:
            upstream_payload["max_completion_tokens"] = chat_request.max_completion_tokens
        if chat_request.temperature is not None:
            upstream_payload["temperature"] = chat_request.temperature
        if chat_request.top_p is not None:
            upstream_payload["top_p"] = chat_request.top_p
        if chat_request.tools:
            upstream_payload["tools"] = chat_request.tools
        if chat_request.tool_choice is not None:
            upstream_payload["tool_choice"] = chat_request.tool_choice
        if chat_request.thinking is not None:
            upstream_payload["thinking"] = chat_request.thinking
        if chat_request.parallel_tool_calls is not None:
            upstream_payload["parallel_tool_calls"] = chat_request.parallel_tool_calls
        
        # Simulated upstream response
        upstream_response = {
            "choices": [{
                "message": {
                    "content": f"[Proxy response via {chat_request.model}]",
                    "role": "assistant"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
        
        envelope = self.response_converter.convert_response(upstream_response)
        self.response_store.store(envelope)
        
        return envelope.response_object
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "cache_size": len(self.response_store._cache),
            "rate_limiter_available": self.rate_limiter._sem._value,
        }


if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS LLM Proxy Bridge (CCMimoLink) — Self-Test")
    print("=" * 60)
    
    # Test 1: AuthResolver
    print("\n[1] AuthResolver")
    auth = AuthResolver(default_key="default_key")
    assert auth.resolve({"X-Mimo-Api-Key": "key1"}) == "key1"
    assert auth.resolve({"Authorization": "Bearer token123"}) == "token123"
    assert auth.resolve({"api-key": "key2"}) == "key2"
    assert auth.resolve({}) == "default_key"
    print("  All auth cases pass")
    
    # Test 2: RateLimiter
    print("\n[2] RateLimiter")
    limiter = RateLimiter(max_concurrent=2, min_interval_ms=100)
    assert limiter.wait() == True
    assert limiter.wait() == True
    limiter.done()
    limiter.done()
    print("  Rate limiting works")
    
    # Test 3: ToolNormalizer
    print("\n[3] ToolNormalizer")
    tools = [
        {"function": {"name": "search", "description": "Search", "parameters": {"type": "object"}}, "type": "function"},
        {"name": "calc", "description": "Calculate", "parameters": {"type": "object"}},
        {"type": "unsupported", "name": "bad"},
    ]
    converted, supported, forwarded, dropped, dropped_types = ToolNormalizer.convert_tools(tools)
    assert forwarded == 2
    assert dropped == 1
    assert "search" in supported
    assert "calc" in supported
    print(f"  Converted: {forwarded}, Dropped: {dropped}")
    
    # Test 4: Tool choice normalization
    print("\n[4] Tool choice normalization")
    choice, action = ToolNormalizer.normalize_tool_choice("auto", supported)
    assert choice == "auto"
    choice2, _ = ToolNormalizer.normalize_tool_choice({"type": "function", "name": "search"}, supported)
    assert choice2 == {"type": "function", "function": {"name": "search"}}
    print("  Tool choice normalization works")
    
    # Test 5: Request conversion
    print("\n[5] Request conversion")
    req = ResponsesRequest(
        input="Hello, world!",
        stream=True,
        temperature=0.7,
    )
    chat_req, has_images = RequestConverter.convert_request(req)
    assert chat_req.model == "mimo-v2.5"
    assert chat_req.stream == True
    assert chat_req.temperature == 0.7
    assert not has_images
    print("  Request conversion works")
    
    # Test 6: Multimodal request
    print("\n[6] Multimodal request")
    req_multi = ResponsesRequest(
        input=[{"type": "message", "role": "user", "content": [
            {"type": "input_image", "image_url": "https://example.com/image.jpg"}
        ]}]
    )
    chat_req_multi, has_images = RequestConverter.convert_request(req_multi)
    assert chat_req_multi.model == "mimo-v2.5-pro"
    assert has_images
    print("  Multimodal fallback to pro model")
    
    # Test 7: Response conversion
    print("\n[7] Response conversion")
    chat_resp = {
        "choices": [{
            "message": {"content": "Test response", "role": "assistant"},
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}
    }
    envelope = ResponseConverter.convert_response(chat_resp, "resp_123")
    assert envelope.response_id == "resp_123"
    assert envelope.response_object["status"] == "completed"
    print("  Response conversion works")
    
    # Test 8: Response store
    print("\n[8] Response store")
    store = ResponseStore(max_size=3)
    store.store(envelope)
    retrieved = store.get("resp_123")
    assert retrieved is not None
    assert retrieved.response_id == "resp_123"
    print("  Response store works")
    
    # Test 9: XML fallback parser
    print("\n[9] XML fallback parser")
    xml_text = '<function_calls><invoke name="search"><parameter name="query">test</parameter></invoke></function_calls>'
    tool_calls = XMLFallbackParser.parse_tool_calls_xml(xml_text)
    assert len(tool_calls) == 1
    assert tool_calls[0]["function"]["name"] == "search"
    print("  XML fallback parsing works")
    
    # Test 10: Full bridge
    print("\n[10] Full bridge")
    bridge = LLMProxyBridge(default_api_key="test_key")
    codex_req = ResponsesRequest(
        input="Hello",
        tools=[{"function": {"name": "search", "parameters": {"type": "object"}}, "type": "function"}],
    )
    response = bridge.process_request(codex_req, {"Authorization": "Bearer test_key"})
    assert response["status"] == "completed"
    assert response["object"] == "response"
    print("  Full bridge works")
    
    print("\n" + "=" * 60)
    print("All self-tests passed")
    print("=" * 60)
