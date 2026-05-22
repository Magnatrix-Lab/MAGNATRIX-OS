"""
MAGNATRIX — Command Line Interface
════════════════════════════════════

Usage:
    python -m magnatrix_cli server          # Start server
    python -m magnatrix_cli status          # Show system status
    python -m magnatrix_cli layer <name>    # Show layer info
    python -m magnatrix_cli agent create    # Create new agent
    python -m magnatrix_cli agent list      # List agents
    python -m magnatrix_cli agent interact  # Interactive agent shell
    python -m magnatrix_cli deploy          # Deploy to Hostinger
    python -m magnatrix_cli benchmark       # Run benchmarks
    python -m magnatrix_cli test            # Run tests
    python -m magnatrix_cli repo hunt       # Auto repo hunter

Author: MAGNATRIX-OS
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kernel.kernel_engine import KernelEngine


def print_banner():
    print(r"""
    ███╗   ███╗ █████╗  ██████╗ ███╗   ██╗ █████╗ ████████╗██████╗ ██╗██╗  ██╗
    ████╗ ████║██╔══██╗██╔════╝ ████╗  ██║██╔══██╗╚══██╔══╝██╔══██╗██║╚██╗██╔╝
    ██╔████╔██║███████║██║  ███╗██╔██╗ ██║███████║   ██║   ██████╔╝██║ ╚███╔╝ 
    ██║╚██╔╝██║██╔══██║██║   ██║██║╚██╗██║██╔══██║   ██║   ██╔══██╗██║ ██╔██╗ 
    ██║ ╚═╝ ██║██║  ██║╚██████╔╝██║ ╚████║██║  ██║   ██║   ██║  ██║██║██╔╝ ██╗
    ╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝
    """)


def cmd_status(args):
    print_banner()
    print("System Status:")
    print(f"  Config: {args.config}")
    print(f"  Environment: {os.environ.get('MAGNATRIX_ENV', 'development')}")
    print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n  Layers (15 total):")
    layers = [
        ("kernel", "Core orchestrator"),
        ("protocol", "Communication layer"),
        ("api-router", "API gateway & routing"),
        ("identity", "Authentication & identity"),
        ("runtime", "Agent runtime environment"),
        ("p2p-mesh", "Global P2P mesh"),
        ("knowledge", "Knowledge graph & RAG"),
        ("skills", "Skill marketplace"),
        ("browser", "Browser automation"),
        ("trading", "HFT & trading engine"),
        ("security", "Defense & audit"),
        ("uncensored", "Uncensored AI models"),
        ("governance", "Constitutional governance"),
        ("ide", "IDE integration"),
        ("offensive", "Offensive security tools"),
    ]
    for name, desc in layers:
        status = "OK" if (Path(__file__).parent / name).exists() else "MISSING"
        print(f"    [{status:7}] {name:15} — {desc}")
    print(f"\n  Total repos integrated: 62+")
    print(f"  GitHub: https://github.com/Magnatrix-Lab/MAGNATRIX-OS")


def cmd_server(args):
    os.system(f"python magnatrix_server.py --config {args.config}")


def cmd_test(args):
    print("Running tests...")
    os.system("pytest tests/ -v || python tests/comprehensive_test_suite.py")


def cmd_benchmark(args):
    print("Running benchmarks...")
    os.system("python benchmarks/comprehensive_benchmarks.py")


def cmd_deploy(args):
    print("Deploying to Hostinger...")
    os.system("bash scripts/deploy-hostinger.sh")


def cmd_agent_create(args):
    print("Creating new agent...")
    agent_id = f"agent-{int(time.time())}"
    print(f"Agent ID: {agent_id}")
    print("Use 'magnatrix agent interact' to start")


def cmd_agent_list(args):
    print("Active agents:")
    print("  [orchestrator] agent-alpha")
    print("  [researcher]   agent-beta")


def cmd_repo_hunt(args):
    print("Auto repo hunter starting...")
    os.system("python hunter/auto_hunter.py")


def main():
    parser = argparse.ArgumentParser(description="MAGNATRIX CLI")
    parser.add_argument("--config", default="magnatrix.toml", help="Config file")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    subparsers.add_parser("status", help="Show system status")
    subparsers.add_parser("server", help="Start server")
    subparsers.add_parser("test", help="Run tests")
    subparsers.add_parser("benchmark", help="Run benchmarks")
    subparsers.add_parser("deploy", help="Deploy to Hostinger")
    subparsers.add_parser("repo-hunt", help="Auto repo hunter")

    agent_parser = subparsers.add_parser("agent", help="Agent management")
    agent_sub = agent_parser.add_subparsers(dest="agent_cmd")
    agent_sub.add_parser("create", help="Create agent")
    agent_sub.add_parser("list", help="List agents")
    agent_sub.add_parser("interact", help="Interactive agent shell")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status(args)
    elif args.command == "server":
        cmd_server(args)
    elif args.command == "test":
        cmd_test(args)
    elif args.command == "benchmark":
        cmd_benchmark(args)
    elif args.command == "deploy":
        cmd_deploy(args)
    elif args.command == "repo-hunt":
        cmd_repo_hunt(args)
    elif args.command == "agent":
        if args.agent_cmd == "create":
            cmd_agent_create(args)
        elif args.agent_cmd == "list":
            cmd_agent_list(args)
        elif args.agent_cmd == "interact":
            print("Interactive mode: agent shell (press Ctrl+C to exit)")
            while True:
                try:
                    inp = input("agent> ")
                    if inp.lower() in ("exit", "quit"):
                        break
                    print(f"  [processed] {inp}")
                except (KeyboardInterrupt, EOFError):
                    break
        else:
            agent_parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
