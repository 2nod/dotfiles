#!/usr/bin/env python3
"""SwiftBar view for live pi and Codex skill activity."""

from __future__ import annotations

import json
import os
import pathlib
import re
from datetime import datetime, timezone

ROOT = pathlib.Path(
    os.environ.get(
        "AGENT_OBSERVABILITY_DIR",
        pathlib.Path.home() / ".local/share/agent-observability",
    )
)
STALE_SECONDS = 30 * 60
REPORTER = pathlib.Path.home() / ".local/bin/agent-observability-report"
if not REPORTER.is_file():
    REPORTER = (
        pathlib.Path(__file__).resolve().parents[2]
        / "agent-observability/generate-report.py"
    )


def safe(value: object) -> str:
    return str(value).replace("|", "¦").replace("\n", " ")


def load_states() -> list[dict[str, object]]:
    now = datetime.now(timezone.utc)
    states: list[dict[str, object]] = []
    for path in (ROOT / "live").glob("*.json"):
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            updated = datetime.fromisoformat(str(state["ts"]).replace("Z", "+00:00"))
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            continue
        if (now - updated).total_seconds() <= STALE_SECONDS and isinstance(state, dict):
            states.append(state)
    return sorted(
        states,
        key=lambda item: (str(item.get("state")) != "working", str(item.get("agent"))),
    )


def state_skills(state: dict[str, object]) -> list[str]:
    value = state.get("skills")
    return [str(skill) for skill in value if skill] if isinstance(value, list) else []


def skill_locations() -> dict[str, tuple[str, str, str]]:
    configured = os.environ.get("AGENT_SKILLS_DIRS")
    roots = (
        [
            ("shared", pathlib.Path(value).expanduser())
            for value in configured.split(os.pathsep)
        ]
        if configured
        else [
            ("shared", pathlib.Path.home() / ".agents/skills"),
            ("codex-system", pathlib.Path.home() / ".codex/skills/.system"),
        ]
    )
    locations: dict[str, tuple[str, str, str]] = {}
    for scope, root in roots:
        for path in root.rglob("SKILL.md"):
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                continue
            match = re.search(r"(?m)^name:\s*[\"']?([^\n\"']+)", content)
            if match:
                name = match.group(1).strip()
                origin = (
                    "bundled"
                    if scope == "codex-system"
                    else "installed"
                    if path.with_name("SOURCE.md").is_file()
                    else "authored"
                )
                locations.setdefault(name, (path.as_uri(), scope, origin))
    return locations


def main() -> None:
    states = load_states()
    working = sum(state.get("state") == "working" for state in states)
    skills = sorted({skill for state in states for skill in state_skills(state)})
    title = f"{working}/{len(states)}"
    if skills:
        title += f" {','.join(skills[:2])}"
    color = "green" if working else "gray"
    print(f"{safe(title)}| sfimage=brain.head.profile sfcolor={color}")
    print("---")
    if not states:
        print("No recent pi/Codex sessions| color=gray")
    for state in states:
        agent = safe(state.get("agent", "unknown"))
        status = safe(state.get("state", "unknown"))
        dot = "circle.fill" if status == "working" else "circle"
        dot_color = "green" if status == "working" else "gray"
        project = pathlib.Path(str(state.get("cwd", ""))).name or "?"
        print(
            f"{agent} · {safe(project)} · {status}| sfimage={dot} sfcolor={dot_color}"
        )
        current_skills = state_skills(state)
        print(
            f"--Skills: {safe(', '.join(current_skills) or 'none')}| size=12 color=gray"
        )
        locations = skill_locations()
        for skill in current_skills:
            location = locations.get(skill)
            if location:
                uri, scope, origin = location
                print(
                    f"---{safe(skill)} · {scope} · {origin}| "
                    f"bash=open param1={uri} terminal=false"
                )
            else:
                print(f"---{safe(skill)}| disabled=true")
        if state.get("model"):
            print(f"--Model: {safe(state['model'])}| size=12 color=gray")
        print(
            f"--Session: {safe(str(state.get('session_id', '?'))[:12])}| size=12 color=gray"
        )
    print("---")
    if REPORTER.is_file():
        print(
            f"Open report| bash={REPORTER} param1=--open terminal=false sfimage=chart.bar.doc.horizontal"
        )
    print("Refresh| refresh=true sfimage=arrow.clockwise")


if __name__ == "__main__":
    main()
