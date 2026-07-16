"""Command-line interface for Metaname domain lifecycle operations."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from typing import Any

from .client import PROD_API_URL, TEST_API_URL, MetanameClient


def _client(production: bool) -> MetanameClient:
    return MetanameClient(base_url=PROD_API_URL if production else TEST_API_URL)


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="octodns-metaname",
        description="Check, list, and register domains through the Metaname API.",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="use the live Metaname API (the test API is the default)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="check whether a domain is available")
    check.add_argument("domain")
    check.add_argument("--source-ip")

    commands.add_parser("list", help="list domains under the authenticated account")

    register = commands.add_parser("register", help="register an available domain")
    register.add_argument("domain")
    register.add_argument("--term", type=int, default=12, help="registration term in months")
    register.add_argument(
        "--confirm",
        action="store_true",
        required=True,
        help="confirm registration and its associated test credit or production cost",
    )
    register.add_argument(
        "--nameserver",
        action="append",
        dest="nameservers",
        help="nameserver hostname; repeat for multiple nameservers",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    client = _client(args.production)

    if args.command == "check":
        status = client.check_domain(args.domain, source_ip=args.source_ip)
        _print_json({"domain": args.domain.rstrip("."), "status": status})
        return 0
    if args.command == "list":
        _print_json(client.list_domains())
        return 0
    if args.command == "register":
        result = client.register_domain(
            args.domain,
            term=args.term,
            confirm=args.confirm,
            nameservers=args.nameservers,
        )
        _print_json(result)
        return 0

    raise AssertionError(f"Unhandled command: {args.command}")  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
