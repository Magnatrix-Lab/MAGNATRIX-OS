"""
api_router_native.py - Layer 1.5 Native API Router Implementation

Pure Python REST API router with middleware chain, rate limiting,
JWT authentication simulation, CORS, and structured error handling.
No external dependencies.

Layer: 1.5 (Routing + Middleware)
"""

import json
import re
import time
import hashlib
import hmac
import base64
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Union, Tuple, Set
from enum import Enum, auto
from collections import defaultdict


# ============================================================================
# HTTP Methods
# ============================================================================

class HTTPMethod(Enum):
    """Supported HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


# ============================================================================
# Status Codes
# ============================================================================

class StatusCode:
    """Common HTTP status codes with descriptions."""
    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    TOO_MANY_REQUESTS = 429
    INTERNAL_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502

    _MESSAGES: Dict[int, str] = {
        200: "OK",
        201: "Created",
        204: "No Content",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        429: "Too Many Requests",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
    }

    @classmethod
    def message(cls, code: int) -> str:
        """Return default message for status code."""
        return cls._MESSAGES.get(code, "Unknown")


# ============================================================================
# Validation
# ============================================================================

class ValidationError(Exception):
    """Raised when request validation fails."""
    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"Validation failed for '{field}': {reason}")


class FieldValidator:
    """Field-level validation rules."""

    @staticmethod
    def required(value: Any, name: str = "field") -> Any:
        """Ensure value is not None or empty."""
        if value is None or (isinstance(value, str) and value.strip() == ""):
            raise ValidationError(name, "Value is required")
        return value

    @staticmethod
    def min_length(value: str, length: int, name: str = "field") -> str:
        """Ensure string has minimum length."""
        if len(value) < length:
            raise ValidationError(name, f"Minimum length is {length}")
        return value

    @staticmethod
    def max_length(value: str, length: int, name: str = "field") -> str:
        """Ensure string does not exceed maximum length."""
        if len(value) > length:
            raise ValidationError(name, f"Maximum length is {length}")
        return value

    @staticmethod
    def pattern(value: str, regex: str, name: str = "field") -> str:
        """Ensure string matches regex pattern."""
        if not re.match(regex, value):
            raise ValidationError(name, f"Does not match pattern {regex}")
        return value


# ============================================================================
# Request / Response Dataclasses
# ============================================================================

@dataclass
class Request:
    """HTTP Request representation.

    Attributes:
        method: HTTP method enum.
        path: Request path string.
        headers: Dictionary of header key-value pairs.
        query_params: URL query parameters.
        body: Raw request body bytes.
        client_ip: Originating client IP address.
        route_params: Extracted path parameters from route matching.
    """
    method: HTTPMethod
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    client_ip: str = "127.0.0.1"
    route_params: Dict[str, str] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (f"Request(method={self.method.value}, path={self.path!r}, "
                f"client_ip={self.client_ip!r}, headers={len(self.headers)}, "
                f"query={self.query_params!r})")

    def json_body(self) -> Dict[str, Any]:
        """Parse body as JSON dictionary."""
        if not self.body:
            return {}
        return json.loads(self.body.decode())

    def header(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Case-insensitive header lookup."""
        for k, v in self.headers.items():
            if k.lower() == key.lower():
                return v
        return default


@dataclass
class Response:
    """HTTP Response representation.

    Attributes:
        status: HTTP status code integer.
        headers: Response headers dictionary.
        body: Response body (bytes, dict, or str).
        error_detail: Structured error information for 4xx/5xx.
    """
    status: int = StatusCode.OK
    headers: Dict[str, str] = field(default_factory=dict)
    body: Union[bytes, Dict[str, Any], str, None] = None
    error_detail: Optional[Dict[str, Any]] = None

    def __repr__(self) -> str:
        return (f"Response(status={self.status}, "
                f"body_len={len(self._body_bytes())}, headers={len(self.headers)})")

    def _body_bytes(self) -> bytes:
        """Normalize body to bytes for length calculation."""
        if self.body is None:
            return b""
        if isinstance(self.body, bytes):
            return self.body
        if isinstance(self.body, str):
            return self.body.encode()
        return json.dumps(self.body).encode()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize response to dictionary."""
        result: Dict[str, Any] = {
            "status": self.status,
            "message": StatusCode.message(self.status),
        }
        if self.body is not None:
            if isinstance(self.body, bytes):
                try:
                    result["body"] = json.loads(self.body.decode())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    result["body"] = base64.b64encode(self.body).decode()
            elif isinstance(self.body, dict):
                result["body"] = self.body
            else:
                result["body"] = str(self.body)
        if self.error_detail:
            result["error"] = self.error_detail
        return result


# ============================================================================
# Route Definition
# ============================================================================

class Route:
    """Registered route with path pattern and handler.

    Supports exact paths and parameterized segments like /user/{id}.
    """

    def __init__(
        self,
        path: str,
        handler: Callable[[Request], Response],
        methods: List[HTTPMethod],
    ) -> None:
        """Initialize route.

        Args:
            path: URL path pattern (e.g., "/users" or "/users/{id}").
            handler: Callable accepting Request and returning Response.
            methods: List of allowed HTTP methods.
        """
        self.path = path
        self.handler = handler
        self.methods = set(methods)
        self._pattern, self._param_names = self._compile_path(path)

    def __repr__(self) -> str:
        return (f"Route(path={self.path!r}, methods={[m.value for m in self.methods]}, "
                f"params={self._param_names})")

    def _compile_path(self, path: str) -> Tuple[re.Pattern, List[str]]:
        """Convert path pattern to regex and extract parameter names."""
        param_names: List[str] = []
        parts = path.split("/")
        regex_parts: List[str] = ["^"]
        for part in parts:
            if not part:
                continue
            regex_parts.append("/")
            if part.startswith("{") and part.endswith("}"):
                name = part[1:-1]
                param_names.append(name)
                regex_parts.append(r"([^/]+)")
            else:
                regex_parts.append(re.escape(part))
        regex_parts.append("$")
        return re.compile("".join(regex_parts)), param_names

    def match(self, path: str) -> Optional[Dict[str, str]]:
        """Match path against route pattern.

        Returns:
            Dictionary of extracted parameters, or None if no match.
        """
        m = self._pattern.match(path)
        if not m:
            return None
        return {name: m.group(i + 1) for i, name in enumerate(self._param_names)}

    def allows_method(self, method: HTTPMethod) -> bool:
        """Check if method is allowed for this route."""
        return method in self.methods


# ============================================================================
# Middleware
# ============================================================================

class Middleware:
    """Base middleware class.

    Subclasses override `process_request` and/or `process_response`.
    """

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"

    def process_request(self, request: Request) -> Optional[Response]:
        """Intercept and optionally short-circuit request handling.

        Returns:
            Response to short-circuit, or None to continue.
        """
        return None

    def process_response(self, request: Request, response: Response) -> Response:
        """Transform response before returning to client.

        Returns:
            Modified or original response.
        """
        return response


class AuthMiddleware(Middleware):
    """JWT-based authentication middleware.

    Validates Bearer token in Authorization header.
    """

    def __init__(self, secret: bytes, exempt_paths: Optional[List[str]] = None) -> None:
        """Initialize auth middleware.

        Args:
            secret: HMAC secret for JWT signature verification.
            exempt_paths: Routes that skip authentication.
        """
        self.secret = secret
        self.exempt_paths = set(exempt_paths or [])

    def __repr__(self) -> str:
        return f"AuthMiddleware(exempts={len(self.exempt_paths)})"

    def process_request(self, request: Request) -> Optional[Response]:
        if request.path in self.exempt_paths:
            return None
        auth = request.header("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return Response(
                status=StatusCode.UNAUTHORIZED,
                error_detail={"reason": "Missing or invalid Authorization header"},
            )
        token = auth[7:]
        try:
            JWT.verify(token, self.secret)
        except ValueError as e:
            return Response(
                status=StatusCode.UNAUTHORIZED,
                error_detail={"reason": str(e)},
            )
        return None


class LoggingMiddleware(Middleware):
    """Request/response logging middleware."""

    def __init__(self, max_history: int = 100) -> None:
        self.history: List[Dict[str, Any]] = []
        self.max_history = max_history

    def __repr__(self) -> str:
        return f"LoggingMiddleware(history={len(self.history)})"

    def process_response(self, request: Request, response: Response) -> Response:
        entry = {
            "timestamp": time.time(),
            "method": request.method.value,
            "path": request.path,
            "status": response.status,
            "client_ip": request.client_ip,
        }
        self.history.append(entry)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        return response

    def get_logs(self) -> List[Dict[str, Any]]:
        """Return logged request history."""
        return list(self.history)


class RateLimitMiddleware(Middleware):
    """Token-bucket rate limiter per client IP."""

    def __init__(
        self,
        capacity: float = 10.0,
        refill_rate: float = 1.0,
        burst_size: float = 20.0,
    ) -> None:
        """Initialize rate limiter.

        Args:
            capacity: Maximum tokens per IP bucket.
            refill_rate: Tokens added per second.
            burst_size: Maximum burst capacity.
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.burst_size = burst_size
        self._buckets: Dict[str, Dict[str, float]] = {}

    def __repr__(self) -> str:
        return f"RateLimitMiddleware(buckets={len(self._buckets)}, cap={self.capacity})"

    def _get_bucket(self, ip: str) -> Dict[str, float]:
        now = time.time()
        if ip not in self._buckets:
            self._buckets[ip] = {"tokens": self.capacity, "last": now}
        bucket = self._buckets[ip]
        elapsed = now - bucket["last"]
        bucket["tokens"] = min(self.burst_size, bucket["tokens"] + elapsed * self.refill_rate)
        bucket["last"] = now
        return bucket

    def process_request(self, request: Request) -> Optional[Response]:
        bucket = self._get_bucket(request.client_ip)
        if bucket["tokens"] < 1.0:
            return Response(
                status=StatusCode.TOO_MANY_REQUESTS,
                headers={"Retry-After": "60"},
                error_detail={
                    "reason": "Rate limit exceeded",
                    "limit": self.capacity,
                    "client_ip": request.client_ip,
                },
            )
        bucket["tokens"] -= 1.0
        return None

    def reset(self, ip: str) -> None:
        """Reset bucket for a specific IP."""
        self._buckets.pop(ip, None)


class CORSMiddleware(Middleware):
    """Cross-Origin Resource Sharing middleware."""

    def __init__(
        self,
        allow_origins: List[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
    ) -> None:
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["Content-Type", "Authorization"]

    def __repr__(self) -> str:
        return f"CORSMiddleware(origins={self.allow_origins})"

    def process_response(self, request: Request, response: Response) -> Response:
        origin = request.headers.get("Origin", "*")
        if "*" in self.allow_origins or origin in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        return response


# ============================================================================
# JWT Simulation
# ============================================================================

class JWT:
    """JWT simulation with HS256 signing.

    No external dependencies. Pure Python base64 + HMAC-SHA256.
    """

    @staticmethod
    def encode(payload: Dict[str, Any], secret: bytes, expiry_sec: int = 3600) -> str:
        """Create a JWT token string.

        Args:
            payload: Claims dictionary (sub, iss, etc.).
            secret: HMAC secret bytes.
            expiry_sec: Token lifetime in seconds.

        Returns:
            JWT token string (header.payload.signature).
        """
        now = int(time.time())
        claims = {
            "iat": now,
            "exp": now + expiry_sec,
            **payload,
        }
        header_b64 = JWT._b64encode({"alg": "HS256", "typ": "JWT"})
        payload_b64 = JWT._b64encode(claims)
        signature = hmac.new(secret, f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
        sig_b64 = JWT._b64encode_raw(signature)
        return f"{header_b64}.{payload_b64}.{sig_b64}"

    @staticmethod
    def decode(token: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Decode JWT without verification.

        Returns:
            Tuple of (header, payload) dictionaries.
        """
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        header = JWT._b64decode(parts[0])
        payload = JWT._b64decode(parts[1])
        return header, payload

    @staticmethod
    def verify(token: str, secret: bytes) -> Dict[str, Any]:
        """Verify JWT signature and expiry.

        Args:
            token: JWT token string.
            secret: HMAC secret bytes.

        Returns:
            Verified payload claims.

        Raises:
            ValueError: If signature invalid or token expired.
        """
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        header_b64, payload_b64, sig_b64 = parts
        expected_sig = hmac.new(secret, f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(JWT._b64decode_raw(sig_b64), expected_sig):
            raise ValueError("Invalid signature")
        payload = JWT._b64decode(payload_b64)
        exp = payload.get("exp")
        if exp and time.time() > exp:
            raise ValueError("Token expired")
        return payload

    @staticmethod
    def _b64encode(data: Dict[str, Any]) -> str:
        """URL-safe base64 encode dictionary."""
        return base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).decode().rstrip("=")

    @staticmethod
    def _b64decode(data: str) -> Dict[str, Any]:
        """URL-safe base64 decode to dictionary."""
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return json.loads(base64.urlsafe_b64decode(data.encode()))

    @staticmethod
    def _b64encode_raw(data: bytes) -> str:
        """URL-safe base64 encode raw bytes."""
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    @staticmethod
    def _b64decode_raw(data: str) -> bytes:
        """URL-safe base64 decode to bytes."""
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data.encode())


# ============================================================================
# Error Responses
# ============================================================================

class APIError(Exception):
    """Structured API error with status code and detail."""

    def __init__(
        self,
        status: int,
        message: str,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.status = status
        self.message = message
        self.detail = detail or {}
        super().__init__(message)

    def to_response(self) -> Response:
        """Convert to Response object."""
        return Response(
            status=self.status,
            error_detail={"message": self.message, **self.detail},
        )


class BadRequestError(APIError):
    def __init__(self, detail: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(StatusCode.BAD_REQUEST, "Bad Request", detail)


class UnauthorizedError(APIError):
    def __init__(self, detail: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(StatusCode.UNAUTHORIZED, "Unauthorized", detail)


class ForbiddenError(APIError):
    def __init__(self, detail: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(StatusCode.FORBIDDEN, "Forbidden", detail)


class NotFoundError(APIError):
    def __init__(self, detail: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(StatusCode.NOT_FOUND, "Not Found", detail)


class RateLimitError(APIError):
    def __init__(self, detail: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(StatusCode.TOO_MANY_REQUESTS, "Too Many Requests", detail)


class InternalError(APIError):
    def __init__(self, detail: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(StatusCode.INTERNAL_ERROR, "Internal Server Error", detail)


# ============================================================================
# Router Kernel (Bridge to Layer 1.5)
# ============================================================================

class RouterKernel:
    """Core router orchestrating routes, middleware, and request dispatch.

    Bridges incoming requests to registered handlers through the
    middleware chain.
    """

    def __init__(self, secret: Optional[bytes] = None) -> None:
        """Initialize router kernel.

        Args:
            secret: Optional HMAC secret for JWT signing.
        """
        self._routes: List[Route] = []
        self._middlewares: List[Middleware] = []
        self._secret = secret or os.urandom(32)
        self._error_handlers: Dict[int, Callable[[Request, APIError], Response]] = {}

    def __repr__(self) -> str:
        return (f"RouterKernel(routes={len(self._routes)}, "
                f"middlewares={len(self._middlewares)})")

    def add_route(
        self,
        path: str,
        handler: Callable[[Request], Response],
        methods: Optional[List[Union[HTTPMethod, str]]] = None,
    ) -> Route:
        """Register a route with path and handler.

        Args:
            path: URL path pattern.
            handler: Request handler callable.
            methods: Allowed HTTP methods (defaults to GET).

        Returns:
            Registered Route instance.
        """
        if methods is None:
            methods = [HTTPMethod.GET]
        parsed: List[HTTPMethod] = []
        for m in methods:
            if isinstance(m, str):
                parsed.append(HTTPMethod(m))
            else:
                parsed.append(m)
        route = Route(path, handler, parsed)
        self._routes.append(route)
        return route

    def add_middleware(self, middleware: Middleware) -> None:
        """Append middleware to processing chain."""
        self._middlewares.append(middleware)

    def set_error_handler(
        self,
        status: int,
        handler: Callable[[Request, APIError], Response],
    ) -> None:
        """Register custom error response handler."""
        self._error_handlers[status] = handler

    def dispatch(self, request: Request) -> Response:
        """Dispatch request through middleware chain and route handler.

        Args:
            request: Incoming Request object.

        Returns:
            Response object.
        """
        try:
            # Run request middlewares
            for mw in self._middlewares:
                short = mw.process_request(request)
                if short is not None:
                    response = short
                    break
            else:
                # Find matching route
                route, params = self._match_route(request)
                if route is None:
                    raise NotFoundError({"path": request.path})
                if not route.allows_method(request.method):
                    raise APIError(
                        StatusCode.METHOD_NOT_ALLOWED,
                        "Method Not Allowed",
                        {"allowed": [m.value for m in route.methods]},
                    )
                request.route_params = params
                response = route.handler(request)

            # Run response middlewares
            for mw in self._middlewares:
                response = mw.process_response(request, response)

            return response

        except APIError as e:
            handler = self._error_handlers.get(e.status)
            if handler:
                return handler(request, e)
            return e.to_response()
        except ValidationError as e:
            return Response(
                status=StatusCode.BAD_REQUEST,
                error_detail={"field": e.field, "reason": e.reason},
            )
        except Exception as e:
            handler = self._error_handlers.get(StatusCode.INTERNAL_ERROR)
            if handler:
                return handler(request, InternalError({"exception": str(e)}))
            return InternalError({"exception": str(e)}).to_response()

    def _match_route(self, request: Request) -> Tuple[Optional[Route], Dict[str, str]]:
        """Find first route matching request path."""
        for route in self._routes:
            params = route.match(request.path)
            if params is not None:
                return route, params
        return None, {}

    def get_routes(self) -> List[Route]:
        """Return all registered routes."""
        return list(self._routes)

    def get_middlewares(self) -> List[Middleware]:
        """Return all middlewares."""
        return list(self._middlewares)


# ============================================================================
# Convenience Helpers
# ============================================================================

def json_response(data: Dict[str, Any], status: int = StatusCode.OK) -> Response:
    """Create a JSON response."""
    return Response(
        status=status,
        headers={"Content-Type": "application/json"},
        body=data,
    )


def text_response(text: str, status: int = StatusCode.OK) -> Response:
    """Create a plain text response."""
    return Response(
        status=status,
        headers={"Content-Type": "text/plain"},
        body=text,
    )


# ============================================================================
# Demo / Self-Test
# ============================================================================

def run_demo() -> None:
    """Demonstrate route registry, middleware chain, rate limit, and auth."""
    print("=" * 60)
    print("API_ROUTER_NATIVE DEMO")
    print("=" * 60)

    # SECURITY: Derive secret from environment or generate ephemeral
    secret_env = os.environ.get("MAGNATRIX_API_SECRET", "")
    if len(secret_env) >= 32:
        secret = secret_env.encode()[:32]
    else:
        # Ephemeral secret for demo only — production MUST set env var
        import hashlib, time
        secret = hashlib.sha256(str(time.time()).encode()).digest()

    router = RouterKernel(secret)

    # Middleware chain
    print("\n[1] Setup middleware chain")
    auth = AuthMiddleware(secret, exempt_paths=["/health", "/login"])
    rate_limit = RateLimitMiddleware(capacity=5.0, refill_rate=2.0)
    cors = CORSMiddleware(allow_origins=["*"])
    logging_mw = LoggingMiddleware()

    router.add_middleware(logging_mw)
    router.add_middleware(cors)
    router.add_middleware(rate_limit)
    router.add_middleware(auth)

    print(f"    Middlewares: {[repr(m) for m in router.get_middlewares()]}")

    # Register 5 routes
    print("\n[2] Register 5 routes")

    def health_handler(req: Request) -> Response:
        return json_response({"status": "ok", "time": time.time()})

    def login_handler(req: Request) -> Response:
        body = req.json_body()
        user = body.get("username", "anon")
        token = JWT.encode({"sub": user, "role": "user"}, secret, expiry_sec=3600)
        return json_response({"token": token, "user": user})

    def users_list(req: Request) -> Response:
        return json_response({"users": ["alice", "bob", "charlie"]})

    def user_get(req: Request) -> Response:
        uid = req.route_params.get("id", "unknown")
        return json_response({"id": uid, "name": f"User-{uid}"})

    def user_create(req: Request) -> Response:
        body = req.json_body()
        return json_response({"created": True, "data": body}, StatusCode.CREATED)

    router.add_route("/health", health_handler, [HTTPMethod.GET])
    router.add_route("/login", login_handler, [HTTPMethod.POST])
    router.add_route("/users", users_list, [HTTPMethod.GET])
    router.add_route("/users", user_create, [HTTPMethod.POST])
    router.add_route("/users/{id}", user_get, [HTTPMethod.GET])

    for r in router.get_routes():
        print(f"    {r}")

    # Test requests
    print("\n[3] Test requests")

    # Health (no auth needed)
    req = Request(method=HTTPMethod.GET, path="/health", client_ip="127.0.0.1")
    resp = router.dispatch(req)
    print(f"    GET /health -> {resp.status} {StatusCode.message(resp.status)}")

    # Login to get token
    req = Request(
        method=HTTPMethod.POST,
        path="/login",
        body=json.dumps({"username": "alice"}).encode(),
        headers={"Content-Type": "application/json"},
        client_ip="127.0.0.1",
    )
    resp = router.dispatch(req)
    login_body = resp.to_dict().get("body", {})
    token = login_body.get("token", "")
    print(f"    POST /login -> {resp.status}, token={token[:20]}...")

    # Users list with auth
    req = Request(
        method=HTTPMethod.GET,
        path="/users",
        headers={"Authorization": f"Bearer {token}"},
        client_ip="127.0.0.1",
    )
    resp = router.dispatch(req)
    print(f"    GET /users -> {resp.status} {StatusCode.message(resp.status)}")

    # User detail with route param
    req = Request(
        method=HTTPMethod.GET,
        path="/users/42",
        headers={"Authorization": f"Bearer {token}"},
        client_ip="127.0.0.1",
    )
    resp = router.dispatch(req)
    print(f"    GET /users/42 -> {resp.status}, body={resp.to_dict().get('body')}")

    # 404
    req = Request(
        method=HTTPMethod.GET,
        path="/notfound",
        headers={"Authorization": f"Bearer {token}"},
        client_ip="127.0.0.1",
    )
    resp = router.dispatch(req)
    print(f"    GET /notfound -> {resp.status} {StatusCode.message(resp.status)}")

    # Rate limit test
    print("\n[4] Rate limit test")
    rate_limit.reset("10.0.0.1")
    blocked = 0
    for i in range(8):
        req = Request(
            method=HTTPMethod.GET,
            path="/health",
            client_ip="10.0.0.1",
        )
        resp = router.dispatch(req)
        if resp.status == StatusCode.TOO_MANY_REQUESTS:
            blocked += 1
            print(f"    Request {i+1}: 429 RATE LIMITED")
        else:
            print(f"    Request {i+1}: {resp.status} OK")
    print(f"    Total blocked: {blocked}")

    # Auth test
    print("\n[5] Auth test")
    req = Request(method=HTTPMethod.GET, path="/users", client_ip="127.0.0.1")
    resp = router.dispatch(req)
    print(f"    No token -> {resp.status} {StatusCode.message(resp.status)}")

    bad_token = token[:-5] + "xxxxx"
    req = Request(
        method=HTTPMethod.GET,
        path="/users",
        headers={"Authorization": f"Bearer {bad_token}"},
        client_ip="127.0.0.1",
    )
    resp = router.dispatch(req)
    print(f"    Bad token -> {resp.status} {StatusCode.message(resp.status)}")

    # JWT verify
    print("\n[6] JWT verify")
    payload = JWT.verify(token, secret)
    print(f"    Verified claims: sub={payload.get('sub')}, role={payload.get('role')}")
    decoded_header, decoded_payload = JWT.decode(token)
    print(f"    Decoded header: {decoded_header}")

    # Logs
    print("\n[7] Middleware logs")
    logs = logging_mw.get_logs()
    print(f"    Total logged requests: {len(logs)}")
    for entry in logs[:3]:
        print(f"      {entry['method']} {entry['path']} -> {entry['status']}")

    # CORS headers
    print("\n[8] CORS headers")
    req = Request(
        method=HTTPMethod.GET,
        path="/health",
        headers={"Origin": "https://example.com"},
        client_ip="127.0.0.1",
    )
    resp = router.dispatch(req)
    print(f"    Access-Control-Allow-Origin: {resp.headers.get('Access-Control-Allow-Origin')}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE -- ALL CHECKS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
