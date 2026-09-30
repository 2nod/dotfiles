#!/usr/bin/env python3
"""Open reports from saved skill usage and evaluation records."""

from __future__ import annotations

import pathlib
import json
import subprocess

REPORTER = pathlib.Path.home() / ".local/bin/agent-observability-report"
if not REPORTER.is_file():
    REPORTER = (
        pathlib.Path(__file__).resolve().parents[2]
        / "agent-observability/generate-report.py"
    )
DOCTOR = pathlib.Path.home() / ".local/bin/agent-observability-doctor"


def main() -> None:
    try:
        result = subprocess.run([str(DOCTOR), "--no-probe"], capture_output=True, text=True, timeout=5)
        collection = json.loads(result.stdout)
        states = {row["state"] for row in collection.get("runtimes", [])}
        attention = collection["state"] != "running" or bool(states - {"up_to_date", "awaiting_line", "unconfigured"})
        label = "Skills !" if attention else "Skills"
    except (OSError, ValueError, subprocess.TimeoutExpired):
        collection = {"state": "unavailable", "runtimes": []}
        label = "Skills !"
    print(f"{label}| sfimage=brain.head.profile")
    print("---")
    print(f'Collector: {collection["state"]}')
    for row in collection.get("runtimes", []):
        print(f'{row["runtime"]}: {row["state"]}')
    if DOCTOR.is_file():
        print(f"Check collection| bash={DOCTOR} terminal=true")
    if REPORTER.is_file():
        print(
            f"Open report| bash={REPORTER} param1=--open terminal=false sfimage=chart.bar.doc.horizontal"
        )
    print("Refresh| refresh=true sfimage=arrow.clockwise")


if __name__ == "__main__":
    main()
