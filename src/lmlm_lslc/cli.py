"""Command-line entry point for LSLC's offline preflight checks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runner import run_security_self_test


def main() -> int:
    parser = argparse.ArgumentParser(prog="lmlm-lslc")
    sub = parser.add_subparsers(dest="command", required=True)
    self_test = sub.add_parser("self-test", help="validate offline security controls")
    self_test.add_argument(
        "--fixture",
        default="fixtures/threatintel/nikke-k2f.json",
        help="path to an offline-only IOC JSON fixture",
    )
    args = parser.parse_args()

    if args.command == "self-test":
        report = run_security_self_test(Path(args.fixture))
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0 if report.status == "passed" else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
