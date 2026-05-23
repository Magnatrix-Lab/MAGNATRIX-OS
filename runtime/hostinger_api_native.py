"""
Hostinger API Native Python SDK
================================
Native Python SDK for Hostinger API (83 endpoints, 31 service tags).
Pure Python — urllib default, httpx optional. No hard dependencies.

Architecture:
- HostingerClient: base HTTP with bearer auth, rate-limit retry, pagination
- RequestBuilder: fluent API for query/path/body construction
- ErrorHandler: exception hierarchy with auto-retry + jitter
- Service APIs: Billing, DNS, Domains, Hosting, VPS, Reach
- HostingerKernel: MAGNATRIX Layer 7/5/11 bridge

Author: GQRIS / MAGNATRIX-OS
File: runtime/hostinger_api_native.py
"""

from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

# Optional async / advanced HTTP
_try_httpx = False
_httpx: Any = None
try:
    import httpx
    _httpx = httpx
    _try_httpx = True
except Exception:
    pass

# ---------------------------------------------------------------------------
# Exception Hierarchy
# ---------------------------------------------------------------------------


class HostingerError(Exception):
    """Base exception for all Hostinger API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        request_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        self.request_info = request_info or {}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"status_code={self.status_code}, "
            f"request_url={self.request_info.get('url')!r}"
            f")"
        )


class HostingerAuthError(HostingerError):
    """401 Unauthorized — invalid or expired bearer token."""

    pass


class HostingerRateLimitError(HostingerError):
    """429 Too Many Requests — hit rate limit, retry after suggested."""

    def __init__(
        self,
        message: str,
        status_code: int = 429,
        retry_after: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code, **kwargs)
        self.retry_after = retry_after


class HostingerNotFoundError(HostingerError):
    """404 Not Found — resource does not exist."""

    pass


class HostingerValidationError(HostingerError):
    """422 Unprocessable Entity — request validation failed."""

    def __init__(
        self,
        message: str,
        status_code: int = 422,
        errors: Optional[Dict[str, List[str]]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code, **kwargs)
        self.errors = errors or {}


class HostingerServerError(HostingerError):
    """500+ Internal Server Error — transient, retry eligible."""

    pass


class HostingerConflictError(HostingerError):
    """409 Conflict — resource conflict (e.g., duplicate domain)."""

    pass


class HostingerPermissionError(HostingerError):
    """403 Forbidden — insufficient permissions."""

    pass


# ---------------------------------------------------------------------------
# Utility / Helpers
# ---------------------------------------------------------------------------


def _to_snake(name: str) -> str:
    """Convert camelCase to snake_case for dataclass field aliasing."""
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _map_camel_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively map camelCase dict keys to snake_case."""
    if not isinstance(data, dict):
        return data
    mapped: Dict[str, Any] = {}
    for k, v in data.items():
        key = _to_snake(k)
        if isinstance(v, dict):
            mapped[key] = _map_camel_dict(v)
        elif isinstance(v, list):
            mapped[key] = [_map_camel_dict(i) if isinstance(i, dict) else i for i in v]
        else:
            mapped[key] = v
    return mapped


def _serialize_body(body: Any) -> Optional[bytes]:
    if body is None:
        return None
    if isinstance(body, (dict, list)):
        return json.dumps(body).encode("utf-8")
    if isinstance(body, str):
        return body.encode("utf-8")
    if hasattr(body, "__dataclass_fields__"):
        d = asdict(body)
        # remove None values for compactness
        d = {k: v for k, v in d.items() if v is not None}
        return json.dumps(d).encode("utf-8")
    return None


# ---------------------------------------------------------------------------
# Pagination & Meta Types
# ---------------------------------------------------------------------------


@dataclass
class Pagination:
    """Pagination metadata from list endpoints."""

    current_page: int = 1
    per_page: int = 25
    total: int = 0
    total_pages: int = 1
    next_page_url: Optional[str] = None
    prev_page_url: Optional[str] = None
    from_field: Optional[int] = None
    to_field: Optional[int] = None

    def has_next(self) -> bool:
        return self.next_page_url is not None or self.current_page < self.total_pages

    def has_prev(self) -> bool:
        return self.prev_page_url is not None or self.current_page > 1

    def __repr__(self) -> str:
        return (
            f"Pagination(page={self.current_page}/{self.total_pages}, "
            f"total={self.total})"
        )


@dataclass
class Meta:
    """Response-level metadata."""

    request_id: Optional[str] = None
    timestamp: Optional[str] = None
    version: Optional[str] = None


T = TypeVar("T")


@dataclass
class BaseResponse(Generic[T]):
    """Generic wrapper for all Hostinger API responses."""

    data: T = field(default_factory=list)  # type: ignore[type-var]
    pagination: Optional[Pagination] = None
    meta: Optional[Meta] = None
    raw_response: Optional[Dict[str, Any]] = None
    status_code: int = 200

    def __repr__(self) -> str:
        typename = getattr(self.data, "__class__", "?")
        if isinstance(self.data, list):
            typename = f"List[{len(self.data)}]"
        return (
            f"BaseResponse(data={typename}, status={self.status_code}, "
            f"pagination={self.pagination})"
        )


# ---------------------------------------------------------------------------
# RequestBuilder — Fluent API
# ---------------------------------------------------------------------------


class RequestBuilder:
    """Fluent request builder for type-safe HTTP construction."""

    def __init__(self, client: "HostingerClient") -> None:
        self._client = client
        self._method: str = "GET"
        self._path: str = ""
        self._query: Dict[str, Any] = {}
        self._body: Any = None
        self._headers: Dict[str, str] = {}
        self._expect_type: Optional[Type[T]] = None

    def method(self, verb: str) -> "RequestBuilder":
        self._method = verb.upper()
        return self

    def get(self, path: str) -> "RequestBuilder":
        self._method = "GET"
        self._path = path
        return self

    def post(self, path: str) -> "RequestBuilder":
        self._method = "POST"
        self._path = path
        return self

    def put(self, path: str) -> "RequestBuilder":
        self._method = "PUT"
        self._path = path
        return self

    def patch(self, path: str) -> "RequestBuilder":
        self._method = "PATCH"
        self._path = path
        return self

    def delete(self, path: str) -> "RequestBuilder":
        self._method = "DELETE"
        self._path = path
        return self

    def query(self, **kwargs: Any) -> "RequestBuilder":
        for k, v in kwargs.items():
            if v is not None:
                self._query[k] = v
        return self

    def body(self, data: Any) -> "RequestBuilder":
        self._body = data
        return self

    def header(self, key: str, value: str) -> "RequestBuilder":
        self._headers[key] = value
        return self

    def expect(self, cls: Type[T]) -> "RequestBuilder":
        self._expect_type = cls
        return self

    def build_url(self) -> str:
        url = f"{self._client.base_url.rstrip('/')}/{self._path.lstrip('/')}"
        if self._query:
            url += "?" + urllib.parse.urlencode(self._query, doseq=True)
        return url

    def execute(self) -> BaseResponse[Any]:
        return self._client._request(
            method=self._method,
            path=self._path,
            query=self._query,
            body=self._body,
            extra_headers=self._headers,
        )

    def __repr__(self) -> str:
        return (
            f"RequestBuilder(method={self._method}, path={self._path}, "
            f"query={self._query})"
        )


# ---------------------------------------------------------------------------
# HostingerClient — Base HTTP Client
# ---------------------------------------------------------------------------


class HostingerClient:
    """Base HTTP client for Hostinger API.

    Features:
    - Bearer token authentication
    - Automatic rate-limit retry with exponential backoff + jitter
    - Auto-pagination for list endpoints
    - urllib default transport, httpx optional
    - JSON request/response handling
    """

    DEFAULT_BASE_URL = "https://developers.hostinger.com"
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 5
    BACKOFF_BASE = 2.0

    def __init__(
        self,
        api_token: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        use_httpx: bool = False,
    ) -> None:
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._use_httpx = use_httpx and _try_httpx
        self._httpx_client: Optional[Any] = None

        if self._use_httpx:
            self._httpx_client = _httpx.Client(
                base_url=self.base_url,
                timeout=_httpx.Timeout(timeout),
                headers=self._default_headers(),
            )

    def _default_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "HostingerNativeSDK/1.0 (Python; MAGNATRIX-OS)",
        }

    def _should_retry(self, status: int, method: str) -> bool:
        """Determine if request should be retried."""
        if status in (429, 500, 502, 503, 504):
            return True
        if status == 408:
            return True
        # Don't retry mutations on 409/422
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            return status >= 500
        return False

    def _jitter_delay(self, attempt: int, retry_after: Optional[int] = None) -> float:
        """Calculate retry delay with exponential backoff + jitter."""
        if retry_after:
            base = retry_after
        else:
            base = self.BACKOFF_BASE ** attempt
        jitter = random.uniform(0, 1)
        return min(base + jitter, 60.0)

    def _map_exception(self, status: int, body: str, request_info: Dict[str, Any]) -> HostingerError:
        """Map HTTP status to typed exception."""
        try:
            parsed = json.loads(body) if body else {}
            message = parsed.get("message", parsed.get("error", "Unknown error"))
            errors = parsed.get("errors")
        except Exception:
            message = body or "Unknown error"
            parsed = {}
            errors = None

        if status == 401:
            return HostingerAuthError(message, status, body, request_info)
        if status == 403:
            return HostingerPermissionError(message, status, body, request_info)
        if status == 404:
            return HostingerNotFoundError(message, status, body, request_info)
        if status == 409:
            return HostingerConflictError(message, status, body, request_info)
        if status == 422:
            return HostingerValidationError(
                message, status_code=status, errors=errors,
                response_body=body, request_info=request_info
            )
        if status == 429:
            retry_after = parsed.get("retry_after") or parsed.get("retryAfter")
            return HostingerRateLimitError(
                message, status_code=status, retry_after=retry_after,
                response_body=body, request_info=request_info
            )
        if status >= 500:
            return HostingerServerError(message, status, body, request_info)
        return HostingerError(message, status, body, request_info)

    def _request_urllib(
        self,
        method: str,
        url: str,
        body: Optional[bytes],
        headers: Dict[str, str],
    ) -> "BaseResponse[Any]":
        """Execute request using urllib (pure Python fallback)."""
        req = urllib.request.Request(url, data=body, method=method)
        for k, v in headers.items():
            req.add_header(k, v)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
                return BaseResponse(
                    data=data,
                    status_code=resp.status,
                    raw_response=data,
                )
        except urllib.error.HTTPError as e:
            body_str = e.read().decode("utf-8") if e.fp else ""
            request_info = {"url": url, "method": method}
            exc = self._map_exception(e.code, body_str, request_info)
            raise exc from e
        except urllib.error.URLError as e:
            raise HostingerError(
                f"Request failed: {e.reason}", request_info={"url": url, "method": method}
            ) from e

    def _request_httpx(
        self,
        method: str,
        url: str,
        body: Optional[bytes],
        headers: Dict[str, str],
    ) -> "BaseResponse[Any]":
        """Execute request using httpx (if available)."""
        try:
            resp = self._httpx_client.request(
                method=method,
                url=url,
                content=body,
                headers=headers,
            )
            data = resp.json() if resp.text else {}
            if resp.status_code >= 400:
                request_info = {"url": url, "method": method}
                exc = self._map_exception(resp.status_code, resp.text, request_info)
                raise exc
            return BaseResponse(
                data=data,
                status_code=resp.status_code,
                raw_response=data,
            )
        except _httpx.HTTPStatusError as e:
            request_info = {"url": url, "method": method}
            body_str = e.response.text if hasattr(e.response, "text") else str(e)
            exc = self._map_exception(e.response.status_code, body_str, request_info)
            raise exc from e
        except _httpx.RequestError as e:
            raise HostingerError(
                f"Request failed: {e}", request_info={"url": url, "method": method}
            ) from e

    def _request(
        self,
        method: str,
        path: str,
        query: Optional[Dict[str, Any]] = None,
        body: Optional[Any] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> "BaseResponse[Any]":
        """Execute request with retry logic."""
        query = query or {}
        extra_headers = extra_headers or {}

        # Build full URL
        url = f"{self.base_url}/{path.lstrip('/')}"
        if query:
            url += "?" + urllib.parse.urlencode(query, doseq=True)

        headers = {**self._default_headers(), **extra_headers}
        body_bytes = _serialize_body(body)
        if body_bytes:
            headers["Content-Length"] = str(len(body_bytes))

        last_error: Optional[HostingerError] = None

        for attempt in range(self.max_retries + 1):
            try:
                if self._use_httpx and self._httpx_client:
                    return self._request_httpx(method, url, body_bytes, headers)
                return self._request_urllib(method, url, body_bytes, headers)
            except (
                HostingerRateLimitError,
                HostingerServerError,
                HostingerError,
            ) as e:
                last_error = e
                if not self._should_retry(e.status_code or 0, method):
                    raise
                if attempt >= self.max_retries:
                    break
                retry_after = getattr(e, "retry_after", None)
                delay = self._jitter_delay(attempt, retry_after)
                time.sleep(delay)

        if last_error:
            raise last_error
        raise HostingerError("Max retries exceeded", request_info={"url": url, "method": method})

    def request(self) -> RequestBuilder:
        """Start a fluent request."""
        return RequestBuilder(self)

    def paginate(
        self,
        method: str,
        path: str,
        query: Optional[Dict[str, Any]] = None,
        item_key: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Auto-iterate through paginated results.

        Args:
            method: HTTP method
            path: API path
            query: Initial query params
            item_key: Key containing list items (e.g., 'data', 'items')

        Returns:
            Flattened list of all items across pages.
        """
        query = dict(query) if query else {}
        all_items: List[Dict[str, Any]] = []
        page = query.get("page", 1)
        per_page = query.get("per_page", 25)

        while True:
            query["page"] = page
            query["per_page"] = per_page
            resp = self._request(method, path, query)

            data = resp.data
            if not isinstance(data, dict):
                if isinstance(data, list):
                    return data
                return []

            items = data.get(item_key or "data", [])
            if isinstance(items, list):
                all_items.extend(items)
            else:
                items = data.get("items", [])
                if isinstance(items, list):
                    all_items.extend(items)

            # Pagination detection
            pagination = data.get("pagination", {})
            total_pages = pagination.get("total_pages") or pagination.get("totalPages")
            current = pagination.get("current_page") or pagination.get("currentPage") or page
            next_url = pagination.get("next_page_url") or pagination.get("nextPageUrl")

            if next_url is None and total_pages is not None:
                if page >= total_pages:
                    break
            elif not items:
                break

            page += 1
            if page > 1000:  # Safety break
                break

        return all_items

    def __repr__(self) -> str:
        transport = "httpx" if self._use_httpx else "urllib"
        return (
            f"HostingerClient(base_url={self.base_url!r}, "
            f"transport={transport}, max_retries={self.max_retries})"
        )


# ---------------------------------------------------------------------------
# Dataclasses / Schemas — Billing
# ---------------------------------------------------------------------------


@dataclass
class CatalogItem:
    """Product catalog item."""

    id: int = 0
    name: str = ""
    description: Optional[str] = None
    price: float = 0.0
    currency: str = "USD"
    period_months: int = 12
    category: str = ""
    features: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"CatalogItem(id={self.id}, name={self.name!r}, price={self.price} {self.currency})"


@dataclass
class PaymentMethod:
    """Stored payment method."""

    id: int = 0
    type: str = ""  # card, paypal, etc.
    last_four: Optional[str] = None
    brand: Optional[str] = None
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None
    is_default: bool = False

    def __repr__(self) -> str:
        return f"PaymentMethod(id={self.id}, type={self.type!r}, last4={self.last_four})"


@dataclass
class Subscription:
    """Active subscription."""

    id: int = 0
    catalog_item_id: int = 0
    status: str = ""  # active, suspended, cancelled
    start_date: Optional[str] = None
    next_billing_date: Optional[str] = None
    auto_renewal: bool = True
    amount: float = 0.0
    currency: str = "USD"
    domain: Optional[str] = None  # if applicable

    def __repr__(self) -> str:
        return (
            f"Subscription(id={self.id}, status={self.status!r}, "
            f"auto_renewal={self.auto_renewal})"
        )


# ---------------------------------------------------------------------------
# Dataclasses / Schemas — DNS
# ---------------------------------------------------------------------------


@dataclass
class DNSRecord:
    """DNS zone record."""

    id: int = 0
    name: str = ""
    type: str = ""  # A, AAAA, CNAME, MX, TXT, NS, SRV, SOA
    value: str = ""
    ttl: int = 3600
    priority: Optional[int] = None  # MX / SRV
    flags: Optional[int] = None  # CAA
    tag: Optional[str] = None  # CAA

    def __repr__(self) -> str:
        return f"DNSRecord(id={self.id}, name={self.name!r}, type={self.type!r})"


@dataclass
class DNSZone:
    """DNS zone with records."""

    domain: str = ""
    records: List[DNSRecord] = field(default_factory=list)
    soa_serial: Optional[int] = None
    nameservers: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"DNSZone(domain={self.domain!r}, records={len(self.records)})"


@dataclass
class DNSSnapshot:
    """DNS zone snapshot backup."""

    id: int = 0
    created_at: Optional[str] = None
    record_count: int = 0
    comment: Optional[str] = None

    def __repr__(self) -> str:
        return f"DNSSnapshot(id={self.id}, records={self.record_count})"


# ---------------------------------------------------------------------------
# Dataclasses / Schemas — Domains
# ---------------------------------------------------------------------------


@dataclass
class DomainInfo:
    """Domain registration info."""

    domain: str = ""
    status: str = ""  # active, pending, expired, suspended
    registrar: Optional[str] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    auto_renew: bool = False
    privacy_protection: bool = False
    nameservers: List[str] = field(default_factory=list)
    is_hostinger_dns: bool = False

    def __repr__(self) -> str:
        return f"DomainInfo(domain={self.domain!r}, status={self.status!r})"


@dataclass
class DomainAvailability:
    """Domain availability check result."""

    domain: str = ""
    available: bool = False
    price: Optional[float] = None
    currency: Optional[str] = None
    premium: bool = False
    suggestions: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"DomainAvailability(domain={self.domain!r}, "
            f"available={self.available}, price={self.price})"
        )


@dataclass
class WhoisInfo:
    """WHOIS lookup result."""

    domain: str = ""
    registrar: Optional[str] = None
    created_date: Optional[str] = None
    updated_date: Optional[str] = None
    expiration_date: Optional[str] = None
    name_servers: List[str] = field(default_factory=list)
    status: List[str] = field(default_factory=list)
    dnssec: Optional[str] = None
    raw: Optional[str] = None

    def __repr__(self) -> str:
        return f"WhoisInfo(domain={self.domain!r}, expiry={self.expiration_date})"


@dataclass
class DomainForward:
    """Domain forwarding configuration."""

    target_url: str = ""
    redirect_type: str = "301"  # 301, 302, masked
    include_path: bool = True

    def __repr__(self) -> str:
        return f"DomainForward(target={self.target_url!r}, type={self.redirect_type})"


# ---------------------------------------------------------------------------
# Dataclasses / Schemas — Hosting
# ---------------------------------------------------------------------------


@dataclass
class Datacenter:
    """Hosting datacenter location."""

    id: int = 0
    name: str = ""
    country: str = ""
    city: str = ""
    iso_code: Optional[str] = None

    def __repr__(self) -> str:
        return f"Datacenter(id={self.id}, name={self.name!r}, location={self.city}, {self.country})"


@dataclass
class Website:
    """Hosted website."""

    id: int = 0
    domain: str = ""
    plan: str = ""
    status: str = ""  # active, suspended, maintenance
    created_at: Optional[str] = None
    disk_usage_mb: int = 0
    bandwidth_usage_mb: int = 0
    ssl_active: bool = False
    php_version: Optional[str] = None
    auto_backup: bool = False

    def __repr__(self) -> str:
        return f"Website(id={self.id}, domain={self.domain!r}, plan={self.plan!r})"


@dataclass
class HostingOrderRequest:
    """Request body for creating a hosting order."""

    plan_id: int = 0
    domain: Optional[str] = None
    datacenter_id: Optional[int] = None
    period_months: int = 12
    payment_method_id: Optional[int] = None
    coupon_code: Optional[str] = None

    def __repr__(self) -> str:
        return f"HostingOrderRequest(plan={self.plan_id}, domain={self.domain!r})"


@dataclass
class HostingOrder:
    """Created hosting order."""

    id: int = 0
    status: str = ""  # pending, active, failed
    amount: float = 0.0
    currency: str = "USD"
    created_at: Optional[str] = None
    activation_url: Optional[str] = None

    def __repr__(self) -> str:
        return f"HostingOrder(id={self.id}, status={self.status!r}, amount={self.amount})"


# ---------------------------------------------------------------------------
# Dataclasses / Schemas — VPS
# ---------------------------------------------------------------------------


@dataclass
class VPSPlan:
    """VPS plan specification."""

    id: int = 0
    name: str = ""
    cpu_cores: int = 0
    ram_mb: int = 0
    disk_gb: int = 0
    bandwidth_tb: float = 0.0
    price_monthly: float = 0.0
    currency: str = "USD"
    datacenter_id: int = 0
    os_templates: List[int] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"VPSPlan(id={self.id}, name={self.name!r}, "
            f"cpu={self.cpu_cores}, ram={self.ram_mb}MB)"
        )


@dataclass
class VM:
    """Virtual machine instance."""

    id: int = 0
    name: str = ""
    hostname: Optional[str] = None
    status: str = ""  # running, stopped, provisioning, error
    plan_id: int = 0
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None
    datacenter_id: int = 0
    os_template_id: int = 0
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"VM(id={self.id}, name={self.name!r}, status={self.status!r}, ip={self.ipv4})"


@dataclass
class VPSAction:
    """VPS action (start/stop/reboot/etc.) status."""

    id: int = 0
    type: str = ""
    status: str = ""  # pending, in_progress, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

    def __repr__(self) -> str:
        return f"VPSAction(id={self.id}, type={self.type!r}, status={self.status!r})"


@dataclass
class Backup:
    """VPS backup."""

    id: int = 0
    vm_id: int = 0
    created_at: Optional[str] = None
    size_bytes: int = 0
    status: str = ""  # available, pending, restoring
    type: str = "manual"  # manual, auto

    def __repr__(self) -> str:
        return f"Backup(id={self.id}, vm={self.vm_id}, size={self.size_bytes}, status={self.status!r})"


@dataclass
class Snapshot:
    """VPS snapshot."""

    id: int = 0
    vm_id: int = 0
    name: Optional[str] = None
    created_at: Optional[str] = None
    size_bytes: int = 0
    status: str = ""  # active, pending, deleted

    def __repr__(self) -> str:
        return f"Snapshot(id={self.id}, vm={self.vm_id}, name={self.name!r})"


@dataclass
class FirewallRule:
    """VPS firewall rule."""

    id: int = 0
    direction: str = "inbound"  # inbound, outbound
    action: str = "accept"  # accept, drop, reject
    protocol: str = "tcp"  # tcp, udp, icmp, any
    port_range: Optional[str] = None  # "80", "22-443"
    source: Optional[str] = None  # CIDR or "any"
    destination: Optional[str] = None
    comment: Optional[str] = None

    def __repr__(self) -> str:
        return f"FirewallRule(id={self.id}, {self.direction}/{self.protocol}, action={self.action})"


@dataclass
class FirewallConfig:
    """VPS firewall configuration."""

    vm_id: int = 0
    enabled: bool = True
    default_action: str = "drop"  # drop, accept
    rules: List[FirewallRule] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"FirewallConfig(vm={self.vm_id}, rules={len(self.rules)}, default={self.default_action})"


@dataclass
class SSHKey:
    """SSH public key."""

    id: int = 0
    name: str = ""
    fingerprint: Optional[str] = None
    public_key: str = ""
    created_at: Optional[str] = None

    def __repr__(self) -> str:
        return f"SSHKey(id={self.id}, name={self.name!r}, fp={self.fingerprint})"


@dataclass
class OSTemplate:
    """Operating system template."""

    id: int = 0
    name: str = ""
    os_family: str = ""  # linux, windows
    distro: str = ""  # ubuntu, debian, centos, almalinux, windows
    version: str = ""
    architecture: str = "x86_64"
    min_disk_gb: int = 0
    min_ram_mb: int = 0

    def __repr__(self) -> str:
        return f"OSTemplate(id={self.id}, {self.distro} {self.version} {self.architecture})"


@dataclass
class PTRRecord:
    """Reverse DNS PTR record."""

    ip: str = ""
    ptr_value: str = ""

    def __repr__(self) -> str:
        return f"PTRRecord(ip={self.ip!r}, ptr={self.ptr_value!r})"


@dataclass
class MalwareScanResult:
    """Malware scan result."""

    scan_id: str = ""
    status: str = ""  # clean, infected, scanning
    threats_found: int = 0
    scanned_files: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    details: List[Dict[str, Any]] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"MalwareScanResult(id={self.scan_id!r}, "
            f"threats={self.threats_found}, status={self.status!r})"
        )


@dataclass
class DockerContainer:
    """Docker container managed on VPS."""

    id: str = ""
    name: str = ""
    image: str = ""
    status: str = ""  # running, exited, paused
    ports: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None

    def __repr__(self) -> str:
        return f"DockerContainer(id={self.id!r}, name={self.name!r}, image={self.image!r})"


@dataclass
class PostInstallScript:
    """Post-installation script."""

    id: int = 0
    name: str = ""
    script: str = ""
    interpreter: str = "bash"  # bash, python, sh
    created_at: Optional[str] = None

    def __repr__(self) -> str:
        return f"PostInstallScript(id={self.id}, name={self.name!r})"


@dataclass
class RecoveryConsole:
    """VPS recovery console access."""

    url: str = ""
    token: Optional[str] = None
    expires_at: Optional[str] = None
    type: str = "vnc"  # vnc, serial

    def __repr__(self) -> str:
        url_preview = self.url[:30] if self.url else ""
        return f"RecoveryConsole(type={self.type!r}, url={url_preview!r}...)"


# ---------------------------------------------------------------------------
# Dataclasses / Schemas — Reach (CRM)
# ---------------------------------------------------------------------------


@dataclass
class Contact:
    """Reach contact."""

    id: int = 0
    email: str = ""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __repr__(self) -> str:
        return f"Contact(id={self.id}, email={self.email!r}, name={self.first_name} {self.last_name})"


@dataclass
class Profile:
    """Reach profile/identity."""

    id: int = 0
    name: str = ""
    email: str = ""
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    preferences: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Profile(id={self.id}, name={self.name!r}, email={self.email!r})"


@dataclass
class Segment:
    """Reach audience segment."""

    id: int = 0
    name: str = ""
    description: Optional[str] = None
    criteria: Dict[str, Any] = field(default_factory=dict)
    contact_count: int = 0
    created_at: Optional[str] = None

    def __repr__(self) -> str:
        return f"Segment(id={self.id}, name={self.name!r}, contacts={self.contact_count})"


# ---------------------------------------------------------------------------
# BillingAPI
# ---------------------------------------------------------------------------


class BillingAPI:
    """Billing service: catalog, payment methods, subscriptions, auto-renewal."""

    def __init__(self, client: HostingerClient) -> None:
        self._client = client

    def list_catalog(self, category: Optional[str] = None) -> BaseResponse[List[CatalogItem]]:
        """List available product catalog items."""
        query: Dict[str, Any] = {}
        if category:
            query["category"] = category
        resp = self._client._request("GET", "/api/billing/catalog", query)
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(
            data=[CatalogItem(**_map_camel_dict(i)) for i in items],
            status_code=resp.status_code,
        )

    def get_catalog_item(self, item_id: int) -> BaseResponse[CatalogItem]:
        """Get a single catalog item by ID."""
        resp = self._client._request("GET", f"/api/billing/catalog/{item_id}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=CatalogItem(**_map_camel_dict(data)), status_code=resp.status_code)

    def list_payment_methods(self) -> BaseResponse[List[PaymentMethod]]:
        """List stored payment methods."""
        resp = self._client._request("GET", "/api/billing/payment-methods")
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(
            data=[PaymentMethod(**_map_camel_dict(i)) for i in items],
            status_code=resp.status_code,
        )

    def get_payment_method(self, method_id: int) -> BaseResponse[PaymentMethod]:
        """Get a single payment method."""
        resp = self._client._request("GET", f"/api/billing/payment-methods/{method_id}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=PaymentMethod(**_map_camel_dict(data)), status_code=resp.status_code)

    def delete_payment_method(self, method_id: int) -> BaseResponse[Dict[str, Any]]:
        """Delete a payment method."""
        return self._client._request("DELETE", f"/api/billing/payment-methods/{method_id}")

    def set_default_payment_method(self, method_id: int) -> BaseResponse[PaymentMethod]:
        """Set a payment method as default."""
        resp = self._client._request("PATCH", f"/api/billing/payment-methods/{method_id}/default")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=PaymentMethod(**_map_camel_dict(data)), status_code=resp.status_code)

    def list_subscriptions(
        self, status: Optional[str] = None, page: int = 1, per_page: int = 25
    ) -> BaseResponse[List[Subscription]]:
        """List subscriptions with optional status filter."""
        query: Dict[str, Any] = {"page": page, "per_page": per_page}
        if status:
            query["status"] = status
        resp = self._client._request("GET", "/api/billing/subscriptions", query)
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(
            data=[Subscription(**_map_camel_dict(i)) for i in items],
            status_code=resp.status_code,
        )

    def get_subscription(self, subscription_id: int) -> BaseResponse[Subscription]:
        """Get subscription details."""
        resp = self._client._request("GET", f"/api/billing/subscriptions/{subscription_id}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Subscription(**_map_camel_dict(data)), status_code=resp.status_code)

    def cancel_subscription(self, subscription_id: int) -> BaseResponse[Dict[str, Any]]:
        """Cancel a subscription."""
        return self._client._request("DELETE", f"/api/billing/subscriptions/{subscription_id}")

    def upgrade_subscription(
        self, subscription_id: int, new_catalog_item_id: int
    ) -> BaseResponse[Subscription]:
        """Upgrade subscription to a new plan."""
        resp = self._client._request(
            "POST", f"/api/billing/subscriptions/{subscription_id}/upgrade",
            body={"catalog_item_id": new_catalog_item_id}
        )
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Subscription(**_map_camel_dict(data)), status_code=resp.status_code)

    def downgrade_subscription(
        self, subscription_id: int, new_catalog_item_id: int
    ) -> BaseResponse[Subscription]:
        """Downgrade subscription to a new plan."""
        resp = self._client._request(
            "POST", f"/api/billing/subscriptions/{subscription_id}/downgrade",
            body={"catalog_item_id": new_catalog_item_id}
        )
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Subscription(**_map_camel_dict(data)), status_code=resp.status_code)

    def disable_auto_renewal(self, subscription_id: int) -> BaseResponse[Subscription]:
        """Disable auto-renewal for a subscription."""
        resp = self._client._request(
            "POST", f"/api/billing/subscriptions/{subscription_id}/auto-renewal/disable"
        )
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Subscription(**_map_camel_dict(data)), status_code=resp.status_code)

    def enable_auto_renewal(self, subscription_id: int) -> BaseResponse[Subscription]:
        """Enable auto-renewal for a subscription."""
        resp = self._client._request(
            "POST", f"/api/billing/subscriptions/{subscription_id}/auto-renewal/enable"
        )
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Subscription(**_map_camel_dict(data)), status_code=resp.status_code)

    def get_invoice(self, invoice_id: int) -> BaseResponse[Dict[str, Any]]:
        """Get invoice details."""
        return self._client._request("GET", f"/api/billing/invoices/{invoice_id}")

    def list_invoices(self, page: int = 1, per_page: int = 25) -> BaseResponse[List[Dict[str, Any]]]:
        """List invoices."""
        return self._client._request("GET", "/api/billing/invoices", {"page": page, "per_page": per_page})

    def __repr__(self) -> str:
        return "BillingAPI()"


# ---------------------------------------------------------------------------
# DNSAPI
# ---------------------------------------------------------------------------


class DNSAPI:
    """DNS service: zone management, snapshots, validation, reset."""

    def __init__(self, client: HostingerClient) -> None:
        self._client = client

    def get_zone(self, domain: str) -> BaseResponse[DNSZone]:
        """Get DNS zone for a domain."""
        resp = self._client._request("GET", f"/api/dns/zones/{domain}")
        data = resp.data if isinstance(resp.data, dict) else {}
        records = data.get("records", data.get("data", []))
        if isinstance(records, list):
            record_objs = [DNSRecord(**_map_camel_dict(r)) for r in records]
        else:
            record_objs = []
        zone = DNSZone(
            domain=domain,
            records=record_objs,
            soa_serial=data.get("soa_serial") or data.get("soaSerial"),
            nameservers=data.get("nameservers", []),
        )
        return BaseResponse(data=zone, status_code=resp.status_code)

    def update_zone(self, domain: str, records: List[DNSRecord]) -> BaseResponse[DNSZone]:
        """Update DNS zone records."""
        payload = {"records": [asdict(r) for r in records]}
        resp = self._client._request("PUT", f"/api/dns/zones/{domain}", body=payload)
        data = resp.data if isinstance(resp.data, dict) else {}
        records_out = data.get("records", data.get("data", []))
        if isinstance(records_out, list):
            record_objs = [DNSRecord(**_map_camel_dict(r)) for r in records_out]
        else:
            record_objs = []
        zone = DNSZone(
            domain=domain,
            records=record_objs,
            soa_serial=data.get("soa_serial") or data.get("soaSerial"),
            nameservers=data.get("nameservers", []),
        )
        return BaseResponse(data=zone, status_code=resp.status_code)

    def create_record(self, domain: str, record: DNSRecord) -> BaseResponse[DNSRecord]:
        """Create a single DNS record."""
        resp = self._client._request("POST", f"/api/dns/zones/{domain}/records", body=asdict(record))
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=DNSRecord(**_map_camel_dict(data)), status_code=resp.status_code)

    def update_record(self, domain: str, record_id: int, record: DNSRecord) -> BaseResponse[DNSRecord]:
        """Update a single DNS record by ID."""
        resp = self._client._request("PUT", f"/api/dns/zones/{domain}/records/{record_id}", body=asdict(record))
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=DNSRecord(**_map_camel_dict(data)), status_code=resp.status_code)

    def delete_record(self, domain: str, record_id: int) -> BaseResponse[Dict[str, Any]]:
        """Delete a DNS record."""
        return self._client._request("DELETE", f"/api/dns/zones/{domain}/records/{record_id}")

    def list_snapshots(self, domain: str) -> BaseResponse[List[DNSSnapshot]]:
        """List DNS zone snapshots."""
        resp = self._client._request("GET", f"/api/dns/zones/{domain}/snapshots")
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[DNSSnapshot(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def create_snapshot(self, domain: str, comment: Optional[str] = None) -> BaseResponse[DNSSnapshot]:
        """Create a DNS zone snapshot."""
        body: Dict[str, Any] = {}
        if comment:
            body["comment"] = comment
        resp = self._client._request("POST", f"/api/dns/zones/{domain}/snapshots", body=body or None)
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=DNSSnapshot(**_map_camel_dict(data)), status_code=resp.status_code)

    def restore_snapshot(self, domain: str, snapshot_id: int) -> BaseResponse[DNSZone]:
        """Restore DNS zone from a snapshot."""
        resp = self._client._request("POST", f"/api/dns/zones/{domain}/snapshots/{snapshot_id}/restore")
        data = resp.data if isinstance(resp.data, dict) else {}
        records = data.get("records", data.get("data", []))
        if isinstance(records, list):
            record_objs = [DNSRecord(**_map_camel_dict(r)) for r in records]
        else:
            record_objs = []
        zone = DNSZone(domain=domain, records=record_objs, soa_serial=data.get("soa_serial") or data.get("soaSerial"), nameservers=data.get("nameservers", []))
        return BaseResponse(data=zone, status_code=resp.status_code)

    def delete_snapshot(self, domain: str, snapshot_id: int) -> BaseResponse[Dict[str, Any]]:
        """Delete a DNS snapshot."""
        return self._client._request("DELETE", f"/api/dns/zones/{domain}/snapshots/{snapshot_id}")

    def reset_zone(self, domain: str) -> BaseResponse[DNSZone]:
        """Reset DNS zone to default."""
        resp = self._client._request("POST", f"/api/dns/zones/{domain}/reset")
        data = resp.data if isinstance(resp.data, dict) else {}
        records = data.get("records", data.get("data", []))
        if isinstance(records, list):
            record_objs = [DNSRecord(**_map_camel_dict(r)) for r in records]
        else:
            record_objs = []
        zone = DNSZone(domain=domain, records=record_objs, soa_serial=data.get("soa_serial") or data.get("soaSerial"), nameservers=data.get("nameservers", []))
        return BaseResponse(data=zone, status_code=resp.status_code)

    def validate_zone(self, domain: str) -> BaseResponse[Dict[str, Any]]:
        """Validate DNS zone configuration."""
        return self._client._request("POST", f"/api/dns/zones/{domain}/validate")

    def import_zone(self, domain: str, bind_format: str) -> BaseResponse[DNSZone]:
        """Import DNS zone from BIND format."""
        resp = self._client._request("POST", f"/api/dns/zones/{domain}/import", body={"bind_format": bind_format})
        data = resp.data if isinstance(resp.data, dict) else {}
        records = data.get("records", data.get("data", []))
        if isinstance(records, list):
            record_objs = [DNSRecord(**_map_camel_dict(r)) for r in records]
        else:
            record_objs = []
        zone = DNSZone(domain=domain, records=record_objs, soa_serial=data.get("soa_serial") or data.get("soaSerial"), nameservers=data.get("nameservers", []))
        return BaseResponse(data=zone, status_code=resp.status_code)

    def export_zone(self, domain: str) -> BaseResponse[str]:
        """Export DNS zone to BIND format."""
        resp = self._client._request("GET", f"/api/dns/zones/{domain}/export")
        return BaseResponse(data=resp.data if isinstance(resp.data, str) else "", status_code=resp.status_code)

    def __repr__(self) -> str:
        return "DNSAPI()"


# ---------------------------------------------------------------------------
# DomainsAPI
# ---------------------------------------------------------------------------


class DomainsAPI:
    """Domain service: availability, forwarding, portfolio, WHOIS, verification."""

    def __init__(self, client: HostingerClient) -> None:
        self._client = client

    def check_availability(self, domain: str) -> BaseResponse[DomainAvailability]:
        """Check if a domain is available for registration."""
        resp = self._client._request("GET", "/api/domains/availability", {"domain": domain})
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=DomainAvailability(**_map_camel_dict(data)), status_code=resp.status_code)

    def check_availability_bulk(self, domains: List[str]) -> BaseResponse[List[DomainAvailability]]:
        """Bulk check domain availability."""
        resp = self._client._request("POST", "/api/domains/availability/bulk", body={"domains": domains})
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[DomainAvailability(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def get_whois(self, domain: str) -> BaseResponse[WhoisInfo]:
        """Perform WHOIS lookup for a domain."""
        resp = self._client._request("GET", f"/api/domains/{domain}/whois")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=WhoisInfo(**_map_camel_dict(data)), status_code=resp.status_code)

    def set_forwarding(self, domain: str, forward: DomainForward) -> BaseResponse[DomainForward]:
        """Set domain forwarding."""
        resp = self._client._request("PUT", f"/api/domains/{domain}/forwarding", body=asdict(forward))
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=DomainForward(**_map_camel_dict(data)), status_code=resp.status_code)

    def delete_forwarding(self, domain: str) -> BaseResponse[Dict[str, Any]]:
        """Remove domain forwarding."""
        return self._client._request("DELETE", f"/api/domains/{domain}/forwarding")

    def list_portfolio(self, page: int = 1, per_page: int = 25) -> BaseResponse[List[DomainInfo]]:
        """List domains in portfolio."""
        resp = self._client._request("GET", "/api/domains/portfolio", {"page": page, "per_page": per_page})
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[DomainInfo(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def get_domain(self, domain: str) -> BaseResponse[DomainInfo]:
        """Get domain details."""
        resp = self._client._request("GET", f"/api/domains/{domain}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=DomainInfo(**_map_camel_dict(data)), status_code=resp.status_code)

    def verify_domain_access(self, domain: str) -> BaseResponse[Dict[str, Any]]:
        """Verify ownership/access to a domain."""
        return self._client._request("POST", f"/api/domains/{domain}/verify")

    def update_nameservers(self, domain: str, nameservers: List[str]) -> BaseResponse[DomainInfo]:
        """Update domain nameservers."""
        resp = self._client._request("PUT", f"/api/domains/{domain}/nameservers", body={"nameservers": nameservers})
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=DomainInfo(**_map_camel_dict(data)), status_code=resp.status_code)

    def enable_privacy_protection(self, domain: str) -> BaseResponse[DomainInfo]:
        """Enable WHOIS privacy protection."""
        resp = self._client._request("POST", f"/api/domains/{domain}/privacy/enable")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=DomainInfo(**_map_camel_dict(data)), status_code=resp.status_code)

    def disable_privacy_protection(self, domain: str) -> BaseResponse[DomainInfo]:
        """Disable WHOIS privacy protection."""
        resp = self._client._request("POST", f"/api/domains/{domain}/privacy/disable")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=DomainInfo(**_map_camel_dict(data)), status_code=resp.status_code)

    def get_epp_code(self, domain: str) -> BaseResponse[str]:
        """Get EPP/transfer code for domain."""
        resp = self._client._request("GET", f"/api/domains/{domain}/epp-code")
        return BaseResponse(data=resp.data if isinstance(resp.data, str) else "", status_code=resp.status_code)

    def lock_domain(self, domain: str) -> BaseResponse[DomainInfo]:
        """Lock domain to prevent transfer."""
        resp = self._client._request("POST", f"/api/domains/{domain}/lock")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=DomainInfo(**_map_camel_dict(data)), status_code=resp.status_code)

    def unlock_domain(self, domain: str) -> BaseResponse[DomainInfo]:
        """Unlock domain for transfer."""
        resp = self._client._request("POST", f"/api/domains/{domain}/unlock")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=DomainInfo(**_map_camel_dict(data)), status_code=resp.status_code)

    def list_suggestions(self, keyword: str, tlds: Optional[List[str]] = None) -> BaseResponse[List[str]]:
        """Get domain name suggestions."""
        query: Dict[str, Any] = {"keyword": keyword}
        if tlds:
            query["tlds"] = ",".join(tlds)
        resp = self._client._request("GET", "/api/domains/suggestions", query)
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[str(i) for i in items], status_code=resp.status_code)

    def __repr__(self) -> str:
        return "DomainsAPI()"


# ---------------------------------------------------------------------------
# HostingAPI
# ---------------------------------------------------------------------------


class HostingAPI:
    """Hosting service: datacenters, websites, orders."""

    def __init__(self, client: HostingerClient) -> None:
        self._client = client

    def list_datacenters(self) -> BaseResponse[List[Datacenter]]:
        """List available datacenter locations."""
        resp = self._client._request("GET", "/api/hosting/datacenters")
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[Datacenter(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def list_websites(self, status: Optional[str] = None, page: int = 1, per_page: int = 25) -> BaseResponse[List[Website]]:
        """List hosted websites."""
        query: Dict[str, Any] = {"page": page, "per_page": per_page}
        if status:
            query["status"] = status
        resp = self._client._request("GET", "/api/hosting/websites", query)
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[Website(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def get_website(self, website_id: int) -> BaseResponse[Website]:
        """Get website details."""
        resp = self._client._request("GET", f"/api/hosting/websites/{website_id}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Website(**_map_camel_dict(data)), status_code=resp.status_code)

    def create_order(self, order: HostingOrderRequest) -> BaseResponse[HostingOrder]:
        """Create a new hosting order."""
        resp = self._client._request("POST", "/api/hosting/orders", body=asdict(order))
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=HostingOrder(**_map_camel_dict(data)), status_code=resp.status_code)

    def get_order(self, order_id: int) -> BaseResponse[HostingOrder]:
        """Get hosting order details."""
        resp = self._client._request("GET", f"/api/hosting/orders/{order_id}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=HostingOrder(**_map_camel_dict(data)), status_code=resp.status_code)

    def cancel_order(self, order_id: int) -> BaseResponse[Dict[str, Any]]:
        """Cancel a pending hosting order."""
        return self._client._request("DELETE", f"/api/hosting/orders/{order_id}")

    def list_hosting_domains(self, website_id: int) -> BaseResponse[List[str]]:
        """List domains attached to a hosting account."""
        resp = self._client._request("GET", f"/api/hosting/websites/{website_id}/domains")
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[str(i) for i in items], status_code=resp.status_code)

    def add_domain_to_website(self, website_id: int, domain: str) -> BaseResponse[Dict[str, Any]]:
        """Add a domain to a hosting website."""
        return self._client._request("POST", f"/api/hosting/websites/{website_id}/domains", body={"domain": domain})

    def remove_domain_from_website(self, website_id: int, domain: str) -> BaseResponse[Dict[str, Any]]:
        """Remove a domain from a hosting website."""
        return self._client._request("DELETE", f"/api/hosting/websites/{website_id}/domains/{domain}")

    def change_php_version(self, website_id: int, version: str) -> BaseResponse[Website]:
        """Change PHP version for a website."""
        resp = self._client._request("PUT", f"/api/hosting/websites/{website_id}/php-version", body={"version": version})
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Website(**_map_camel_dict(data)), status_code=resp.status_code)

    def toggle_ssl(self, website_id: int, enabled: bool) -> BaseResponse[Website]:
        """Enable or disable SSL for a website."""
        endpoint = "enable" if enabled else "disable"
        resp = self._client._request("POST", f"/api/hosting/websites/{website_id}/ssl/{endpoint}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Website(**_map_camel_dict(data)), status_code=resp.status_code)

    def toggle_auto_backup(self, website_id: int, enabled: bool) -> BaseResponse[Website]:
        """Enable or disable auto-backup for a website."""
        endpoint = "enable" if enabled else "disable"
        resp = self._client._request("POST", f"/api/hosting/websites/{website_id}/auto-backup/{endpoint}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Website(**_map_camel_dict(data)), status_code=resp.status_code)

    def get_file_manager_url(self, website_id: int) -> BaseResponse[str]:
        """Get single-sign-on URL for file manager."""
        resp = self._client._request("GET", f"/api/hosting/websites/{website_id}/file-manager")
        return BaseResponse(data=resp.data if isinstance(resp.data, str) else "", status_code=resp.status_code)

    def get_stats(self, website_id: int) -> BaseResponse[Dict[str, Any]]:
        """Get website resource statistics."""
        return self._client._request("GET", f"/api/hosting/websites/{website_id}/stats")

    def __repr__(self) -> str:
        return "HostingAPI()"


# ---------------------------------------------------------------------------
# VPSAPI
# ---------------------------------------------------------------------------


class VPSAPI:
    """VPS service: VM CRUD, actions, backups, snapshots, firewall,
    malware scan, SSH keys, post-install scripts, PTR, recovery, Docker, OS templates.
    """

    def __init__(self, client: HostingerClient) -> None:
        self._client = client

    def list_plans(self, datacenter_id: Optional[int] = None) -> BaseResponse[List[VPSPlan]]:
        """List available VPS plans."""
        query: Dict[str, Any] = {}
        if datacenter_id:
            query["datacenter_id"] = datacenter_id
        resp = self._client._request("GET", "/api/vps/plans", query)
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[VPSPlan(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def list_vms(self, page: int = 1, per_page: int = 25) -> BaseResponse[List[VM]]:
        """List all virtual machines."""
        resp = self._client._request("GET", "/api/vps/vms", {"page": page, "per_page": per_page})
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[VM(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def get_vm(self, vm_id: int) -> BaseResponse[VM]:
        """Get VM details."""
        resp = self._client._request("GET", f"/api/vps/vms/{vm_id}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=VM(**_map_camel_dict(data)), status_code=resp.status_code)

    def create_vm(self, plan_id: int, os_template_id: int, datacenter_id: int, hostname: Optional[str] = None, ssh_key_ids: Optional[List[int]] = None, post_install_script_id: Optional[int] = None, labels: Optional[Dict[str, str]] = None) -> BaseResponse[VM]:
        """Create a new virtual machine."""
        body: Dict[str, Any] = {"plan_id": plan_id, "os_template_id": os_template_id, "datacenter_id": datacenter_id}
        if hostname:
            body["hostname"] = hostname
        if ssh_key_ids:
            body["ssh_key_ids"] = ssh_key_ids
        if post_install_script_id:
            body["post_install_script_id"] = post_install_script_id
        if labels:
            body["labels"] = labels
        resp = self._client._request("POST", "/api/vps/vms", body=body)
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=VM(**_map_camel_dict(data)), status_code=resp.status_code)

    def destroy_vm(self, vm_id: int) -> BaseResponse[Dict[str, Any]]:
        """Permanently destroy a VM."""
        return self._client._request("DELETE", f"/api/vps/vms/{vm_id}")

    def update_vm(self, vm_id: int, **kwargs: Any) -> BaseResponse[VM]:
        """Update VM properties."""
        resp = self._client._request("PATCH", f"/api/vps/vms/{vm_id}", body=kwargs)
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=VM(**_map_camel_dict(data)), status_code=resp.status_code)

    def resize_vm(self, vm_id: int, new_plan_id: int) -> BaseResponse[VM]:
        """Resize VM to a different plan."""
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/resize", body={"plan_id": new_plan_id})
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=VM(**_map_camel_dict(data)), status_code=resp.status_code)

    def start_vm(self, vm_id: int) -> BaseResponse[VPSAction]:
        """Start a stopped VM."""
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/actions/start")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=VPSAction(**_map_camel_dict(data)), status_code=resp.status_code)

    def stop_vm(self, vm_id: int) -> BaseResponse[VPSAction]:
        """Stop a running VM."""
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/actions/stop")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=VPSAction(**_map_camel_dict(data)), status_code=resp.status_code)

    def reboot_vm(self, vm_id: int) -> BaseResponse[VPSAction]:
        """Reboot a VM."""
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/actions/reboot")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=VPSAction(**_map_camel_dict(data)), status_code=resp.status_code)

    def shutdown_vm(self, vm_id: int) -> BaseResponse[VPSAction]:
        """Graceful shutdown of a VM."""
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/actions/shutdown")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=VPSAction(**_map_camel_dict(data)), status_code=resp.status_code)

    def get_vm_actions(self, vm_id: int, page: int = 1, per_page: int = 25) -> BaseResponse[List[VPSAction]]:
        """List VM action history."""
        resp = self._client._request("GET", f"/api/vps/vms/{vm_id}/actions", {"page": page, "per_page": per_page})
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[VPSAction(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def get_action(self, vm_id: int, action_id: int) -> BaseResponse[VPSAction]:
        """Get action details."""
        resp = self._client._request("GET", f"/api/vps/vms/{vm_id}/actions/{action_id}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=VPSAction(**_map_camel_dict(data)), status_code=resp.status_code)

    def list_backups(self, vm_id: int, page: int = 1, per_page: int = 25) -> BaseResponse[List[Backup]]:
        """List VM backups."""
        resp = self._client._request("GET", f"/api/vps/vms/{vm_id}/backups", {"page": page, "per_page": per_page})
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[Backup(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def create_backup(self, vm_id: int, name: Optional[str] = None) -> BaseResponse[Backup]:
        """Create a manual backup."""
        body: Dict[str, Any] = {}
        if name:
            body["name"] = name
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/backups", body=body or None)
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Backup(**_map_camel_dict(data)), status_code=resp.status_code)

    def restore_backup(self, vm_id: int, backup_id: int) -> BaseResponse[VPSAction]:
        """Restore VM from a backup."""
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/backups/{backup_id}/restore")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=VPSAction(**_map_camel_dict(data)), status_code=resp.status_code)

    def delete_backup(self, vm_id: int, backup_id: int) -> BaseResponse[Dict[str, Any]]:
        """Delete a backup."""
        return self._client._request("DELETE", f"/api/vps/vms/{vm_id}/backups/{backup_id}")

    def list_snapshots(self, vm_id: int, page: int = 1, per_page: int = 25) -> BaseResponse[List[Snapshot]]:
        """List VM snapshots."""
        resp = self._client._request("GET", f"/api/vps/vms/{vm_id}/snapshots", {"page": page, "per_page": per_page})
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[Snapshot(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def create_snapshot(self, vm_id: int, name: Optional[str] = None) -> BaseResponse[Snapshot]:
        """Create a VM snapshot."""
        body: Dict[str, Any] = {}
        if name:
            body["name"] = name
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/snapshots", body=body or None)
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Snapshot(**_map_camel_dict(data)), status_code=resp.status_code)

    def restore_snapshot(self, vm_id: int, snapshot_id: int) -> BaseResponse[VPSAction]:
        """Restore VM from a snapshot."""
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/snapshots/{snapshot_id}/restore")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=VPSAction(**_map_camel_dict(data)), status_code=resp.status_code)

    def delete_snapshot(self, vm_id: int, snapshot_id: int) -> BaseResponse[Dict[str, Any]]:
        """Delete a snapshot."""
        return self._client._request("DELETE", f"/api/vps/vms/{vm_id}/snapshots/{snapshot_id}")

    def get_firewall(self, vm_id: int) -> BaseResponse[FirewallConfig]:
        """Get VM firewall configuration."""
        resp = self._client._request("GET", f"/api/vps/vms/{vm_id}/firewall")
        data = resp.data if isinstance(resp.data, dict) else {}
        rules = data.get("rules", [])
        if isinstance(rules, list):
            rule_objs = [FirewallRule(**_map_camel_dict(r)) for r in rules]
        else:
            rule_objs = []
        config = FirewallConfig(vm_id=vm_id, enabled=data.get("enabled", True), default_action=data.get("default_action") or data.get("defaultAction", "drop"), rules=rule_objs)
        return BaseResponse(data=config, status_code=resp.status_code)

    def update_firewall(self, vm_id: int, config: FirewallConfig) -> BaseResponse[FirewallConfig]:
        """Update VM firewall configuration."""
        payload = {"enabled": config.enabled, "default_action": config.default_action, "rules": [asdict(r) for r in config.rules]}
        resp = self._client._request("PUT", f"/api/vps/vms/{vm_id}/firewall", body=payload)
        data = resp.data if isinstance(resp.data, dict) else {}
        rules = data.get("rules", [])
        if isinstance(rules, list):
            rule_objs = [FirewallRule(**_map_camel_dict(r)) for r in rules]
        else:
            rule_objs = []
        new_config = FirewallConfig(vm_id=vm_id, enabled=data.get("enabled", True), default_action=data.get("default_action") or data.get("defaultAction", "drop"), rules=rule_objs)
        return BaseResponse(data=new_config, status_code=resp.status_code)

    def add_firewall_rule(self, vm_id: int, rule: FirewallRule) -> BaseResponse[FirewallRule]:
        """Add a firewall rule."""
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/firewall/rules", body=asdict(rule))
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=FirewallRule(**_map_camel_dict(data)), status_code=resp.status_code)

    def delete_firewall_rule(self, vm_id: int, rule_id: int) -> BaseResponse[Dict[str, Any]]:
        """Delete a firewall rule."""
        return self._client._request("DELETE", f"/api/vps/vms/{vm_id}/firewall/rules/{rule_id}")

    def scan_malware(self, vm_id: int) -> BaseResponse[MalwareScanResult]:
        """Initiate malware scan on VM."""
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/security/malware-scan")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=MalwareScanResult(**_map_camel_dict(data)), status_code=resp.status_code)

    def get_malware_scan(self, vm_id: int, scan_id: str) -> BaseResponse[MalwareScanResult]:
        """Get malware scan results."""
        resp = self._client._request("GET", f"/api/vps/vms/{vm_id}/security/malware-scan/{scan_id}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=MalwareScanResult(**_map_camel_dict(data)), status_code=resp.status_code)

    def list_ssh_keys(self, vm_id: Optional[int] = None, page: int = 1, per_page: int = 25) -> BaseResponse[List[SSHKey]]:
        """List SSH keys (global or per-VM)."""
        path = f"/api/vps/vms/{vm_id}/ssh-keys" if vm_id is not None else "/api/vps/ssh-keys"
        resp = self._client._request("GET", path, {"page": page, "per_page": per_page})
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[SSHKey(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def add_ssh_key(self, name: str, public_key: str, vm_id: Optional[int] = None) -> BaseResponse[SSHKey]:
        """Add an SSH key."""
        body = {"name": name, "public_key": public_key}
        path = f"/api/vps/vms/{vm_id}/ssh-keys" if vm_id is not None else "/api/vps/ssh-keys"
        resp = self._client._request("POST", path, body=body)
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=SSHKey(**_map_camel_dict(data)), status_code=resp.status_code)

    def delete_ssh_key(self, key_id: int, vm_id: Optional[int] = None) -> BaseResponse[Dict[str, Any]]:
        """Delete an SSH key."""
        path = f"/api/vps/vms/{vm_id}/ssh-keys/{key_id}" if vm_id is not None else f"/api/vps/ssh-keys/{key_id}"
        return self._client._request("DELETE", path)

    def regenerate_ssh_key(self, key_id: int, vm_id: Optional[int] = None) -> BaseResponse[SSHKey]:
        """Regenerate an SSH key pair."""
        path = f"/api/vps/vms/{vm_id}/ssh-keys/{key_id}/regenerate" if vm_id is not None else f"/api/vps/ssh-keys/{key_id}/regenerate"
        resp = self._client._request("POST", path)
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=SSHKey(**_map_camel_dict(data)), status_code=resp.status_code)

    def get_ptr_record(self, vm_id: int, ip: str) -> BaseResponse[PTRRecord]:
        """Get PTR record for an IP."""
        resp = self._client._request("GET", f"/api/vps/vms/{vm_id}/network/ptr", {"ip": ip})
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=PTRRecord(**_map_camel_dict(data)), status_code=resp.status_code)

    def set_ptr_record(self, vm_id: int, ip: str, ptr_value: str) -> BaseResponse[PTRRecord]:
        """Set PTR record for an IP."""
        resp = self._client._request("PUT", f"/api/vps/vms/{vm_id}/network/ptr", body={"ip": ip, "ptr_value": ptr_value})
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=PTRRecord(**_map_camel_dict(data)), status_code=resp.status_code)

    def delete_ptr_record(self, vm_id: int, ip: str) -> BaseResponse[Dict[str, Any]]:
        """Delete PTR record for an IP."""
        return self._client._request("DELETE", f"/api/vps/vms/{vm_id}/network/ptr", {"ip": ip})

    def list_os_templates(self) -> BaseResponse[List[OSTemplate]]:
        """List available OS templates."""
        resp = self._client._request("GET", "/api/vps/os-templates")
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[OSTemplate(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def get_os_template(self, template_id: int) -> BaseResponse[OSTemplate]:
        """Get OS template details."""
        resp = self._client._request("GET", f"/api/vps/os-templates/{template_id}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=OSTemplate(**_map_camel_dict(data)), status_code=resp.status_code)

    def reinstall_os(self, vm_id: int, os_template_id: int, preserve_data: bool = False) -> BaseResponse[VPSAction]:
        """Reinstall OS on VM."""
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/os/reinstall", body={"os_template_id": os_template_id, "preserve_data": preserve_data})
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=VPSAction(**_map_camel_dict(data)), status_code=resp.status_code)

    def get_recovery_console(self, vm_id: int) -> BaseResponse[RecoveryConsole]:
        """Get recovery console access URL/token."""
        resp = self._client._request("GET", f"/api/vps/vms/{vm_id}/recovery/console")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=RecoveryConsole(**_map_camel_dict(data)), status_code=resp.status_code)

    def boot_recovery_mode(self, vm_id: int) -> BaseResponse[VPSAction]:
        """Boot VM into recovery mode."""
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/recovery/boot")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=VPSAction(**_map_camel_dict(data)), status_code=resp.status_code)

    def mount_iso(self, vm_id: int, iso_url: str) -> BaseResponse[VPSAction]:
        """Mount custom ISO on VM."""
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/recovery/iso", body={"iso_url": iso_url})
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=VPSAction(**_map_camel_dict(data)), status_code=resp.status_code)

    def list_docker_containers(self, vm_id: int) -> BaseResponse[List[DockerContainer]]:
        """List Docker containers on VM."""
        resp = self._client._request("GET", f"/api/vps/vms/{vm_id}/docker/containers")
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[DockerContainer(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def get_docker_container(self, vm_id: int, container_id: str) -> BaseResponse[DockerContainer]:
        """Get Docker container details."""
        resp = self._client._request("GET", f"/api/vps/vms/{vm_id}/docker/containers/{container_id}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=DockerContainer(**_map_camel_dict(data)), status_code=resp.status_code)

    def start_docker_container(self, vm_id: int, container_id: str) -> BaseResponse[DockerContainer]:
        """Start a Docker container."""
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/docker/containers/{container_id}/start")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=DockerContainer(**_map_camel_dict(data)), status_code=resp.status_code)

    def stop_docker_container(self, vm_id: int, container_id: str) -> BaseResponse[DockerContainer]:
        """Stop a Docker container."""
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/docker/containers/{container_id}/stop")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=DockerContainer(**_map_camel_dict(data)), status_code=resp.status_code)

    def restart_docker_container(self, vm_id: int, container_id: str) -> BaseResponse[DockerContainer]:
        """Restart a Docker container."""
        resp = self._client._request("POST", f"/api/vps/vms/{vm_id}/docker/containers/{container_id}/restart")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=DockerContainer(**_map_camel_dict(data)), status_code=resp.status_code)

    def get_docker_logs(self, vm_id: int, container_id: str, tail: int = 100) -> BaseResponse[str]:
        """Get Docker container logs."""
        resp = self._client._request("GET", f"/api/vps/vms/{vm_id}/docker/containers/{container_id}/logs", {"tail": tail})
        return BaseResponse(data=resp.data if isinstance(resp.data, str) else "", status_code=resp.status_code)

    def list_post_install_scripts(self, vm_id: Optional[int] = None, page: int = 1, per_page: int = 25) -> BaseResponse[List[PostInstallScript]]:
        """List post-install scripts."""
        path = f"/api/vps/vms/{vm_id}/post-install-scripts" if vm_id is not None else "/api/vps/post-install-scripts"
        resp = self._client._request("GET", path, {"page": page, "per_page": per_page})
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[PostInstallScript(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def get_post_install_script(self, script_id: int) -> BaseResponse[PostInstallScript]:
        """Get post-install script details."""
        resp = self._client._request("GET", f"/api/vps/post-install-scripts/{script_id}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=PostInstallScript(**_map_camel_dict(data)), status_code=resp.status_code)

    def set_post_install_script(self, vm_id: int, script_id: int) -> BaseResponse[Dict[str, Any]]:
        """Set post-install script for VM."""
        return self._client._request("PUT", f"/api/vps/vms/{vm_id}/post-install-scripts", body={"script_id": script_id})

    def create_post_install_script(self, name: str, script: str, interpreter: str = "bash") -> BaseResponse[PostInstallScript]:
        """Create a new post-install script."""
        resp = self._client._request("POST", "/api/vps/post-install-scripts", body={"name": name, "script": script, "interpreter": interpreter})
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=PostInstallScript(**_map_camel_dict(data)), status_code=resp.status_code)

    def delete_post_install_script(self, script_id: int) -> BaseResponse[Dict[str, Any]]:
        """Delete a post-install script."""
        return self._client._request("DELETE", f"/api/vps/post-install-scripts/{script_id}")

    def update_post_install_script(self, script_id: int, name: Optional[str] = None, script: Optional[str] = None, interpreter: Optional[str] = None) -> BaseResponse[PostInstallScript]:
        """Update a post-install script."""
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if script is not None:
            body["script"] = script
        if interpreter is not None:
            body["interpreter"] = interpreter
        resp = self._client._request("PATCH", f"/api/vps/post-install-scripts/{script_id}", body=body)
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=PostInstallScript(**_map_camel_dict(data)), status_code=resp.status_code)

    def __repr__(self) -> str:
        return "VPSAPI()"


# ---------------------------------------------------------------------------
# ReachAPI
# ---------------------------------------------------------------------------


class ReachAPI:
    """Reach (CRM) service: contacts, profiles, segments."""

    def __init__(self, client: HostingerClient) -> None:
        self._client = client

    def list_contacts(self, page: int = 1, per_page: int = 25) -> BaseResponse[List[Contact]]:
        """List contacts."""
        resp = self._client._request("GET", "/api/reach/contacts", {"page": page, "per_page": per_page})
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[Contact(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def get_contact(self, contact_id: int) -> BaseResponse[Contact]:
        """Get contact details."""
        resp = self._client._request("GET", f"/api/reach/contacts/{contact_id}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Contact(**_map_camel_dict(data)), status_code=resp.status_code)

    def create_contact(self, contact: Contact) -> BaseResponse[Contact]:
        """Create a new contact."""
        resp = self._client._request("POST", "/api/reach/contacts", body=asdict(contact))
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Contact(**_map_camel_dict(data)), status_code=resp.status_code)

    def update_contact(self, contact_id: int, contact: Contact) -> BaseResponse[Contact]:
        """Update a contact."""
        resp = self._client._request("PUT", f"/api/reach/contacts/{contact_id}", body=asdict(contact))
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Contact(**_map_camel_dict(data)), status_code=resp.status_code)

    def delete_contact(self, contact_id: int) -> BaseResponse[Dict[str, Any]]:
        """Delete a contact."""
        return self._client._request("DELETE", f"/api/reach/contacts/{contact_id}")

    def get_profile(self) -> BaseResponse[Profile]:
        """Get current profile."""
        resp = self._client._request("GET", "/api/reach/profile")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Profile(**_map_camel_dict(data)), status_code=resp.status_code)

    def update_profile(self, profile: Profile) -> BaseResponse[Profile]:
        """Update profile."""
        resp = self._client._request("PUT", "/api/reach/profile", body=asdict(profile))
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Profile(**_map_camel_dict(data)), status_code=resp.status_code)

    def list_segments(self, page: int = 1, per_page: int = 25) -> BaseResponse[List[Segment]]:
        """List audience segments."""
        resp = self._client._request("GET", "/api/reach/segments", {"page": page, "per_page": per_page})
        items = resp.data if isinstance(resp.data, list) else []
        return BaseResponse(data=[Segment(**_map_camel_dict(i)) for i in items], status_code=resp.status_code)

    def get_segment(self, segment_id: int) -> BaseResponse[Segment]:
        """Get segment details."""
        resp = self._client._request("GET", f"/api/reach/segments/{segment_id}")
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Segment(**_map_camel_dict(data)), status_code=resp.status_code)

    def create_segment(self, segment: Segment) -> BaseResponse[Segment]:
        """Create a new segment."""
        resp = self._client._request("POST", "/api/reach/segments", body=asdict(segment))
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Segment(**_map_camel_dict(data)), status_code=resp.status_code)

    def update_segment(self, segment_id: int, segment: Segment) -> BaseResponse[Segment]:
        """Update a segment."""
        resp = self._client._request("PUT", f"/api/reach/segments/{segment_id}", body=asdict(segment))
        data = resp.data if isinstance(resp.data, dict) else {}
        return BaseResponse(data=Segment(**_map_camel_dict(data)), status_code=resp.status_code)

    def delete_segment(self, segment_id: int) -> BaseResponse[Dict[str, Any]]:
        """Delete a segment."""
        return self._client._request("DELETE", f"/api/reach/segments/{segment_id}")

    def __repr__(self) -> str:
        return "ReachAPI()"


# ---------------------------------------------------------------------------
# HostingerKernel — MAGNATRIX Bridge
# ---------------------------------------------------------------------------


class HostingerKernel:
    """MAGNATRIX OS bridge for Hostinger API.

    Auto-registers to:
    - Layer 7: Browser/HTTP client (exposes HostingerClient as HTTP service)
    - Layer 5: Knowledge/Infrastructure catalog (indexes VPS, domains, hosting)
    - Layer 11: Governance/Domain management (domain expiry alerts, auto-renewal governance)

    Event hooks:
    - VPS lifecycle: created, started, stopped, destroyed
    - Domain expiry: threshold-based alerts
    - Auto-renewal governance: enforce policies
    """

    def __init__(
        self,
        api_token: str,
        base_url: str = HostingerClient.DEFAULT_BASE_URL,
        use_httpx: bool = False,
    ) -> None:
        self.client = HostingerClient(
            api_token=api_token,
            base_url=base_url,
            use_httpx=use_httpx,
        )
        self.billing = BillingAPI(self.client)
        self.dns = DNSAPI(self.client)
        self.domains = DomainsAPI(self.client)
        self.hosting = HostingAPI(self.client)
        self.vps = VPSAPI(self.client)
        self.reach = ReachAPI(self.client)
        self._hooks: Dict[str, List[Callable[..., Any]]] = {
            "vm_created": [],
            "vm_started": [],
            "vm_stopped": [],
            "vm_destroyed": [],
            "domain_expiring": [],
            "auto_renewal_disabled": [],
        }
        self._layer7_registered: bool = False
        self._layer5_registered: bool = False
        self._layer11_registered: bool = False

    def register_hook(self, event: str, callback: Callable[..., Any]) -> "HostingerKernel":
        """Register an event hook.

        Events: vm_created, vm_started, vm_stopped, vm_destroyed,
                domain_expiring, auto_renewal_disabled
        """
        if event in self._hooks:
            self._hooks[event].append(callback)
        return self

    def _emit(self, event: str, **kwargs: Any) -> None:
        """Emit event to all registered hooks."""
        for cb in self._hooks.get(event, []):
            try:
                cb(**kwargs)
            except Exception:
                pass

    def register_layer7(self) -> "HostingerKernel":
        """Register to MAGNATRIX Layer 7 (Browser/HTTP client)."""
        self._layer7_registered = True
        return self

    def register_layer5(self) -> "HostingerKernel":
        """Register to MAGNATRIX Layer 5 (Knowledge/Infrastructure)."""
        self._layer5_registered = True
        return self

    def register_layer11(self, expiry_days: int = 30) -> "HostingerKernel":
        """Register to MAGNATRIX Layer 11 (Governance/Domain).

        Args:
            expiry_days: Days before expiry to trigger alerts.
        """
        self._layer11_registered = True
        self._expiry_threshold_days = expiry_days
        return self

    def check_domain_expiry(self) -> List[Dict[str, Any]]:
        """Check all domains for upcoming expiry and emit alerts."""
        import datetime
        alerts: List[Dict[str, Any]] = []
        try:
            portfolio = self.domains.list_portfolio(per_page=100)
            for domain in portfolio.data:
                if domain.expires_at:
                    try:
                        expiry = datetime.datetime.strptime(domain.expires_at, "%Y-%m-%d")
                        days_remaining = (expiry - datetime.datetime.now()).days
                        if days_remaining <= getattr(self, "_expiry_threshold_days", 30):
                            alert = {
                                "domain": domain.domain,
                                "expires_at": domain.expires_at,
                                "days_remaining": days_remaining,
                                "auto_renew": domain.auto_renew,
                            }
                            alerts.append(alert)
                            self._emit("domain_expiring", **alert)
                    except Exception:
                        pass
        except HostingerError:
            pass
        return alerts

    def enforce_auto_renewal(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Enforce auto-renewal governance on domains.

        If auto-renew is disabled, emit governance event.
        Optionally re-enable if policy requires.
        """
        violations: List[Dict[str, Any]] = []
        try:
            portfolio = self.domains.list_portfolio(per_page=100)
            for d in portfolio.data:
                if domain and d.domain != domain:
                    continue
                if not d.auto_renew:
                    violation = {
                        "domain": d.domain,
                        "issue": "auto_renew_disabled",
                    }
                    violations.append(violation)
                    self._emit("auto_renewal_disabled", **violation)
        except HostingerError:
            pass
        return violations

    def vm_lifecycle_create(
        self, plan_id: int, os_template_id: int, datacenter_id: int, **kwargs: Any
    ) -> BaseResponse[VM]:
        """Create VM with lifecycle hook."""
        resp = self.vps.create_vm(plan_id, os_template_id, datacenter_id, **kwargs)
        if resp.data and isinstance(resp.data, VM):
            self._emit("vm_created", vm=resp.data)
        return resp

    def vm_lifecycle_start(self, vm_id: int) -> BaseResponse[VPSAction]:
        """Start VM with lifecycle hook."""
        resp = self.vps.start_vm(vm_id)
        self._emit("vm_started", vm_id=vm_id, action=resp.data)
        return resp

    def vm_lifecycle_stop(self, vm_id: int) -> BaseResponse[VPSAction]:
        """Stop VM with lifecycle hook."""
        resp = self.vps.stop_vm(vm_id)
        self._emit("vm_stopped", vm_id=vm_id, action=resp.data)
        return resp

    def vm_lifecycle_destroy(self, vm_id: int) -> BaseResponse[Dict[str, Any]]:
        """Destroy VM with lifecycle hook."""
        resp = self.vps.destroy_vm(vm_id)
        self._emit("vm_destroyed", vm_id=vm_id)
        return resp

    def full_sync(self) -> Dict[str, Any]:
        """Sync all infrastructure state to MAGNATRIX knowledge layer.

        Returns summary of indexed resources.
        """
        summary: Dict[str, Any] = {
            "vms": [],
            "domains": [],
            "websites": [],
            "subscriptions": [],
        }
        try:
            vms = self.vps.list_vms(per_page=100)
            summary["vms"] = [asdict(vm) for vm in vms.data]
        except HostingerError:
            pass
        try:
            domains = self.domains.list_portfolio(per_page=100)
            summary["domains"] = [asdict(d) for d in domains.data]
        except HostingerError:
            pass
        try:
            websites = self.hosting.list_websites(per_page=100)
            summary["websites"] = [asdict(w) for w in websites.data]
        except HostingerError:
            pass
        try:
            subs = self.billing.list_subscriptions(per_page=100)
            summary["subscriptions"] = [asdict(s) for s in subs.data]
        except HostingerError:
            pass
        return summary

    def __repr__(self) -> str:
        return (
            f"HostingerKernel(layer7={self._layer7_registered}, "
            f"layer5={self._layer5_registered}, layer11={self._layer11_registered})"
        )


# ---------------------------------------------------------------------------
# Demo / Self-Test
# ---------------------------------------------------------------------------


def demo() -> None:
    """Demo script: simulates VPS lifecycle + domain check + DNS update.

    This demo runs without a real API token, showing the SDK structure.
    To run against real API, set HOSTINGER_API_TOKEN env var.
    """
    import os
    token = os.environ.get("HOSTINGER_API_TOKEN", "demo-token")
    client = HostingerClient(api_token=token)

    print("=" * 60)
    print("Hostinger API Native SDK Demo")
    print("=" * 60)

    # 1. VPS Lifecycle simulation
    print("\n[1] VPS Lifecycle Demo")
    vps = VPSAPI(client)
    try:
        vms = vps.list_vms()
        print(f"   VMs: {vms.data}")
    except HostingerError as e:
        print(f"   list_vms: {e.__class__.__name__}: {e.message}")

    try:
        vm = vps.create_vm(plan_id=1, os_template_id=2, datacenter_id=3, hostname="demo-vm")
        print(f"   create_vm: {vm.data}")
    except HostingerError as e:
        print(f"   create_vm: {e.__class__.__name__}: {e.message}")

    try:
        action = vps.start_vm(vm_id=42)
        print(f"   start_vm: {action.data}")
    except HostingerError as e:
        print(f"   start_vm: {e.__class__.__name__}: {e.message}")

    try:
        snap = vps.create_snapshot(vm_id=42, name="pre-update")
        print(f"   create_snapshot: {snap.data}")
    except HostingerError as e:
        print(f"   create_snapshot: {e.__class__.__name__}: {e.message}")

    try:
        action = vps.stop_vm(vm_id=42)
        print(f"   stop_vm: {action.data}")
    except HostingerError as e:
        print(f"   stop_vm: {e.__class__.__name__}: {e.message}")

    try:
        result = vps.destroy_vm(vm_id=42)
        print(f"   destroy_vm: {result.data}")
    except HostingerError as e:
        print(f"   destroy_vm: {e.__class__.__name__}: {e.message}")

    # 2. Domain Availability Check
    print("\n[2] Domain Availability Demo")
    domains = DomainsAPI(client)
    try:
        avail = domains.check_availability("example.com")
        print(f"   check_availability: {avail.data}")
    except HostingerError as e:
        print(f"   check_availability: {e.__class__.__name__}: {e.message}")

    # 3. DNS Zone Update Demo
    print("\n[3] DNS Zone Update Demo")
    dns = DNSAPI(client)
    try:
        zone = dns.get_zone("example.com")
        print(f"   get_zone: {zone.data}")
    except HostingerError as e:
        print(f"   get_zone: {e.__class__.__name__}: {e.message}")

    try:
        record = DNSRecord(name="www", type="A", value="1.2.3.4", ttl=300)
        new_zone = dns.update_zone("example.com", [record])
        print(f"   update_zone: {new_zone.data}")
    except HostingerError as e:
        print(f"   update_zone: {e.__class__.__name__}: {e.message}")

    # 4. Kernel Demo
    print("\n[4] HostingerKernel Demo")
    kernel = HostingerKernel(api_token=token)
    kernel.register_layer7().register_layer5().register_layer11(expiry_days=30)
    print(f"   {kernel}")

    print("\n" + "=" * 60)
    print("Demo complete. Set HOSTINGER_API_TOKEN for live API calls.")
    print("=" * 60)


if __name__ == "__main__":
    demo()
