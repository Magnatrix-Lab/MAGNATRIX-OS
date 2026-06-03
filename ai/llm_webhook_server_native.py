#!/usr/bin/env python3
"""
MAGNATRIX-OS — Webhook Server Engine
ai/llm_webhook_server_native.py

Features:
- Webhook endpoint registration (URL patterns, handlers)
- Payload validation (signature verification simulation)
- Retry mechanism with exponential backoff for failed deliveries
- Event routing (route webhooks to registered handlers)
- Delivery logging and status tracking

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import hashlib
import hmac
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("webhook_server")


class DeliveryStatus(enum.Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class WebhookEndpoint:
    id: str
    url_pattern: str
    handler: Callable[[Dict[str, Any]], Any]
    secret: Optional[str] = None
    retries: int = 3


@dataclass
class WebhookDelivery:
    id: str
    endpoint_id: str
    payload: Dict[str, Any]
    status: DeliveryStatus
    attempts: int = 0
    timestamp: float = 0.0
    response: Optional[str] = None


class WebhookServerEngine:
    """Webhook server with routing, validation, and retry."""

    def __init__(self):
        self._endpoints: Dict[str, WebhookEndpoint] = {}
        self._deliveries: Dict[str, WebhookDelivery] = {}
        self._history: List[WebhookDelivery] = []
        self._counter = 0

    def register(self, endpoint: WebhookEndpoint) -> None:
        self._endpoints[endpoint.id] = endpoint
        logger.info(f"Registered webhook endpoint: {endpoint.id}")

    def unregister(self, endpoint_id: str) -> bool:
        if endpoint_id in self._endpoints:
            del self._endpoints[endpoint_id]
            return True
        return False

    def _verify_signature(self, payload: str, secret: str, signature: str) -> bool:
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def receive(self, endpoint_id: str, payload: Dict[str, Any], signature: Optional[str] = None) -> WebhookDelivery:
        """Receive a webhook payload."""
        self._counter += 1
        delivery_id = f"DEL-{self._counter}"
        endpoint = self._endpoints.get(endpoint_id)
        if not endpoint:
            delivery = WebhookDelivery(delivery_id, endpoint_id, payload, DeliveryStatus.FAILED, 0, time.time(), "Endpoint not found")
            self._history.append(delivery)
            return delivery

        # Verify signature if secret exists
        if endpoint.secret and signature:
            payload_str = str(payload)
            if not self._verify_signature(payload_str, endpoint.secret, signature):
                delivery = WebhookDelivery(delivery_id, endpoint_id, payload, DeliveryStatus.FAILED, 0, time.time(), "Invalid signature")
                self._history.append(delivery)
                return delivery

        # Attempt delivery
        delivery = WebhookDelivery(delivery_id, endpoint_id, payload, DeliveryStatus.PENDING, 0, time.time())
        for attempt in range(endpoint.retries + 1):
            delivery.attempts = attempt + 1
            try:
                result = endpoint.handler(payload)
                delivery.status = DeliveryStatus.DELIVERED
                delivery.response = str(result)
                break
            except Exception as e:
                delivery.status = DeliveryStatus.RETRYING if attempt < endpoint.retries else DeliveryStatus.FAILED
                delivery.response = str(e)[:200]
                if attempt < endpoint.retries:
                    time.sleep(0.1 * (2 ** attempt))  # exponential backoff
        self._history.append(delivery)
        return delivery

    def get_endpoint_status(self, endpoint_id: str) -> Dict[str, Any]:
        deliveries = [d for d in self._history if d.endpoint_id == endpoint_id]
        total = len(deliveries)
        success = sum(1 for d in deliveries if d.status == DeliveryStatus.DELIVERED)
        return {"total": total, "delivered": success, "failed": total - success, "success_rate": success / max(total, 1)}

    def get_history(self, n: int = 20) -> List[WebhookDelivery]:
        return self._history[-n:]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._history)
        delivered = sum(1 for d in self._history if d.status == DeliveryStatus.DELIVERED)
        return {
            "endpoints": len(self._endpoints),
            "total_deliveries": total,
            "delivered": delivered,
            "failed": total - delivered,
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Webhook Server Engine")
    print("ai/llm_webhook_server_native.py")
    print("=" * 60)

    engine = WebhookServerEngine()

    # 1. Register endpoints
    print("\n[1] Register Endpoints")
    def handler_a(payload):
        return f"Processed: {payload.get('event', 'unknown')}"
    def handler_b(payload):
        if payload.get('amount', 0) > 1000:
            raise ValueError("Amount too large")
        return f"Payment: {payload.get('amount', 0)}"
    def flaky_handler(payload):
        if random.random() < 0.5:
            raise RuntimeError("Flaky service")
        return "OK"

    engine.register(WebhookEndpoint("e1", "/events", handler_a, secret="secret123"))
    engine.register(WebhookEndpoint("e2", "/payments", handler_b, retries=2))
    engine.register(WebhookEndpoint("e3", "/flaky", flaky_handler, retries=3))
    print(f"  Registered 3 endpoints")

    # 2. Deliver with valid signature
    print("\n[2] Valid Signature Delivery")
    import hashlib, hmac
    payload = {"event": "user.signup", "user": "alice"}
    payload_str = str(payload)
    sig = hmac.new("secret123".encode(), payload_str.encode(), hashlib.sha256).hexdigest()
    d = engine.receive("e1", payload, sig)
    print(f"  Status: {d.status.value}, Response: {d.response}")

    # 3. Invalid signature
    print("\n[3] Invalid Signature")
    d = engine.receive("e1", payload, "bad_signature")
    print(f"  Status: {d.status.value}, Response: {d.response}")

    # 4. Failed then retry
    print("\n[4] Retry Mechanism")
    d = engine.receive("e2", {"amount": 5000})
    print(f"  Status: {d.status.value}, Attempts: {d.attempts}")

    # 5. Flaky endpoint
    print("\n[5] Flaky Endpoint (may succeed after retries)")
    random.seed(42)
    for i in range(3):
        d = engine.receive("e3", {"data": i})
        print(f"  Attempt {i+1}: {d.status.value} (attempts={d.attempts})")

    # 6. Stats
    print("\n[6] Engine Stats")
    stats = engine.get_stats()
    print(f"  {stats}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
