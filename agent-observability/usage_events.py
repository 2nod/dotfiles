"""Reconstruct observed work turns for both usage reports and offline analysis."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import pathlib
from typing import cast


@dataclass
class Turn:
    agent: str
    session_id: str
    turn_id: str
    project: str
    model: str
    started: datetime
    agent_id: str = "root"
    turn_id_inferred: bool = False
    start_observed: bool = False
    schema_version: int | None = None
    ended: datetime | None = None
    skills: set[str] = field(default_factory=set)
    versions: dict[str, str] = field(default_factory=dict)
    tools: int = 0
    tool_counts: dict[str, int] = field(default_factory=dict)
    verification_status: dict[str, str] = field(default_factory=dict)
    verification_details: dict[str, str] = field(default_factory=dict)
    observations: list[dict] = field(default_factory=list)


@dataclass
class SkillStats:
    uses: int = 0
    verified: int = 0
    failed: int = 0
    unverified: int = 0
    ongoing: int = 0
    legacy: int = 0
    tools: int = 0
    tool_counts: dict[str, int] = field(default_factory=dict)
    durations: list[float] = field(default_factory=list)
    versions: set[str] = field(default_factory=set)
    last_used: datetime | None = None


def turn_outcome(turn: Turn) -> str:
    if turn.schema_version not in {2, 3}:
        return "旧形式"
    if not turn.ended:
        return "終了記録なし"
    if turn.verification_status and all(
        status == "passed" for status in turn.verification_status.values()
    ):
        return "検証済み"
    return "検証失敗" if "failed" in turn.verification_status.values() else "未検証"


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return timestamp if timestamp.tzinfo is not None else None
    except ValueError:
        return None


def build_turns(events: list[dict[str, object]]) -> list[Turn]:
    turns: list[Turn] = []
    active: dict[tuple[str, str, str], Turn] = {}
    identified: dict[tuple[str, str, str, str], Turn] = {}
    counters: dict[tuple[str, str, str], int] = {}

    for event in events:
        agent = str(event.get("agent", "unknown"))
        session = str(event.get("session_id", "unknown"))
        agent_id = str(event.get("agent_id", "root"))
        owner = (agent, session, agent_id)
        name = str(event.get("event", ""))
        timestamp = parse_time(event.get("ts"))
        if not timestamp or name in {"session_started", "session_ended"}:
            continue
        event_turn_id = event.get("turn_id")
        key = (*owner, str(event_turn_id)) if event_turn_id else None
        turn = identified.get(key) if key else active.get(owner)
        if name == "agent_started":
            counters[owner] = counters.get(owner, 0) + 1
            # Pi has no explicit turn ID. Each start establishes a new turn.
            if not key:
                turn = None
        if turn is None:
            turn_id = str(event_turn_id or (
                counters[owner] if name == "agent_started" else "unknown"
            ))
            turn = Turn(
                agent=agent,
                session_id=session,
                turn_id=turn_id,
                project=pathlib.Path(str(event.get("cwd", ""))).name or "?",
                model=str(event.get("model", "?")),
                started=timestamp,
                agent_id=agent_id,
                turn_id_inferred=bool(event.get("turn_id_inferred")) or not bool(event_turn_id),
                schema_version=(
                    cast(int, event["schema_version"])
                    if isinstance(event.get("schema_version"), int)
                    else None
                ),
            )
            active[owner] = turn
            turns.append(turn)
            if key:
                identified[key] = turn
        turn.observations.append(event)
        if name == "agent_started":
            turn.start_observed = True
            active[owner] = turn
        elif name == "skill_activated" and isinstance(event.get("skill"), str):
            skill = str(event["skill"])
            if event.get("schema_version") != 3 or (event.get("skill_evidence") == "confirmed" and not event.get("branch_unverified")):
                turn.skills.add(skill)
            version = event.get("skill_version")
            if isinstance(version, str):
                turn.versions[skill] = version
        elif name in {"tool_started", "verification_started"}:
            turn.tools += 1
            tool = event.get("tool")
            if isinstance(tool, str):
                turn.tool_counts[tool] = turn.tool_counts.get(tool, 0) + 1
        elif name == "verification_finished":
            verification = event.get("verification")
            status = event.get("status")
            if event.get("schema_version") == 3 and verification and event.get("tool_use_id"):
                verification = f"{verification}:{event['tool_use_id']}"
            if isinstance(verification, str) and isinstance(status, str) and status in {"passed", "failed", "unknown"}:
                turn.verification_status[verification] = str(status)
                details = []
                diagnostics = event.get("diagnostics")
                if isinstance(diagnostics, (int, float)) and diagnostics:
                    details.append(f"error {diagnostics:g}件")
                warnings = event.get("warnings")
                if isinstance(warnings, (int, float)) and warnings:
                    details.append(f"warning {warnings:g}件")
                if event.get("unconfirmed"):
                    details.append("未確認")
                if details:
                    turn.verification_details[verification] = "・".join(details)
                else:
                    turn.verification_details.pop(verification, None)
        elif name == "agent_end":
            turn.ended = timestamp
            if active.get(owner) is turn:
                active.pop(owner, None)
    return turns


def aggregate(turns: list[Turn]) -> dict[str, SkillStats]:
    result: dict[str, SkillStats] = {}
    for turn in turns:
        for skill in turn.skills:
            stats = result.setdefault(skill, SkillStats())
            stats.uses += 1
            stats.tools += turn.tools
            if stats.last_used is None or turn.started > stats.last_used:
                stats.last_used = turn.started
            for tool, count in turn.tool_counts.items():
                stats.tool_counts[tool] = stats.tool_counts.get(tool, 0) + count
            version = turn.versions.get(skill)
            if version:
                stats.versions.add(version)
            if turn.schema_version not in {2, 3}:
                stats.legacy += 1
            elif not turn.ended:
                stats.ongoing += 1
            elif turn.verification_status and all(
                status == "passed" for status in turn.verification_status.values()
            ):
                stats.verified += 1
            elif "failed" in turn.verification_status.values():
                stats.failed += 1
            else:
                stats.unverified += 1
            if turn.ended:
                stats.durations.append((turn.ended - turn.started).total_seconds())
    return result
