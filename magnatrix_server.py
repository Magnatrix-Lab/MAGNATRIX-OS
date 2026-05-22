"""
MAGNATRIX Agentic OS — Main Server Entry Point
════════════════════════════════════════════════

Bootstraps Kernel Engine → starts all layers → serves FastAPI + gRPC + WebSocket.

Usage:
    python magnatrix_server.py
    python magnatrix_server.py --config magnatrix.toml
    python magnatrix_server.py --host 0.0.0.0 --port 8080

Environment:
    MAGNATRIX_ENV=production|development
    MAGNATRIX_CONFIG_PATH=magnatrix.toml
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from kernel.kernel_engine import KernelEngine, ServiceDescriptor, ServiceState


async def main():
    parser = argparse.ArgumentParser(description="MAGNATRIX Agentic OS Server")
    parser.add_argument("--config", default="magnatrix.toml", help="Config file path")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port")
    parser.add_argument("--grpc-port", type=int, default=50051, help="gRPC port")
    parser.add_argument("--ws-port", type=int, default=50052, help="WebSocket port")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    print(r"""
    ███╗   ███╗ █████╗  ██████╗ ███╗   ██╗ █████╗ ████████╗██████╗ ██╗██╗  ██╗
    ████╗ ████║██╔══██╗██╔════╝ ████╗  ██║██╔══██╗╚══██╔══╝██╔══██╗██║╚██╗██╔╝
    ██╔████╔██║███████║██║  ███╗██╔██╗ ██║███████║   ██║   ██████╔╝██║ ╚███╔╝ 
    ██║╚██╔╝██║██╔══██║██║   ██║██║╚██╗██║██╔══██║   ██║   ██╔══██╗██║ ██╔██╗ 
    ██║ ╚═╝ ██║██║  ██║╚██████╔╝██║ ╚████║██║  ██║   ██║   ██║  ██║██║██╔╝ ██╗
    ╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝
    Agentic OS → AGI → Super AI
    """)

    kernel = KernelEngine(config_path=args.config)

    # Register all core services
    services = [
        ServiceDescriptor(
            name="protocol",
            module_path="protocol.protocol_layer",
            class_name="ProtocolServer",
            critical=True,
            depends_on=[],
        ),
        ServiceDescriptor(
            name="identity",
            module_path="identity.identity_manager",
            class_name="IdentityManager",
            depends_on=["protocol"],
        ),
        ServiceDescriptor(
            name="knowledge",
            module_path="knowledge.knowledge_graph",
            class_name="KnowledgeGraph",
            depends_on=["identity"],
        ),
        ServiceDescriptor(
            name="browser",
            module_path="browser.browser_layer",
            class_name="BrowserLayer",
            depends_on=["protocol"],
        ),
        ServiceDescriptor(
            name="trading",
            module_path="trading.ai_trader",
            class_name="AITrader",
            depends_on=["identity", "knowledge"],
        ),
        ServiceDescriptor(
            name="runtime",
            module_path="runtime.n8n_native_runtime",
            class_name="N8NNativeRuntime",
            depends_on=["protocol"],
        ),
        ServiceDescriptor(
            name="p2p",
            module_path="p2p_mesh.global_mesh",
            class_name="GlobalMesh",
            depends_on=["protocol"],
        ),
        ServiceDescriptor(
            name="security",
            module_path="security.native_engines",
            class_name="SecurityEngine",
            depends_on=["identity"],
        ),
        ServiceDescriptor(
            name="uncensored",
            module_path="uncensored.native_engines",
            class_name="UncensoredEngine",
            depends_on=["identity"],
        ),
        ServiceDescriptor(
            name="governance",
            module_path="governance.enforcement.runtime_enforcer",
            class_name="ConstitutionalMonitor",
            depends_on=["identity", "security"],
        ),
        ServiceDescriptor(
            name="collective_brain",
            module_path="collective_brain.agents.agent_zero_native",
            class_name="AgentZeroCore",
            critical=True,
            depends_on=["protocol", "identity", "knowledge", "browser"],
        ),
    ]

    for svc in services:
        kernel.register_service(svc)

    # Start
    await kernel.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Server] Interrupted by user")
        sys.exit(0)
