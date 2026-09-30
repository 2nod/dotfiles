#!/usr/bin/env python3
"""Collect native Codex, Claude Code and Pi logs without hooks or model calls."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from usage_store import collect, default_root, discover, source_roots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_root())
    parser.add_argument("--sources", type=Path, help="JSON object mapping runtime names to log directories")
    parser.add_argument("--once", action="store_true", help="Run one bounded pass (the default)")
    parser.add_argument("--dry-run", action="store_true", help="Discover sources without creating or modifying the DB")
    parser.add_argument("--max-mib", type=int, default=256)
    args = parser.parse_args()
    if args.max_mib < 1:
        parser.error("--max-mib must be positive")
    try:
        roots = source_roots(args.sources)
        if args.dry_run:
            files, sources = discover(roots)
            result = {"sources": sources, "files": len(files)}
        else:
            result = collect(args.root.expanduser(), roots, max_bytes=args.max_mib * 1024 * 1024)
    except (OSError, ValueError) as error:
        print(json.dumps({"state": "error", "reason": type(error).__name__}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("state") != "partial" else 1


if __name__ == "__main__":
    raise SystemExit(main())
