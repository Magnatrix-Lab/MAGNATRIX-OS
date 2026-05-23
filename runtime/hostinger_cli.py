#!/usr/bin/env python3
"""
Hostinger CLI — Command-line interface for Hostinger API Native SDK.
Provides interactive commands for managing VPS, domains, DNS, hosting, billing.

Usage:
    python3 hostinger_cli.py --token <API_TOKEN> vps list
    python3 hostinger_cli.py --token <API_TOKEN> domain check example.com
    python3 hostinger_cli.py --token <API_TOKEN> dns get-zone example.com
    python3 hostinger_cli.py --token <API_TOKEN> vps create --plan 1 --os 2 --dc 3

Environment:
    HOSTINGER_API_TOKEN — default API token
    HOSTINGER_BASE_URL  — override base URL
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hostinger_api_native import (
    HostingerClient,
    HostingerError,
    HostingerKernel,
    BillingAPI,
    DNSAPI,
    DomainsAPI,
    HostingAPI,
    VPSAPI,
    ReachAPI,
    DNSRecord,
    DomainForward,
    FirewallRule,
    FirewallConfig,
    HostingOrderRequest,
)


class OutputFormatter:
    """Pretty-print API responses."""

    @staticmethod
    def print_json(data: Any) -> None:
        """Print as formatted JSON."""
        if hasattr(data, "__dataclass_fields__"):
            from dataclasses import asdict
            data = asdict(data)
        print(json.dumps(data, indent=2, default=str))

    @staticmethod
    def print_table(headers: List[str], rows: List[List[Any]]) -> None:
        """Print as simple text table."""
        if not rows:
            print("(no data)")
            return
        col_widths = [max(len(str(h)), max(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)]
        sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        print(sep)
        print("| " + " | ".join(str(h).ljust(w) for h, w in zip(headers, col_widths)) + " |")
        print(sep)
        for row in rows:
            print("| " + " | ".join(str(c).ljust(w) for c, w in zip(row, col_widths)) + " |")
        print(sep)

    @staticmethod
    def print_response(resp: Any, table: bool = False, headers: Optional[List[str]] = None) -> None:
        """Print a BaseResponse."""
        if hasattr(resp, "data"):
            data = resp.data
        else:
            data = resp
        if table and isinstance(data, list) and headers:
            rows = []
            for item in data:
                if hasattr(item, "__dataclass_fields__"):
                    from dataclasses import asdict
                    d = asdict(item)
                else:
                    d = item
                rows.append([str(d.get(h, "")) for h in headers])
            OutputFormatter.print_table(headers, rows)
        else:
            OutputFormatter.print_json(data)


def get_client(args: argparse.Namespace) -> HostingerClient:
    """Create client from args or environment."""
    token = args.token or os.environ.get("HOSTINGER_API_TOKEN")
    if not token:
        print("Error: API token required. Use --token or set HOSTINGER_API_TOKEN", file=sys.stderr)
        sys.exit(1)
    base_url = os.environ.get("HOSTINGER_BASE_URL", HostingerClient.DEFAULT_BASE_URL)
    return HostingerClient(api_token=token, base_url=base_url)


def cmd_vps_list(args: argparse.Namespace) -> None:
    client = get_client(args)
    vps = VPSAPI(client)
    resp = vps.list_vms(page=args.page, per_page=args.per_page)
    OutputFormatter.print_response(resp, table=True, headers=["id", "name", "status", "ipv4", "plan_id"])


def cmd_vps_get(args: argparse.Namespace) -> None:
    client = get_client(args)
    vps = VPSAPI(client)
    resp = vps.get_vm(args.id)
    OutputFormatter.print_response(resp)


def cmd_vps_create(args: argparse.Namespace) -> None:
    client = get_client(args)
    vps = VPSAPI(client)
    labels = {}
    if args.label:
        for lv in args.label:
            k, v = lv.split("=", 1)
            labels[k] = v
    resp = vps.create_vm(
        plan_id=args.plan,
        os_template_id=args.os,
        datacenter_id=args.datacenter,
        hostname=args.hostname,
        ssh_key_ids=args.ssh_key,
        labels=labels or None,
    )
    OutputFormatter.print_response(resp)


def cmd_vps_destroy(args: argparse.Namespace) -> None:
    client = get_client(args)
    vps = VPSAPI(client)
    resp = vps.destroy_vm(args.id)
    OutputFormatter.print_response(resp)


def cmd_vps_start(args: argparse.Namespace) -> None:
    client = get_client(args)
    vps = VPSAPI(client)
    resp = vps.start_vm(args.id)
    OutputFormatter.print_response(resp)


def cmd_vps_stop(args: argparse.Namespace) -> None:
    client = get_client(args)
    vps = VPSAPI(client)
    resp = vps.stop_vm(args.id)
    OutputFormatter.print_response(resp)


def cmd_vps_reboot(args: argparse.Namespace) -> None:
    client = get_client(args)
    vps = VPSAPI(client)
    resp = vps.reboot_vm(args.id)
    OutputFormatter.print_response(resp)


def cmd_vps_snapshots(args: argparse.Namespace) -> None:
    client = get_client(args)
    vps = VPSAPI(client)
    resp = vps.list_snapshots(args.id)
    OutputFormatter.print_response(resp, table=True, headers=["id", "name", "created_at", "status"])


def cmd_vps_firewall(args: argparse.Namespace) -> None:
    client = get_client(args)
    vps = VPSAPI(client)
    resp = vps.get_firewall(args.id)
    OutputFormatter.print_response(resp)


def cmd_domain_check(args: argparse.Namespace) -> None:
    client = get_client(args)
    domains = DomainsAPI(client)
    resp = domains.check_availability(args.domain)
    OutputFormatter.print_response(resp)


def cmd_domain_list(args: argparse.Namespace) -> None:
    client = get_client(args)
    domains = DomainsAPI(client)
    resp = domains.list_portfolio(page=args.page, per_page=args.per_page)
    OutputFormatter.print_response(resp, table=True, headers=["domain", "status", "expires_at", "auto_renew"])


def cmd_domain_whois(args: argparse.Namespace) -> None:
    client = get_client(args)
    domains = DomainsAPI(client)
    resp = domains.get_whois(args.domain)
    OutputFormatter.print_response(resp)


def cmd_dns_get(args: argparse.Namespace) -> None:
    client = get_client(args)
    dns = DNSAPI(client)
    resp = dns.get_zone(args.domain)
    OutputFormatter.print_response(resp)


def cmd_dns_records(args: argparse.Namespace) -> None:
    client = get_client(args)
    dns = DNSAPI(client)
    resp = dns.get_zone(args.domain)
    if resp.data and resp.data.records:
        rows = [[r.id, r.type, r.name, r.value, r.ttl] for r in resp.data.records]
        OutputFormatter.print_table(["id", "type", "name", "value", "ttl"], rows)
    else:
        print("(no records)")


def cmd_dns_add(args: argparse.Namespace) -> None:
    client = get_client(args)
    dns = DNSAPI(client)
    record = DNSRecord(
        name=args.name,
        type=args.type,
        value=args.value,
        ttl=args.ttl,
        priority=args.priority,
    )
    resp = dns.create_record(args.domain, record)
    OutputFormatter.print_response(resp)


def cmd_website_list(args: argparse.Namespace) -> None:
    client = get_client(args)
    hosting = HostingAPI(client)
    resp = hosting.list_websites(page=args.page, per_page=args.per_page)
    OutputFormatter.print_response(resp, table=True, headers=["id", "domain", "plan", "status", "ssl_active"])


def cmd_billing_subscriptions(args: argparse.Namespace) -> None:
    client = get_client(args)
    billing = BillingAPI(client)
    resp = billing.list_subscriptions(page=args.page, per_page=args.per_page)
    OutputFormatter.print_response(resp, table=True, headers=["id", "status", "domain", "auto_renewal", "next_billing_date"])


def cmd_kernel_sync(args: argparse.Namespace) -> None:
    token = args.token or os.environ.get("HOSTINGER_API_TOKEN")
    if not token:
        print("Error: API token required", file=sys.stderr)
        sys.exit(1)
    kernel = HostingerKernel(api_token=token)
    summary = kernel.full_sync()
    OutputFormatter.print_json(summary)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="hostinger-cli",
        description="Hostinger API CLI — manage VPS, domains, DNS, hosting",
    )
    parser.add_argument("--token", help="Hostinger API bearer token")
    parser.add_argument("--output", choices=["json", "table"], default="json", help="Output format")

    sub = parser.add_subparsers(dest="command", help="Commands")

    # VPS
    vps_p = sub.add_parser("vps", help="VPS management")
    vps_sub = vps_p.add_subparsers(dest="vps_cmd")

    vps_list_p = vps_sub.add_parser("list", help="List VMs")
    vps_list_p.set_defaults(func=cmd_vps_list)
    vps_list_p.add_argument("--page", type=int, default=1)
    vps_list_p.add_argument("--per-page", type=int, default=25)

    vps_get_p = vps_sub.add_parser("get", help="Get VM details")
    vps_get_p.set_defaults(func=cmd_vps_get)
    vps_get_p.add_argument("id", type=int)

    vps_create_p = vps_sub.add_parser("create", help="Create VM")
    vps_create_p.set_defaults(func=cmd_vps_create)
    vps_create_p.add_argument("--plan", type=int, required=True)
    vps_create_p.add_argument("--os", type=int, required=True)
    vps_create_p.add_argument("--datacenter", type=int, required=True)
    vps_create_p.add_argument("--hostname")
    vps_create_p.add_argument("--ssh-key", type=int, action="append")
    vps_create_p.add_argument("--label", action="append", help="key=value")

    vps_destroy_p = vps_sub.add_parser("destroy", help="Destroy VM")
    vps_destroy_p.set_defaults(func=cmd_vps_destroy)
    vps_destroy_p.add_argument("id", type=int)

    vps_start_p = vps_sub.add_parser("start", help="Start VM")
    vps_start_p.set_defaults(func=cmd_vps_start)
    vps_start_p.add_argument("id", type=int)

    vps_stop_p = vps_sub.add_parser("stop", help="Stop VM")
    vps_stop_p.set_defaults(func=cmd_vps_stop)
    vps_stop_p.add_argument("id", type=int)

    vps_reboot_p = vps_sub.add_parser("reboot", help="Reboot VM")
    vps_reboot_p.set_defaults(func=cmd_vps_reboot)
    vps_reboot_p.add_argument("id", type=int)

    vps_snap_p = vps_sub.add_parser("snapshots", help="List VM snapshots")
    vps_snap_p.set_defaults(func=cmd_vps_snapshots)
    vps_snap_p.add_argument("id", type=int)

    vps_fw_p = vps_sub.add_parser("firewall", help="Get VM firewall")
    vps_fw_p.set_defaults(func=cmd_vps_firewall)
    vps_fw_p.add_argument("id", type=int)

    # Domains
    domain_p = sub.add_parser("domain", help="Domain management")
    domain_sub = domain_p.add_subparsers(dest="domain_cmd")

    domain_check_p = domain_sub.add_parser("check", help="Check domain availability")
    domain_check_p.set_defaults(func=cmd_domain_check)
    domain_check_p.add_argument("domain")

    domain_list_p = domain_sub.add_parser("list", help="List portfolio")
    domain_list_p.set_defaults(func=cmd_domain_list)
    domain_list_p.add_argument("--page", type=int, default=1)
    domain_list_p.add_argument("--per-page", type=int, default=25)

    domain_whois_p = domain_sub.add_parser("whois", help="WHOIS lookup")
    domain_whois_p.set_defaults(func=cmd_domain_whois)
    domain_whois_p.add_argument("domain")

    # DNS
    dns_p = sub.add_parser("dns", help="DNS management")
    dns_sub = dns_p.add_subparsers(dest="dns_cmd")

    dns_get_p = dns_sub.add_parser("get-zone", help="Get DNS zone")
    dns_get_p.set_defaults(func=cmd_dns_get)
    dns_get_p.add_argument("domain")

    dns_records_p = dns_sub.add_parser("records", help="List DNS records")
    dns_records_p.set_defaults(func=cmd_dns_records)
    dns_records_p.add_argument("domain")

    dns_add_p = dns_sub.add_parser("add", help="Add DNS record")
    dns_add_p.set_defaults(func=cmd_dns_add)
    dns_add_p.add_argument("domain")
    dns_add_p.add_argument("--name", required=True)
    dns_add_p.add_argument("--type", required=True, choices=["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SRV"])
    dns_add_p.add_argument("--value", required=True)
    dns_add_p.add_argument("--ttl", type=int, default=3600)
    dns_add_p.add_argument("--priority", type=int)

    # Hosting / Websites
    web_p = sub.add_parser("website", help="Website management")
    web_sub = web_p.add_subparsers(dest="web_cmd")

    web_list_p = web_sub.add_parser("list", help="List websites")
    web_list_p.set_defaults(func=cmd_website_list)
    web_list_p.add_argument("--page", type=int, default=1)
    web_list_p.add_argument("--per-page", type=int, default=25)

    # Billing
    bill_p = sub.add_parser("billing", help="Billing management")
    bill_sub = bill_p.add_subparsers(dest="bill_cmd")

    bill_subs_p = bill_sub.add_parser("subscriptions", help="List subscriptions")
    bill_subs_p.set_defaults(func=cmd_billing_subscriptions)
    bill_subs_p.add_argument("--page", type=int, default=1)
    bill_subs_p.add_argument("--per-page", type=int, default=25)

    # Kernel
    kernel_p = sub.add_parser("kernel", help="MAGNATRIX kernel operations")
    kernel_sub = kernel_p.add_subparsers(dest="kernel_cmd")

    kernel_sync_p = kernel_sub.add_parser("sync", help="Full infrastructure sync")
    kernel_sync_p.set_defaults(func=cmd_kernel_sync)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    try:
        if hasattr(args, "func"):
            args.func(args)
        else:
            parser.print_help()
            return 1
    except HostingerError as e:
        print(f"Error: {e.__class__.__name__}: {e.message}", file=sys.stderr)
        if e.status_code:
            print(f"HTTP {e.status_code}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130

    return 0


if __name__ == "__main__":
    sys.exit(main())
