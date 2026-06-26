#!/usr/bin/env python3
"""
MAGNATRIX-OS — Master Bootstrap & Entry Point
=============================================
The single command to start the entire AI operating system.

Usage:
    python magnatrix.py start           # Start the full system
    python magnatrix.py status          # Check system status
    python magnatrix.py module list     # List all modules
    python magnatrix.py module on <name> # Enable a module
    python magnatrix.py config get      # Get configuration
    python magnatrix.py config set <k> <v> # Set config
    python magnatrix.py doc ingest <file> # Ingest a document
    python magnatrix.py backup          # Create backup
    python magnatrix.py update          # Check for updates
    python magnatrix.py stop            # Graceful shutdown

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable


@dataclass
class ModuleInfo:
    """Runtime info for a loaded module."""
    name: str
    path: str
    class_name: str
    instance: Any = None
    state: str = "pending"  # pending, loading, active, error, disabled
    error: Optional[str] = None
    load_time_ms: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)


class ModuleRegistry:
    """Central registry for all MAGNATRIX-OS modules."""

    CORE_MODULES = [
        # --- Infrastructure Layer ---
        ("config", "core.config_manager_native", "ConfigManager"),
        ("logging", "core.logging_engine_native", "LoggingEngine"),
        ("cache", "core.cache_engine_native", "CacheEngine"),
        ("rate_limiter", "core.rate_limiter_native", "RateLimiter"),
        ("secrets", "core.secrets_vault_native", "SecretsVault"),
        ("auth", "core.auth_engine_native", "AuthEngine"),
        ("session", "core.session_manager_native", "SessionManager"),
        ("backup", "core.backup_recovery_native", "BackupRecovery"),
        ("schema", "core.schema_validator_native", "SchemaValidator"),
        ("i18n", "core.i18n_engine_native", "I18nEngine"),
        ("test", "core.test_framework_native", "TestFramework"),
        ("docgen", "core.doc_generator_native", "DocGenerator"),
        # --- System Layer ---
        ("monitor", "core.resource_monitor_native", "ResourceMonitor"),
        ("health", "core.health_check_aggregator_native", "HealthCheckAggregator"),
        ("metrics", "core.metrics_health_native", "MetricsHealth"),
        ("event_bus", "core.event_bus_native", "EventBus"),
        ("event_streaming", "core.event_streaming_native", "EventStreaming"),
        ("workflow", "core.workflow_engine_native", "WorkflowEngine"),
        ("cicd", "core.cicd_pipeline_native", "CICDPipeline"),
        ("audit", "core.code_audit_engine_native", "CodeAuditEngine"),
        ("security", "core.security_audit_framework_native", "SecurityAuditFramework"),
        # --- Data Layer ---
        ("database", "core.database_abstraction_native", "DatabaseAbstraction"),
        ("data_lineage", "core.data_lineage_native", "DataLineage"),
        ("knowledge_graph", "core.knowledge_graph_engine_native", "KnowledgeGraphEngine"),
        ("rag", "core.advanced_rag_pipeline_native", "AdvancedRAGPipeline"),
        ("memory", "core.memory_learning_system_native", "MemoryLearningSystem"),
        # --- AI/LLM Layer ---
        ("model_catalog", "core.model_catalog_native", "ModelCatalog"),
        ("hardware", "core.hardware_profiler_native", "HardwareProfiler"),
        ("llm", "core.local_llm_manager_native", "LocalLLMManager"),
        ("multi_model", "core.multi_model_llm_adapter_native", "MultiModelLLMAdapter"),
        ("prompt_vc", "core.prompt_version_control_native", "PromptVersionControl"),
        ("ab_testing", "core.model_ab_testing_native", "ModelABTesting"),
        ("cost", "core.cost_tracker_native", "CostTracker"),
        ("prompt_guard", "core.prompt_injection_guard_native", "PromptInjectionGuard"),
        # --- Agent Layer ---
        ("agent_router", "core.multi_agent_router_native", "MultiAgentRouter"),
        ("agent_collab", "core.multi_agent_collaboration_native", "MultiAgentCollaboration"),
        ("agent_connector", "core.agent_connector_native", "AgentConnector"),
        ("agent_attribution", "core.agent_attribution_native", "AgentAttribution"),
        ("plugin", "core.plugin_system_native", "PluginSystem"),
        ("plugin_market", "core.agent_plugin_marketplace_native", "AgentPluginMarketplace"),
        # --- Communication Layer ---
        ("mesh", "core.distributed_mesh_engine_native", "DistributedMeshEngine"),
        ("message_queue", "core.message_queue_router_native", "MessageQueueRouter"),
        ("task_queue", "core.task_queue_scheduler_native", "TaskQueueScheduler"),
        ("http_client", "core.http_client_native", "HttpClient"),
        ("email", "core.email_client_native", "EmailClient"),
        ("voice", "core.voice_audio_pipeline_native", "VoiceAudioPipeline"),
        # --- Web Layer ---
        ("web_api", "core.web_api_gateway_native", "WebAPIGateway"),
        ("web_dashboard", "core.web_dashboard_server_native", "DashboardServer"),
        ("dashboard_fe", "core.dashboard_frontend_native", "DashboardManager"),
        ("pwa", "core.pwa_desktop_wrapper_native", "PWADesktopManager"),
        ("doc_intel", "core.document_intelligence_native", "DocumentIntelligence"),
        # --- GENesis Layer ---
        ("ego", "core.ego_engine_native", "EgoEngine"),
        ("awareness", "core.awareness_engine_native", "AwarenessEngine"),
        ("autonomy", "core.autonomy_engine_native", "AutonomyEngine"),
        ("guardian", "core.guardian_native", "Guardian"),
        ("content", "core.content_engine_native", "ContentEngine"),
        ("outreach", "core.outreach_engine_native", "OutreachEngine"),
        ("distribution", "core.distribution_engine_native", "DistributionEngine"),
        ("learning", "core.learning_engine_native", "LearningEngine"),
        ("follow_up", "core.follow_up_engine_native", "FollowUpEngine"),
        ("genesis_hub", "core.genesis_integration_hub_native", "GenesisIntegrationHub"),
        # --- Deployment Layer ---
        ("deployment", "core.auto_deployment_native", "AutoDeploymentManager"),
        ("graphql", "core.graphql_engine_native", "GraphQLServer"),
        ("ai_training", "core.ai_training_pipeline_native", "AITrainingPipeline"),
        ("nlq", "core.nlq_engine_native", "NLQEngine"),
        ("analytics", "core.analytics_engine_native", "AnalyticsEngine"),
        ("model_registry", "core.ai_model_registry_native", "ModelRegistry"),
        ("search", "core.search_engine_native", "SearchEngine"),
    ]

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self._modules: Dict[str, ModuleInfo] = {}
        self._running = False
        self._lock = threading.RLock()
        self._hooks: Dict[str, List[Callable]] = {"pre_boot": [], "post_boot": [], "pre_shutdown": [], "post_shutdown": []}
        self._sys_path_inserted = False

    def _ensure_path(self) -> None:
        if not self._sys_path_inserted:
            sys.path.insert(0, str(self.root))
            self._sys_path_inserted = True

    def _load_module(self, name: str, mod_path: str, cls_name: str) -> Optional[Any]:
        """Try to load a module and instantiate its class."""
        try:
            self._ensure_path()
            mod = importlib.import_module(mod_path)
            cls = getattr(mod, cls_name)
            # Try to instantiate with reasonable args
            sig_args = {}
            try:
                import inspect
                sig = inspect.signature(cls.__init__)
                if "repo_root" in sig.parameters or "root" in sig.parameters:
                    sig_args["repo_root"] = str(self.root)
                if "store_dir" in sig.parameters:
                    sig_args["store_dir"] = str(self.root / "data" / name)
            except Exception:
                pass
            instance = cls(**sig_args) if sig_args else cls()
            return instance
        except Exception as e:
            return None

    def boot(self, target_modules: Optional[List[str]] = None) -> Dict[str, Any]:
        """Boot all or selected modules."""
        with self._lock:
            self._running = True
            start_all = time.time()
            results = {"loaded": 0, "failed": 0, "skipped": 0, "total": len(self.CORE_MODULES), "details": []}

            for hook in self._hooks["pre_boot"]:
                try:
                    hook()
                except Exception:
                    pass

            for name, mod_path, cls_name in self.CORE_MODULES:
                if target_modules and name not in target_modules:
                    results["skipped"] += 1
                    continue
                info = ModuleInfo(name=name, path=mod_path, class_name=cls_name)
                info.state = "loading"
                t0 = time.time()
                instance = self._load_module(name, mod_path, cls_name)
                info.load_time_ms = (time.time() - t0) * 1000
                if instance is not None:
                    info.instance = instance
                    info.state = "active"
                    info.provides = [name]
                    results["loaded"] += 1
                else:
                    info.state = "error"
                    info.error = "Failed to load"
                    results["failed"] += 1
                self._modules[name] = info
                results["details"].append({
                    "name": name, "state": info.state, "load_ms": round(info.load_time_ms, 1),
                    "error": info.error,
                })

            total_ms = (time.time() - start_all) * 1000
            results["boot_time_ms"] = round(total_ms, 1)

            for hook in self._hooks["post_boot"]:
                try:
                    hook()
                except Exception:
                    pass

            return results

    def shutdown(self) -> Dict[str, Any]:
        """Graceful shutdown of all modules."""
        with self._lock:
            self._running = False
            results = {"shutdown": 0, "errors": 0}

            for hook in self._hooks["pre_shutdown"]:
                try:
                    hook()
                except Exception:
                    pass

            for name, info in reversed(list(self._modules.items())):
                if info.instance and hasattr(info.instance, "stop"):
                    try:
                        info.instance.stop()
                        results["shutdown"] += 1
                    except Exception:
                        results["errors"] += 1
                info.state = "disabled"
                info.instance = None

            for hook in self._hooks["post_shutdown"]:
                try:
                    hook()
                except Exception:
                    pass

            return results

    def get_module(self, name: str) -> Optional[Any]:
        with self._lock:
            info = self._modules.get(name)
            return info.instance if info else None

    def get_status(self, name: str) -> Dict[str, Any]:
        with self._lock:
            info = self._modules.get(name)
            if not info:
                return {"name": name, "state": "unknown"}
            return {
                "name": info.name, "state": info.state, "path": info.path,
                "class": info.class_name, "load_ms": round(info.load_time_ms, 1),
                "error": info.error, "provides": info.provides,
            }

    def list_modules(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self.get_status(name) for name in self._modules]

    def active_modules(self) -> List[str]:
        with self._lock:
            return [n for n, i in self._modules.items() if i.state == "active"]

    def register_hook(self, event: str, callback: Callable) -> None:
        self._hooks.setdefault(event, []).append(callback)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            states = {}
            for i in self._modules.values():
                states[i.state] = states.get(i.state, 0) + 1
            return {
                "total_registered": len(self.CORE_MODULES),
                "loaded": len([i for i in self._modules.values() if i.state == "active"]),
                "failed": len([i for i in self._modules.values() if i.state == "error"]),
                "states": states,
                "running": self._running,
            }


class SystemManager:
    """High-level system manager combining all modules."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self.registry = ModuleRegistry(repo_root)
        self._dashboard_server: Optional[Any] = None
        self._genesis_hub: Optional[Any] = None
        self._doc_intel: Optional[Any] = None
        self._deployment: Optional[Any] = None
        self._pwa: Optional[Any] = None
        self._shutdown_event = threading.Event()

    def boot(self, quick: bool = False) -> Dict[str, Any]:
        """Boot the full system."""
        print("=" * 60)
        print("  MAGNATRIX-OS Boot Sequence")
        print("  Private, Uncensored AI Operating System")
        print("=" * 60)

        # Boot core modules first
        if quick:
            # Only boot essential modules
            essential = ["config", "logging", "cache", "auth", "monitor", "event_bus", "web_dashboard", "dashboard_fe"]
            result = self.registry.boot(essential)
        else:
            result = self.registry.boot()

        print(f"\n  Modules loaded: {result['loaded']}/{result['total']}")
        print(f"  Failed: {result['failed']}")
        print(f"  Boot time: {result['boot_time_ms']}ms")

        # Wire key services
        self._wire_services()

        # Start dashboard server if available
        self._start_dashboard()

        print(f"\n  System ready at: http://0.0.0.0:8080")
        print("=" * 60)

        return result

    def _wire_services(self) -> None:
        """Wire key services together."""
        try:
            # Wire genesis hub
            hub = self.registry.get_module("genesis_hub")
            if hub:
                self._genesis_hub = hub
                print("  [Wired] Genesis Integration Hub")
        except Exception as e:
            print(f"  [Skip] Genesis Hub: {e}")

        try:
            # Wire document intelligence
            di = self.registry.get_module("doc_intel")
            if di:
                self._doc_intel = di
                print("  [Wired] Document Intelligence")
        except Exception as e:
            print(f"  [Skip] Document Intelligence: {e}")

        try:
            # Wire deployment
            dep = self.registry.get_module("deployment")
            if dep:
                self._deployment = dep
                print("  [Wired] Auto-Deployment")
        except Exception as e:
            print(f"  [Skip] Auto-Deployment: {e}")

        try:
            # Wire PWA manager
            pwa = self.registry.get_module("pwa")
            if pwa:
                self._pwa = pwa
                # Inject PWA into dashboard
                dashboard_path = self.root / "core" / "dashboard.html"
                if dashboard_path.exists():
                    pwa.inject_pwa_into_dashboard(str(dashboard_path))
                    print("  [Wired] PWA assets injected into dashboard")
        except Exception as e:
            print(f"  [Skip] PWA: {e}")

    def _start_dashboard(self) -> None:
        """Start the web dashboard server."""
        try:
            web = self.registry.get_module("web_dashboard")
            if web and hasattr(web, "start"):
                web.start(blocking=False)
                self._dashboard_server = web
                print(f"  [Started] Dashboard server at http://0.0.0.0:8080")
        except Exception as e:
            print(f"  [Skip] Dashboard server: {e}")

    def shutdown(self) -> None:
        """Graceful shutdown."""
        print("\n  MAGNATRIX-OS shutting down...")
        if self._dashboard_server and hasattr(self._dashboard_server, "stop"):
            try:
                self._dashboard_server.stop()
            except Exception:
                pass
        result = self.registry.shutdown()
        print(f"  Shutdown: {result['shutdown']} modules stopped")
        self._shutdown_event.set()

    def status(self) -> Dict[str, Any]:
        return {
            "registry": self.registry.stats(),
            "dashboard_running": self._dashboard_server is not None,
            "genesis_hub": self._genesis_hub is not None,
            "doc_intel": self._doc_intel is not None,
            "root": str(self.root),
        }

    def wait(self) -> None:
        """Block until shutdown signal."""
        try:
            while not self._shutdown_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()


def _cli() -> None:
    """Command-line interface."""
    parser = argparse.ArgumentParser(description="MAGNATRIX-OS — Private AI Operating System")
    sub = parser.add_subparsers(dest="command")

    # start
    start_p = sub.add_parser("start", help="Start the full system")
    start_p.add_argument("--quick", action="store_true", help="Quick boot (essential modules only)")
    start_p.add_argument("--port", type=int, default=8080, help="Dashboard port")

    # status
    sub.add_parser("status", help="Check system status")

    # module
    mod_p = sub.add_parser("module", help="Module management")
    mod_sub = mod_p.add_subparsers(dest="mod_cmd")
    mod_sub.add_parser("list", help="List all modules")
    mod_sub.add_parser("on", help="Enable a module")
    mod_sub.add_parser("off", help="Disable a module")

    # config
    cfg_p = sub.add_parser("config", help="Configuration management")
    cfg_sub = cfg_p.add_subparsers(dest="cfg_cmd")
    cfg_sub.add_parser("get", help="Get configuration")
    cfg_sub.add_parser("set", help="Set configuration value")

    # doc
    doc_p = sub.add_parser("doc", help="Document management")
    doc_sub = doc_p.add_subparsers(dest="doc_cmd")
    doc_ingest = doc_sub.add_parser("ingest", help="Ingest a document")
    doc_ingest.add_argument("file", help="Path to document file")

    # backup
    sub.add_parser("backup", help="Create system backup")

    # update
    sub.add_parser("update", help="Check for updates")

    # stop
    sub.add_parser("stop", help="Stop the system")

    args = parser.parse_args()
    repo_root = Path(__file__).parent.resolve()
    sys.path.insert(0, str(repo_root))

    if args.command == "start":
        manager = SystemManager(repo_root)
        manager.boot(quick=args.quick)
        manager.wait()

    elif args.command == "status":
        manager = SystemManager(repo_root)
        status = manager.status()
        print(json.dumps(status, indent=2, ensure_ascii=False))

    elif args.command == "module":
        manager = SystemManager(repo_root)
        manager.boot(quick=True)
        if args.mod_cmd == "list":
            for m in manager.registry.list_modules():
                icon = "✓" if m["state"] == "active" else "✗" if m["state"] == "error" else "○"
                print(f"  {icon} {m['name']:20s} {m['state']:10s} {m.get('load_ms', 0)}ms")
        else:
            print(f"Module command: {args.mod_cmd}")

    elif args.command == "config":
        print(f"Config: {args.cfg_cmd}")

    elif args.command == "doc":
        if args.doc_cmd == "ingest":
            manager = SystemManager(repo_root)
            manager.boot(quick=True)
            di = manager.registry.get_module("doc_intel")
            if di and hasattr(di, "ingest_file"):
                result = di.ingest_file(args.file)
                print(f"Ingested: {result.source} -> {result.chunks} chunks, {result.chars} chars")
            else:
                print("Document intelligence module not available")

    elif args.command == "backup":
        manager = SystemManager(repo_root)
        manager.boot(quick=True)
        backup = manager.registry.get_module("backup")
        if backup and hasattr(backup, "backup"):
            path = backup.backup(str(repo_root))
            print(f"Backup created: {path}")
        else:
            print("Backup module not available")

    elif args.command == "update":
        manager = SystemManager(repo_root)
        manager.boot(quick=True)
        dep = manager.registry.get_module("deployment")
        if dep and hasattr(dep, "check_update"):
            result = dep.check_update()
            print(f"Current: {result['current']}")
            print(f"Latest: {result.get('latest', 'Unknown')}")
            print(f"Update available: {result.get('update_available', False)}")
        else:
            print("Deployment module not available")

    elif args.command == "stop":
        print("Send SIGTERM to the running process to shutdown gracefully.")

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
