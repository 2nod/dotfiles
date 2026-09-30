#!/usr/bin/env python3
"""Check collector heartbeat and source freshness independently of the collector."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from usage_store import default_root, health, source_roots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_root())
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--no-probe", action="store_true", help="Check stored health and heartbeat only")
    args = parser.parse_args()
    try:
        result = health(args.root.expanduser(), roots=source_roots(args.sources), probe=not args.no_probe)
    except (OSError, ValueError) as error:
        result = {"state": "unreadable", "reason": type(error).__name__}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["state"] == "running" else 1


if __name__ == "__main__":
    raise SystemExit(main())
