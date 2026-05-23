"""
Hostinger Skill Adapter for MAGNATRIX OS Orchestrator
=======================================================
Bridges the Hostinger API SDK to MAGNATRIX's task bus and agent governance system.

Usage:
    from hostinger_magnatrix_adapter import HostingerSkillAdapter
    adapter = HostingerSkillAdapter(orchestrator)
    adapter.register()

Features:
- Auto-discovery by MAGNATRIX Skills Registry
- Task bus integration: commands become tasks
- Constitution-aware: validates actions before execution
- Event streaming: webhook events → MAGNATRIX event bus
- Health reporting: periodic status to orchestrator
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger("hostinger-magnatrix")


# ---------------------------------------------------------------------------
# Task / Command Types
# ---------------------------------------------------------------------------

@dataclass
class SkillTask:
    """MAGNATRIX task representation for Hostinger commands."""
    task_id: str
    command: str
    params: Dict[str, Any]
    agent_id: str = "hostinger-skill"
    priority: int = 5
    timeout_seconds: int = 60
    created_at: Optional[float] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


@dataclass
class SkillResult:
    """Result of executing a Hostinger skill command."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    task_id: str = ""
    execution_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# Hostinger Skill Adapter
# ---------------------------------------------------------------------------

class HostingerSkillAdapter:
    """
    MAGNATRIX skill adapter for Hostinger API.
    
    Provides:
    - Command dispatch to HostingerKernel
    - Event routing to MAGNATRIX event bus
    - Health status reporting
    - Constitution validation hooks
    """

    # Commands supported by this skill
    COMMANDS: Dict[str, Dict[str, Any]] = {
        "vps.list": {"api": "vps", "method": "list_vms", "params": ["page", "per_page"]},
        "vps.get": {"api": "vps", "method": "get_vm", "params": ["vm_id"]},
        "vps.create": {"api": "vps", "method": "create_vm", "params": ["plan_id", "os_template_id", "datacenter_id", "hostname", "ssh_key_ids", "labels"]},
        "vps.destroy": {"api": "vps", "method": "destroy_vm", "params": ["vm_id"]},
        "vps.start": {"api": "vps", "method": "start_vm", "params": ["vm_id"]},
        "vps.stop": {"api": "vps", "method": "stop_vm", "params": ["vm_id"]},
        "vps.reboot": {"api": "vps", "method": "reboot_vm", "params": ["vm_id"]},
        "vps.snapshot.create": {"api": "vps", "method": "create_snapshot", "params": ["vm_id", "name"]},
        "vps.snapshot.list": {"api": "vps", "method": "list_snapshots", "params": ["vm_id"]},
        "vps.backup.list": {"api": "vps", "method": "list_backups", "params": ["vm_id"]},
        "vps.firewall.get": {"api": "vps", "method": "get_firewall", "params": ["vm_id"]},
        "vps.ssh.list": {"api": "vps", "method": "list_ssh_keys", "params": ["vm_id"]},
        "domain.check": {"api": "domains", "method": "check_availability", "params": ["domain"]},
        "domain.list": {"api": "domains", "method": "list_portfolio", "params": ["page", "per_page"]},
        "domain.get": {"api": "domains", "method": "get_domain", "params": ["domain"]},
        "domain.whois": {"api": "domains", "method": "get_whois", "params": ["domain"]},
        "dns.get_zone": {"api": "dns", "method": "get_zone", "params": ["domain"]},
        "dns.update_zone": {"api": "dns", "method": "update_zone", "params": ["domain", "records"]},
        "dns.create_record": {"api": "dns", "method": "create_record", "params": ["domain", "record"]},
        "website.list": {"api": "hosting", "method": "list_websites", "params": ["page", "per_page"]},
        "website.get": {"api": "hosting", "method": "get_website", "params": ["website_id"]},
        "billing.subscriptions": {"api": "billing", "method": "list_subscriptions", "params": ["page", "per_page"]},
        "billing.catalog": {"api": "billing", "method": "list_catalog", "params": ["category"]},
        "reach.contacts": {"api": "reach", "method": "list_contacts", "params": ["page", "per_page"]},
        "kernel.sync": {"api": "kernel", "method": "full_sync", "params": []},
    }

    def __init__(
        self,
        orchestrator: Any,
        api_token: Optional[str] = None,
        base_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.api_token = api_token or os.environ.get("HOSTINGER_API_TOKEN")
        self.base_url = base_url or os.environ.get("HOSTINGER_BASE_URL")
        self.webhook_secret = webhook_secret or os.environ.get("HOSTINGER_WEBHOOK_SECRET")
        
        self._kernel: Optional[Any] = None
        self._registered: bool = False
        self._health_interval: int = 60
        self._last_health: float = 0
        
    def _init_kernel(self) -> None:
        """Lazy-init the HostingerKernel."""
        if self._kernel is None:
            from hostinger_api_native import HostingerKernel
            kwargs: Dict[str, Any] = {"api_token": self.api_token}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._kernel = HostingerKernel(**kwargs)
            logger.info("HostingerKernel initialized")

    def validate_constitution(self, task: SkillTask) -> tuple[bool, Optional[str]]:
        """
        Validate task against MAGNATRIX constitution.
        
        Returns (allowed, reason_if_denied).
        """
        # Example: Block destroy operations without explicit confirmation
        if task.command in ("vps.destroy", "domain.delete"):
            return False, "Destructive operations require manual confirmation"
        
        # Example: Limit VM creation rate
        if task.command == "vps.create":
            # Check if too many VMs already exist
            self._init_kernel()
            try:
                vms = self._kernel.vps.list_vms(per_page=1)
                if hasattr(vms, "pagination") and vms.pagination and vms.pagination.total >= 50:
                    return False, "VM limit reached (max 50)"
            except Exception:
                pass
        
        return True, None

    def execute(self, task: SkillTask) -> SkillResult:
        """
        Execute a Hostinger skill task.
        
        Returns SkillResult with data or error.
        """
        start = time.time()
        
        # Constitution check
        allowed, reason = self.validate_constitution(task)
        if not allowed:
            return SkillResult(
                success=False,
                error=f"Constitution blocked: {reason}",
                task_id=task.task_id,
                execution_time_ms=(time.time() - start) * 1000,
            )
        
        # Command dispatch
        spec = self.COMMANDS.get(task.command)
        if not spec:
            return SkillResult(
                success=False,
                error=f"Unknown command: {task.command}",
                task_id=task.task_id,
                execution_time_ms=(time.time() - start) * 1000,
            )
        
        self._init_kernel()
        
        try:
            api_name = spec["api"]
            method_name = spec["method"]
            
            # Get API instance from kernel
            api = getattr(self._kernel, api_name, None)
            if api is None:
                return SkillResult(
                    success=False,
                    error=f"API not found: {api_name}",
                    task_id=task.task_id,
                    execution_time_ms=(time.time() - start) * 1000,
                )
            
            # Get method
            method = getattr(api, method_name, None)
            if method is None:
                return SkillResult(
                    success=False,
                    error=f"Method not found: {method_name}",
                    task_id=task.task_id,
                    execution_time_ms=(time.time() - start) * 1000,
                )
            
            # Build kwargs from task params
            kwargs = {}
            for param in spec["params"]:
                if param in task.params:
                    kwargs[param] = task.params[param]
            
            # Execute
            response = method(**kwargs)
            
            # Extract data from BaseResponse
            data = response.data if hasattr(response, "data") else response
            
            return SkillResult(
                success=True,
                data=data,
                task_id=task.task_id,
                execution_time_ms=(time.time() - start) * 1000,
            )
            
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                task_id=task.task_id,
                execution_time_ms=(time.time() - start) * 1000,
            )

    def register(self) -> "HostingerSkillAdapter":
        """
        Register with MAGNATRIX orchestrator.
        
        Hooks into task bus and event system.
        """
        if self._registered:
            return self
        
        self._init_kernel()
        
        # Register as skill
        if hasattr(self.orchestrator, "register_skill"):
            self.orchestrator.register_skill(
                skill_id="hostinger-api",
                adapter=self,
                capabilities=list(self.COMMANDS.keys()),
            )
            logger.info("Registered with orchestrator skill registry")
        
        # Register event hooks
        if hasattr(self._kernel, "register_hook"):
            self._kernel.register_hook("vm_created", self._on_vm_created)
            self._kernel.register_hook("vm_destroyed", self._on_vm_destroyed)
            self._kernel.register_hook("domain_expiring", self._on_domain_expiring)
        
        self._registered = True
        logger.info("HostingerSkillAdapter registered")
        return self

    def _on_vm_created(self, **kwargs: Any) -> None:
        """Handle VM created event."""
        vm = kwargs.get("vm")
        self._emit_orchestrator_event("hostinger.vm.created", {"vm": vm})

    def _on_vm_destroyed(self, **kwargs: Any) -> None:
        """Handle VM destroyed event."""
        vm_id = kwargs.get("vm_id")
        self._emit_orchestrator_event("hostinger.vm.destroyed", {"vm_id": vm_id})

    def _on_domain_expiring(self, **kwargs: Any) -> None:
        """Handle domain expiring event."""
        self._emit_orchestrator_event("hostinger.domain.expiring", kwargs)

    def _emit_orchestrator_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Emit event to MAGNATRIX orchestrator event bus."""
        if hasattr(self.orchestrator, "emit_event"):
            self.orchestrator.emit_event(event_type, payload)
        logger.info(f"Event emitted: {event_type}")

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.
        
        Returns status dict for orchestrator monitoring.
        """
        self._init_kernel()
        status = {
            "skill": "hostinger-api",
            "registered": self._registered,
            "timestamp": time.time(),
            "api_connected": False,
            "vm_count": 0,
            "domain_count": 0,
            "error": None,
        }
        
        try:
            # Test API connectivity
            profile = self._kernel.reach.get_profile()
            status["api_connected"] = profile.data is not None
        except Exception as e:
            status["error"] = str(e)
        
        try:
            vms = self._kernel.vps.list_vms(per_page=1)
            if vms.pagination:
                status["vm_count"] = vms.pagination.total
        except Exception:
            pass
        
        try:
            domains = self._kernel.domains.list_portfolio(per_page=1)
            if domains.pagination:
                status["domain_count"] = domains.pagination.total
        except Exception:
            pass
        
        self._last_health = time.time()
        return status

    def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Handle incoming webhook from Hostinger.
        
        Routes to appropriate kernel hooks.
        """
        self._init_kernel()
        
        event_map = {
            "vm.created": ("vm_created", {"vm": payload.get("data")}),
            "vm.started": ("vm_started", {"vm_id": payload.get("data", {}).get("id")}),
            "vm.stopped": ("vm_stopped", {"vm_id": payload.get("data", {}).get("id")}),
            "vm.destroyed": ("vm_destroyed", {"vm_id": payload.get("data", {}).get("id")}),
            "domain.expiring": ("domain_expiring", payload.get("data", {})),
            "invoice.paid": (None, None),
            "snapshot.created": (None, None),
        }
        
        hook_name, hook_kwargs = event_map.get(event_type, (None, None))
        
        if hook_name and hasattr(self._kernel, "_emit"):
            self._kernel._emit(hook_name, **hook_kwargs)
            logger.info(f"Webhook routed: {event_type} -> {hook_name}")
        
        # Always emit to orchestrator
        self._emit_orchestrator_event(f"hostinger.{event_type}", payload)

    def __repr__(self) -> str:
        return f"HostingerSkillAdapter(registered={self._registered}, commands={len(self.COMMANDS)})"


# ---------------------------------------------------------------------------
# Demo / Self-Test
# ---------------------------------------------------------------------------

def demo() -> None:
    """Demo the adapter with a mock orchestrator."""
    
    class MockOrchestrator:
        def __init__(self):
            self.skills: Dict[str, Any] = {}
            self.events: List[tuple] = []
        
        def register_skill(self, skill_id: str, adapter: Any, capabilities: List[str]) -> None:
            self.skills[skill_id] = {"adapter": adapter, "capabilities": capabilities}
            print(f"[Orchestrator] Registered skill: {skill_id} with {len(capabilities)} capabilities")
        
        def emit_event(self, event_type: str, payload: Any) -> None:
            self.events.append((event_type, payload))
            print(f"[Orchestrator] Event: {event_type}")
    
    # Create mock orchestrator
    orch = MockOrchestrator()
    
    # Create adapter (without real token, will fail on API calls but shows structure)
    adapter = HostingerSkillAdapter(
        orchestrator=orch,
        api_token="demo-token",
    )
    
    print("=" * 60)
    print("HostingerSkillAdapter Demo")
    print("=" * 60)
    
    # Register
    adapter.register()
    print(f"\nAdapter: {adapter}")
    
    # Test command execution (will fail with demo token but shows flow)
    print("\n[Test] Executing vps.list command...")
    task = SkillTask(
        task_id="test-001",
        command="vps.list",
        params={"page": 1, "per_page": 5},
    )
    result = adapter.execute(task)
    print(f"Result: success={result.success}, error={result.error}, time={result.execution_time_ms:.1f}ms")
    
    # Test constitution block
    print("\n[Test] Constitution check for vps.destroy...")
    task = SkillTask(
        task_id="test-002",
        command="vps.destroy",
        params={"vm_id": 42},
    )
    allowed, reason = adapter.validate_constitution(task)
    print(f"Constitution: allowed={allowed}, reason={reason}")
    
    # Test unknown command
    print("\n[Test] Unknown command handling...")
    task = SkillTask(
        task_id="test-003",
        command="vps.fly",
        params={},
    )
    result = adapter.execute(task)
    print(f"Result: success={result.success}, error={result.error}")
    
    # Health check
    print("\n[Test] Health check...")
    health = adapter.health_check()
    print(f"Health: {json.dumps(health, indent=2, default=str)}")
    
    # Webhook handling
    print("\n[Test] Webhook handling...")
    adapter.handle_webhook("vm.created", {
        "event_id": "evt-001",
        "data": {"id": 1, "name": "demo-vm", "status": "running"}
    })
    
    print("\n" + "=" * 60)
    print(f"Total orchestrator events: {len(orch.events)}")
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    demo()
