"""
Hostinger Webhook Server — Receive and route Hostinger API webhooks to MAGNATRIX events.

Runs a lightweight HTTP server that listens for Hostinger webhook callbacks
and emits them to the HostingerKernel event system.

Usage:
    python3 hostinger_webhook_server.py --port 8080 --token $WEBHOOK_SECRET

Supported events:
    vm.created, vm.started, vm.stopped, vm.destroyed
    domain.registered, domain.expiring, domain.renewed
    backup.completed, snapshot.created
    invoice.paid, invoice.failed
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import logging
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Callable, Dict, List, Optional

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("hostinger-webhook")


class WebhookEvent:
    """Parsed Hostinger webhook event."""

    def __init__(self, event_type: str, payload: Dict[str, Any], signature: Optional[str] = None) -> None:
        self.event_type = event_type
        self.payload = payload
        self.signature = signature
        self.timestamp: Optional[str] = payload.get("timestamp")
        self.event_id: Optional[str] = payload.get("event_id")

    def __repr__(self) -> str:
        return f"WebhookEvent(type={self.event_type!r}, id={self.event_id})"


class WebhookRouter:
    """Routes webhook events to registered handlers."""

    def __init__(self, secret: Optional[str] = None) -> None:
        self.secret = secret
        self._handlers: Dict[str, List[Callable[[WebhookEvent], None]]] = {}
        self._catch_all: List[Callable[[WebhookEvent], None]] = []

    def on(self, event_type: str, handler: Callable[[WebhookEvent], None]) -> "WebhookRouter":
        """Register handler for a specific event type."""
        self._handlers.setdefault(event_type, []).append(handler)
        return self

    def on_any(self, handler: Callable[[WebhookEvent], None]) -> "WebhookRouter":
        """Register catch-all handler."""
        self._catch_all.append(handler)
        return self

    def verify_signature(self, body: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 signature if secret is configured."""
        if not self.secret:
            return True
        expected = hmac.new(
            self.secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def dispatch(self, event: WebhookEvent) -> None:
        """Dispatch event to all matching handlers."""
        logger.info(f"Dispatching {event.event_type} (id={event.event_id})")

        # Specific handlers
        for handler in self._handlers.get(event.event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler error for {event.event_type}: {e}")

        # Catch-all handlers
        for handler in self._catch_all:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Catch-all handler error: {e}")


class HostingerWebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Hostinger webhooks."""

    router: Optional[WebhookRouter] = None

    def log_message(self, format: str, *args: Any) -> None:
        logger.info(format % args)

    def do_POST(self) -> None:
        if self.path != "/webhook":
            self.send_error(404, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # Get signature header
        signature = self.headers.get("X-Hostinger-Signature", "")

        # Parse JSON
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        event_type = payload.get("event_type", "unknown")
        event = WebhookEvent(event_type, payload, signature)

        # Verify signature
        if self.router and self.router.secret:
            if not self.router.verify_signature(body, signature):
                logger.warning(f"Invalid signature for event {event.event_id}")
                self.send_error(401, "Invalid Signature")
                return

        # Dispatch
        if self.router:
            self.router.dispatch(event)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"received": true}')

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_error(404, "Not Found")


def make_handler(router: WebhookRouter) -> type:
    """Create a handler class bound to a router instance."""
    class BoundHandler(HostingerWebhookHandler):
        pass
    BoundHandler.router = router
    return BoundHandler


class WebhookServer:
    """Standalone webhook server."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080, secret: Optional[str] = None) -> None:
        self.host = host
        self.port = port
        self.router = WebhookRouter(secret=secret)
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self, blocking: bool = True) -> None:
        """Start the webhook server."""
        handler = make_handler(self.router)
        self._server = HTTPServer((self.host, self.port), handler)
        logger.info(f"Webhook server listening on http://{self.host}:{self.port}/webhook")
        logger.info(f"Health check: http://{self.host}:{self.port}/health")

        if blocking:
            self._server.serve_forever()
        else:
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop the webhook server."""
        if self._server:
            self._server.shutdown()
            logger.info("Webhook server stopped")

    def on(self, event_type: str, handler: Callable[[WebhookEvent], None]) -> "WebhookServer":
        """Register event handler."""
        self.router.on(event_type, handler)
        return self

    def on_any(self, handler: Callable[[WebhookEvent], None]) -> "WebhookServer":
        """Register catch-all handler."""
        self.router.on_any(handler)
        return self


# ---------------------------------------------------------------------------
# MAGNATRIX Integration Handlers
# ---------------------------------------------------------------------------


def vm_created_handler(event: WebhookEvent) -> None:
    """Handle VM created webhook."""
    vm = event.payload.get("data", {})
    logger.info(f"VM created: {vm.get('name')} (id={vm.get('id')})")


def vm_started_handler(event: WebhookEvent) -> None:
    """Handle VM started webhook."""
    vm = event.payload.get("data", {})
    logger.info(f"VM started: {vm.get('name')} (id={vm.get('id')})")


def vm_stopped_handler(event: WebhookEvent) -> None:
    """Handle VM stopped webhook."""
    vm = event.payload.get("data", {})
    logger.info(f"VM stopped: {vm.get('name')} (id={vm.get('id')})")


def vm_destroyed_handler(event: WebhookEvent) -> None:
    """Handle VM destroyed webhook."""
    vm_id = event.payload.get("data", {}).get("id")
    logger.info(f"VM destroyed: id={vm_id}")


def domain_expiring_handler(event: WebhookEvent) -> None:
    """Handle domain expiring webhook."""
    domain = event.payload.get("data", {})
    logger.warning(
        f"Domain expiring: {domain.get('domain')} in {domain.get('days_remaining')} days"
    )


def invoice_paid_handler(event: WebhookEvent) -> None:
    """Handle invoice paid webhook."""
    inv = event.payload.get("data", {})
    logger.info(f"Invoice paid: {inv.get('id')} amount={inv.get('amount')} {inv.get('currency')}")


def snapshot_created_handler(event: WebhookEvent) -> None:
    """Handle snapshot created webhook."""
    snap = event.payload.get("data", {})
    logger.info(f"Snapshot created: {snap.get('name')} vm={snap.get('vm_id')}")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="hostinger-webhook-server",
        description="Hostinger Webhook Server — route events to MAGNATRIX",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8080, help="Bind port")
    parser.add_argument("--secret", help="Webhook signature secret")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    server = WebhookServer(host=args.host, port=args.port, secret=args.secret)

    # Register default handlers
    server.on("vm.created", vm_created_handler)
    server.on("vm.started", vm_started_handler)
    server.on("vm.stopped", vm_stopped_handler)
    server.on("vm.destroyed", vm_destroyed_handler)
    server.on("domain.expiring", domain_expiring_handler)
    server.on("invoice.paid", invoice_paid_handler)
    server.on("snapshot.created", snapshot_created_handler)

    # Catch-all logger
    def log_all(event: WebhookEvent) -> None:
        logger.debug(f"Received event: {event.event_type} payload={event.payload}")

    server.on_any(log_all)

    try:
        server.start(blocking=True)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
