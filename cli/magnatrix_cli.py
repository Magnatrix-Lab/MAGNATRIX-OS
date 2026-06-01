#!/usr/bin/env python3
"""
magnatrix_cli.py — MAGNATRIX Unified CLI
Command-line interface untuk mengontrol seluruh MAGNATRIX Agentic OS.
Fitur: status, swarm, trading, knowledge, governance, evolve, chat, emergency.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional


API_URL = os.environ.get("MAGNATRIX_API", "http://localhost:8080")

def _api_get(endpoint: str) -> Dict:
    import urllib.request
    try:
        url = f"{API_URL}{endpoint}"
        req = urllib.request.Request(url, method="GET")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def _api_post(endpoint: str, payload: Dict) -> Dict:
    import urllib.request
    try:
        url = f"{API_URL}{endpoint}"
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def _print_table(headers: List[str], rows: List[List]):
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    sep = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    print(sep)
    header_row = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    print(header_row)
    print(sep)
    for row in rows:
        print("| " + " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)) + " |")
    print(sep)

def cmd_status(args):
    """Tampilkan status sistem MAGNATRIX."""
    print("=" * 70)
    print("🧠  MAGNATRIX Agentic OS — System Status")
    print("=" * 70)
    
    health = _api_get("/health")
    status = _api_get("/api/v2/status")
    
    if "error" in health:
        print(f"\n⚠️  API tidak tersedia di {API_URL}")
        print(f"   Error: {health['error']}")
        print(f"\n   Coba jalankan: python scripts/magnatrix_boot.py --start")
        return
    
    print(f"\n🟢 API Status    : {health.get('status', 'unknown').upper()}")
    print(f"⏱️  Uptime        : {health.get('uptime_seconds', 0)} detik")
    print(f"📦 Version       : {health.get('version', 'unknown')}")
    print(f"🕐 Timestamp     : {health.get('timestamp', 'N/A')}")
    
    if "layers" in status:
        print(f"\n{'Layer':<8} {'Name':<20} {'Status':<10}")
        print("-" * 40)
        for layer in status["layers"]:
            icon = "🟢" if layer.get("status") == "active" else "🔴"
            print(f"  {layer.get('layer', '?'):<6} {layer.get('name', '?'):<20} {icon} {layer.get('status', '?'):<10}")
    
    print(f"\n🔄 Cycle Count   : {status.get('cycle_count', 0)}")
    print(f"🚨 Emergency     : {'YES' if status.get('emergency_mode') else 'NO'}")
    print("=" * 70)

def cmd_swarm(args):
    """Kelola swarm nodes."""
    if args.swarm_cmd == "list":
        nodes = _api_get("/api/v2/swarm/nodes")
        print("=" * 70)
        print("🐝  MAGNATRIX Swarm Nodes")
        print("=" * 70)
        if isinstance(nodes, list):
            _print_table(
                ["Node ID", "Type", "Health", "Load"],
                [[n.get("node_id"), n.get("type"), f"{n.get('health', 0):.2f}", f"{n.get('load', 0):.2f}"] for n in nodes]
            )
        else:
            print(f"\n⚠️  {nodes.get('error', 'Unknown error')}")
        print("=" * 70)
    
    elif args.swarm_cmd == "spawn":
        count = args.count or 1
        brain = args.brain or "hermes"
        result = _api_post("/api/v2/swarm/spawn", {"brain_type": brain, "count": count})
        print("=" * 70)
        print(f"🆕  Spawn Nodes: {count}x {brain}")
        print("=" * 70)
        if "error" in result:
            print(f"\n⚠️  {result['error']}")
        else:
            print(f"\n✅ Spawned : {result.get('spawned', 0)} node(s)")
            for nid in result.get("node_ids", []):
                print(f"   → {nid}")
        print("=" * 70)
    
    elif args.swarm_cmd == "kill":
        print("=" * 70)
        print(f"💀  Kill Node: {args.node_id}")
        print("=" * 70)
        print("\n⚠️  Feature: Implement node termination logic")
        print("=" * 70)

def cmd_trading(args):
    """Kelola trading engine."""
    if args.trading_cmd == "status":
        result = _api_get("/api/v2/trading/status")
        print("=" * 70)
        print("💰  MAGNATRIX Trading Engine")
        print("=" * 70)
        if "error" in result:
            print(f"\n⚠️  {result['error']}")
        else:
            print(f"\n📊 Mode           : {result.get('mode', 'N/A').upper()}")
            print(f"💵 NAV            : ${result.get('nav', 0):,.2f}")
            print(f"📈 Daily P&L      : ${result.get('daily_pnl', 0):,.2f}")
            print(f"📋 Positions      : {result.get('positions', 0)}")
            print(f"🔄 Reinvestment   : {result.get('reinvestment_rate', 0)*100:.0f}%")
        print("=" * 70)
    
    elif args.trading_cmd == "execute":
        result = _api_post("/api/v2/trading/execute", {
            "symbol": args.symbol,
            "side": args.side,
            "amount": args.amount
        })
        print("=" * 70)
        print(f"🚀  Execute Trade: {args.side.upper()} {args.amount} {args.symbol}")
        print("=" * 70)
        if "error" in result:
            print(f"\n⚠️  {result['error']}")
        else:
            print(f"\n✅ Status  : {result.get('status', 'N/A')}")
            print(f"📊 New NAV : ${result.get('new_nav', 0):,.2f}")
        print("=" * 70)

def cmd_knowledge(args):
    """Query knowledge graph."""
    result = _api_post("/api/v2/knowledge/query", {
        "entity": args.entity,
        "depth": args.depth or 2
    })
    print("=" * 70)
    print(f"🧠  Knowledge Graph Query: '{args.entity}'")
    print("=" * 70)
    if "error" in result:
        print(f"\n⚠️  {result['error']}")
    else:
        print(f"\n📌 Entity   : {result.get('entity', 'N/A')}")
        print(f"🔍 Depth    : {result.get('depth', 0)}")
        print(f"🔗 Related  : {', '.join(result.get('related', []))}")
        if result.get("paths"):
            print(f"\n📍 Paths:")
            for path in result["paths"]:
                print(f"   {' → '.join(path)}")
    print("=" * 70)

def cmd_governance(args):
    """Kelola governance dan constitution."""
    if args.gov_cmd == "constitution":
        result = _api_get("/api/v2/governance/constitution")
        print("=" * 70)
        print("⚖️   MAGNATRIX Constitution")
        print("=" * 70)
        if "error" in result:
            print(f"\n⚠️  {result['error']}")
        else:
            for rule in result.get("rules", []):
                print(f"\n📜 [{rule.get('id', '?')}]")
                print(f"   Weight : {rule.get('weight', 0)}")
                print(f"   Text   : {rule.get('text', 'N/A')}")
        print("=" * 70)
    
    elif args.gov_cmd == "goals":
        result = _api_get("/api/v2/governance/goals")
        print("=" * 70)
        print("🎯  Active Goals")
        print("=" * 70)
        if "error" in result:
            print(f"\n⚠️  {result['error']}")
        else:
            for goal in result.get("active_goals", []):
                print(f"\n🎯 {goal.get('title', 'N/A')}")
                print(f"   ID      : {goal.get('id', 'N/A')}")
                print(f"   Priority: {goal.get('priority', 0)}")
                print(f"   Status  : {goal.get('status', 'N/A')}")
        print("=" * 70)

def cmd_evolve(args):
    """Trigger self-evolution."""
    result = _api_post("/api/v2/evolve/trigger", {})
    print("=" * 70)
    print("🧬  MAGNATRIX Self-Evolution")
    print("=" * 70)
    if "error" in result:
        print(f"\n⚠️  {result['error']}")
    else:
        print(f"\n✅ Cycle Triggered : {result.get('cycle_id', 'N/A')}")
        print(f"📊 Status          : {result.get('status', 'N/A')}")
        if result.get("improvements"):
            print(f"\n🔧 Improvements:")
            for imp in result["improvements"]:
                print(f"   → {imp}")
    print("=" * 70)

def cmd_emergency(args):
    """Emergency stop."""
    print("=" * 70)
    print("🚨  EMERGENCY STOP")
    print("=" * 70)
    confirm = input("\n⚠️  Yakin hentikan SEMUA service? [yes/no]: ")
    if confirm.lower() == "yes":
        result = _api_post("/api/v2/emergency", {"action": "stop"})
        print("\n🔴 SEMUA SERVICE DIHENTIKAN")
        print(f"   Timestamp: {datetime.now(timezone.utc).isoformat()}")
    else:
        print("\n❌ Dibatalkan")
    print("=" * 70)

def cmd_chat(args):
    """Buka chat client."""
    print("=" * 70)
    print("💬  MAGNATRIX Chat Bridge")
    print("=" * 70)
    print("\nMenjalankan chat client...")
    script_path = os.path.join(os.path.dirname(__file__), "../chat-bridge/chat_client.py")
    if os.path.isfile(script_path):
        subprocess.run([sys.executable, script_path])
    else:
        print("⚠️  Chat client tidak ditemukan")
    print("=" * 70)

def cmd_boot(args):
    """Boot atau shutdown MAGNATRIX."""
    script_path = os.path.join(os.path.dirname(__file__), "magnatrix_boot.py")
    if args.boot_cmd == "start":
        print("=" * 70)
        print("🚀  Starting MAGNATRIX...")
        print("=" * 70)
        if os.path.isfile(script_path):
            subprocess.Popen([sys.executable, script_path, "--start"])
            print("\n✅ Boot script dijalankan")
            print(f"   Dashboard: http://localhost:8095")
            print(f"   API      : http://localhost:8080")
        else:
            print(f"\n⚠️  Boot script tidak ditemukan: {script_path}")
    elif args.boot_cmd == "stop":
        print("=" * 70)
        print("🛑  Stopping MAGNATRIX...")
        print("=" * 70)
        if os.path.isfile(script_path):
            subprocess.run([sys.executable, script_path, "--stop"])
        print("\n✅ Stop command executed")
    elif args.boot_cmd == "restart":
        print("=" * 70)
        print("🔄  Restarting MAGNATRIX...")
        print("=" * 70)
        if os.path.isfile(script_path):
            subprocess.run([sys.executable, script_path, "--stop"])
            time.sleep(2)
            subprocess.Popen([sys.executable, script_path, "--start"])
        print("\n✅ Restart command executed")

def cmd_dashboard(args):
    """Buka dashboard di browser."""
    url = "http://localhost:8095"
    print(f"\n🌐  Membuka dashboard: {url}")
    if sys.platform == "darwin":
        subprocess.run(["open", url])
    elif sys.platform == "linux":
        subprocess.run(["xdg-open", url])
    elif sys.platform == "win32":
        import os
        os.startfile(url)

def interactive_shell():
    """Interactive shell mode."""
    print("\n" + "=" * 70)
    print("🧠  MAGNATRIX Agentic OS — Interactive CLI")
    print("=" * 70)
    print("\nPerintah tersedia:")
    print("  status       — Tampilkan status sistem")
    print("  swarm list   — Daftar swarm nodes")
    print("  swarm spawn  — Spawn node baru")
    print("  trading      — Status trading")
    print("  knowledge    — Query knowledge graph")
    print("  governance   — Lihat constitution/goals")
    print("  evolve       — Trigger self-evolution")
    print("  boot start   — Jalankan MAGNATRIX")
    print("  boot stop    — Hentikan MAGNATRIX")
    print("  dashboard    — Buka web dashboard")
    print("  emergency    — Emergency stop")
    print("  help         — Tampilkan bantuan")
    print("  quit/exit    — Keluar")
    print("=" * 70)
    
    while True:
        try:
            user_input = input("\nmagnatrix> ").strip()
            if not user_input:
                continue
            
            parts = user_input.split()
            cmd = parts[0]
            
            if cmd in ("quit", "exit"):
                print("\n👋  Selamat tinggal!")
                break
            elif cmd == "help":
                print("\nGunakan: magnatrix <command> --help untuk detail")
            elif cmd == "status":
                cmd_status(None)
            elif cmd == "swarm":
                if len(parts) > 1:
                    if parts[1] == "list":
                        class Args:
                            swarm_cmd = "list"
                        cmd_swarm(Args())
                    elif parts[1] == "spawn":
                        class Args:
                            swarm_cmd = "spawn"
                            count = int(parts[2]) if len(parts) > 2 else 1
                            brain = parts[3] if len(parts) > 3 else "hermes"
                        cmd_swarm(Args())
            elif cmd == "trading":
                class Args:
                    trading_cmd = "status"
                cmd_trading(Args())
            elif cmd == "knowledge":
                entity = parts[1] if len(parts) > 1 else "trading"
                class Args:
                    entity = entity
                    depth = 2
                cmd_knowledge(Args())
            elif cmd == "governance":
                class Args:
                    gov_cmd = "constitution"
                cmd_governance(Args())
            elif cmd == "evolve":
                cmd_evolve(None)
            elif cmd == "boot":
                class Args:
                    boot_cmd = parts[1] if len(parts) > 1 else "status"
                cmd_boot(Args())
            elif cmd == "dashboard":
                cmd_dashboard(None)
            elif cmd == "emergency":
                cmd_emergency(None)
            else:
                print(f"❌  Perintah tidak dikenal: {cmd}")
                print("    Ketik 'help' untuk daftar perintah")
                
        except KeyboardInterrupt:
            print("\n\n👋  Selamat tinggal!")
            break
        except EOFError:
            break

def main():
    parser = argparse.ArgumentParser(
        description="MAGNATRIX Agentic OS — Unified CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:
  magnatrix status                          # Status sistem
  magnatrix swarm list                      # Daftar nodes
  magnatrix swarm spawn --count 3           # Spawn 3 nodes
  magnatrix trading status                  # Status trading
  magnatrix knowledge "trading strategy"    # Query knowledge
  magnatrix governance constitution         # Lihat constitution
  magnatrix evolve                          # Trigger evolution
  magnatrix boot start                      # Jalankan MAGNATRIX
  magnatrix dashboard                       # Buka dashboard
  magnatrix cli                             # Interactive mode
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Perintah MAGNATRIX")
    
    # Status
    subparsers.add_parser("status", help="Tampilkan status sistem")
    
    # Swarm
    swarm_parser = subparsers.add_parser("swarm", help="Kelola swarm nodes")
    swarm_parser.add_argument("swarm_cmd", choices=["list", "spawn", "kill"])
    swarm_parser.add_argument("--count", type=int, help="Jumlah node untuk spawn")
    swarm_parser.add_argument("--brain", type=str, help="Tipe brain (hermes, kimi, gqris)")
    swarm_parser.add_argument("--node-id", type=str, help="Node ID untuk kill")
    
    # Trading
    trading_parser = subparsers.add_parser("trading", help="Kelola trading engine")
    trading_parser.add_argument("trading_cmd", choices=["status", "execute"])
    trading_parser.add_argument("--symbol", type=str, default="BTCUSDT")
    trading_parser.add_argument("--side", choices=["buy", "sell"], default="buy")
    trading_parser.add_argument("--amount", type=float, default=1.0)
    
    # Knowledge
    knowledge_parser = subparsers.add_parser("knowledge", help="Query knowledge graph")
    knowledge_parser.add_argument("entity", type=str, help="Entity untuk query")
    knowledge_parser.add_argument("--depth", type=int, default=2)
    
    # Governance
    gov_parser = subparsers.add_parser("governance", help="Kelola governance")
    gov_parser.add_argument("gov_cmd", choices=["constitution", "goals"])
    
    # Evolve
    subparsers.add_parser("evolve", help="Trigger self-evolution cycle")
    
    # Emergency
    subparsers.add_parser("emergency", help="Emergency stop semua service")
    
    # Chat
    subparsers.add_parser("chat", help="Buka chat client")
    
    # Boot
    boot_parser = subparsers.add_parser("boot", help="Boot/shutdown MAGNATRIX")
    boot_parser.add_argument("boot_cmd", choices=["start", "stop", "restart"])
    
    # Dashboard
    subparsers.add_parser("dashboard", help="Buka web dashboard")
    
    # Interactive CLI
    subparsers.add_parser("cli", help="Interactive shell mode")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    commands = {
        "status": cmd_status,
        "swarm": cmd_swarm,
        "trading": cmd_trading,
        "knowledge": cmd_knowledge,
        "governance": cmd_governance,
        "evolve": cmd_evolve,
        "emergency": cmd_emergency,
        "chat": cmd_chat,
        "boot": cmd_boot,
        "dashboard": cmd_dashboard,
        "cli": lambda _: interactive_shell(),
    }
    
    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
