#!/usr/bin/env python3
"""Generate a local HTML report from agent observability JSONL events."""

from __future__ import annotations

import argparse
import importlib.util
import html
import json
import os
import pathlib
import re
import statistics
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import cast
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from eval_contracts import (
    EVALUATION_PAUSE_REASON,
    load_catalog,
    skill_summary,
    case_verdict,
    contract_version,
    reviewed_result,
    LABELS,
)

from skill_current_state import deployment_state, collect_rounds, decision_state

ROOT = pathlib.Path(
    os.environ.get(
        "AGENT_OBSERVABILITY_DIR",
        pathlib.Path.home() / ".local/share/agent-observability",
    )
)


@dataclass
class Turn:
    agent: str
    session_id: str
    turn_id: str
    project: str
    model: str
    started: datetime
    schema_version: int | None = None
    ended: datetime | None = None
    skills: set[str] = field(default_factory=set)
    versions: dict[str, str] = field(default_factory=dict)
    tools: int = 0
    tool_counts: dict[str, int] = field(default_factory=dict)
    verification_status: dict[str, str] = field(default_factory=dict)
    verification_details: dict[str, str] = field(default_factory=dict)


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
    if turn.schema_version != 2:
        return "旧形式"
    if not turn.ended:
        return "終了記録なし"
    if turn.verification_status and all(
        status == "passed" for status in turn.verification_status.values()
    ):
        return "検証済み"
    return "検証失敗" if turn.verification_status else "未検証"


def format_verifications(turn: Turn) -> str:
    labels = {"passed": "成功", "failed": "失敗"}
    return " / ".join(
        f"{html.escape(kind)}: {labels[status]}"
        + (
            f"（{html.escape(turn.verification_details[kind])}）"
            if kind in turn.verification_details
            else ""
        )
        for kind, status in sorted(turn.verification_status.items())
    )


def format_tool_counts(counts: dict[str, int]) -> str:
    return (
        " / ".join(
            f"{html.escape(tool)} {count}"
            for tool, count in sorted(
                counts.items(), key=lambda item: (-item[1], item[0])
            )
        )
        or "—"
    )


def load_skill_locations() -> dict[str, tuple[str, str, str]]:
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
        for skill_path in root.rglob("SKILL.md"):
            try:
                content = skill_path.read_text(encoding="utf-8")
            except OSError:
                continue
            match = re.search(r"(?m)^name:\s*[\"']?([^\n\"']+)", content)
            if not match:
                continue
            name = match.group(1).strip()
            origin = (
                "bundled"
                if scope == "codex-system"
                else "installed"
                if skill_path.with_name("SOURCE.md").is_file()
                else "authored"
            )
            locations.setdefault(name, (skill_path.as_uri(), scope, origin))
    return locations


def skill_link(skill: str, locations: dict[str, tuple[str, str, str]]) -> str:
    label = html.escape(skill)
    location = locations.get(skill)
    return (
        f'<a href="{html.escape(location[0], quote=True)}">{label}</a>'
        if location
        else label
    )


def skill_status(skill: str, locations: dict[str, tuple[str, str, str]]) -> str:
    location = locations.get(skill)
    return f"{location[1]} · {location[2]}" if location else "unknown"


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_events(days: int) -> list[dict[str, object]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    events: list[dict[str, object]] = []
    for path in sorted((ROOT / "events").glob("*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(raw, dict):
                continue
            event = cast(dict[str, object], raw)
            timestamp = parse_time(event.get("ts"))
            if timestamp and timestamp >= cutoff:
                events.append(event)
    return sorted(events, key=lambda event: parse_time(event.get("ts")) or cutoff)


def load_eval_cases() -> dict[str, dict[str, object]]:
    configured = os.environ.get("AGENT_EVAL_CASES_DIR")
    cases_dir = (
        pathlib.Path(configured).expanduser()
        if configured
        else pathlib.Path(__file__).resolve().parents[1] / ".agents/evals"
    )
    cases: dict[str, dict[str, object]] = {}
    for path in cases_dir.glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(raw, dict) and isinstance(raw.get("id"), str):
            cases[str(raw["id"])] = cast(dict[str, object], raw)
    return cases


def load_eval_results(days: int) -> list[dict[str, object]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    results: list[dict[str, object]] = []
    for path in sorted((ROOT / "eval-results").glob("*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(raw, dict):
                continue
            result = cast(dict[str, object], raw)
            timestamp = parse_time(result.get("ts"))
            if timestamp and timestamp >= cutoff:
                results.append(reviewed_result(result))
    return results


def median_value(items: list[dict[str, object]], key: str) -> float:
    values = [
        value for item in items if isinstance((value := item.get(key)), (int, float))
    ]
    try:
        return float(statistics.median(values)) if values else 0
    except statistics.StatisticsError:
        return 0


def number_value(value: object, default: float = 0) -> float:
    try:
        return float(value) if isinstance(value, (int, float)) else default
    except (TypeError, ValueError):
        return default


def render_eval_details(items: list[dict[str, object]]) -> str:
    failures = [item for item in items if not bool(item.get("success"))]
    if not failures:
        return "<span class=good>失敗なし</span>"
    entries = []
    for item in sorted(
        failures,
        key=lambda value: (
            str(value.get("variant")),
            number_value(value.get("run")),
        ),
    ):
        kind = str(item.get("failure_kind", "verifier_failed"))
        phase = str(item.get("failure_phase", "verifier"))
        detail = str(item.get("failure_detail", ""))
        expected = str(item.get("expected_behavior", ""))
        conditions = item.get("failure_conditions", [])
        condition_text = (
            "、".join(str(value) for value in conditions)
            if isinstance(conditions, list)
            else ""
        )
        verifiers = item.get("verifiers", [])
        verifier_text = []
        if isinstance(verifiers, list):
            for verifier in verifiers:
                if isinstance(verifier, dict) and verifier.get("exit") != 0:
                    verifier_text.append(
                        f"{verifier.get('name', 'verifier')} exit {verifier.get('exit', '?')}"
                    )
        facts = " · ".join(
            [f"phase: {phase}"]
            + ([f"期待: {expected}"] if expected else [])
            + ([f"条件: {condition_text}"] if condition_text else [])
            + verifier_text
            + ([f"実際: {detail}"] if detail else [])
        )
        entries.append(
            "<li>"
            f"<strong>{html.escape(str(item.get('variant', '?')))} #{html.escape(str(item.get('run', '?')))}</strong> "
            f"{html.escape(kind)} · {number_value(item.get('duration_seconds')):.1f}s"
            f"{f'<small>{html.escape(facts)}</small>' if facts else ''}</li>"
        )
    return f"<details class=detail-panel><summary>{len(failures)}件の失敗</summary><ul>{''.join(entries)}</ul></details>"


def render_eval_contract(case: dict[str, object] | None) -> str:
    if not case:
        return "<span class=note>評価ケースの定義なし</span>"
    conditions = case.get("failure_conditions", [])
    condition_items = (
        "".join(f"<li>{html.escape(str(value))}</li>" for value in conditions)
        if isinstance(conditions, list)
        else ""
    )
    verifiers = case.get("verifiers", [])
    verifier_items = []
    if isinstance(verifiers, list):
        for verifier in verifiers:
            if isinstance(verifier, list):
                verifier_items.append(
                    " ".join(html.escape(str(value)) for value in verifier)
                )
    verifier_text = " / ".join(verifier_items) or "—"
    return (
        "<details class=contract><summary>条件を見る</summary>"
        "<dl>"
        f"<dt>スキルなし</dt><dd>同じテストデータ・課題・検証プログラムを使い、対象スキルを読み込まない</dd>"
        f"<dt>スキルあり</dt><dd>同じ条件で{html.escape(str(case.get('skill', '?')))}を追加で読み込む（依存スキルは計画で明示）</dd>"
        f"<dt>課題</dt><dd>{html.escape(str(case.get('prompt', '—')))}</dd>"
        f"<dt>テストデータ</dt><dd>{html.escape(pathlib.Path(str(case.get('fixture', '—'))).name)}</dd>"
        f"<dt>成功条件</dt><dd>{html.escape(str(case.get('expected_behavior', '—')))}</dd>"
        f"<dt>失敗条件</dt><dd><ul>{condition_items}</ul></dd>"
        f"<dt>検証コマンド</dt><dd>{verifier_text}</dd>"
        "<dt>成功判定</dt><dd>エージェントと全検証プログラムの正常終了を確認したうえで、目的を達成したかを成果物の証拠に基づいて別途採点する</dd>"
        "</dl></details>"
    )


def render_eval_rows(
    results: list[dict[str, object]],
    locations: dict[str, tuple[str, str, str]],
    cases: dict[str, dict[str, object]],
    include_contract: bool = True,
) -> str:
    grouped: dict[
        tuple[str, str, str, str, str, str], dict[str, list[dict[str, object]]]
    ] = {}
    for result in results:
        key = (
            str(result.get("skill", "?")),
            str(result.get("case", "?")),
            str(result.get("agent", "?")),
            str(result.get("model", "?")),
            str(result.get("experiment_id", "legacy")),
            str(result.get("skill_version", "legacy")),
        )
        variant = str(result.get("variant", ""))
        if variant in {"control", "treatment"}:
            grouped.setdefault(key, {"control": [], "treatment": []})[variant].append(
                result
            )

    rows = []
    for (skill, case, agent, model, experiment_id, skill_version), variants in sorted(
        grouped.items()
    ):
        control = variants["control"]
        treatment = variants["treatment"]
        control_success = sum(bool(item.get("success")) for item in control)
        treatment_success = sum(bool(item.get("success")) for item in treatment)
        control_rate = control_success / len(control) if control else 0
        treatment_rate = treatment_success / len(treatment) if treatment else 0
        successful_control = [item for item in control if bool(item.get("success"))]
        successful_treatment = [item for item in treatment if bool(item.get("success"))]
        control_lines = median_value(successful_control, "changed_lines")
        treatment_lines = median_value(successful_treatment, "changed_lines")
        control_classes = median_value(successful_control, "classes_added")
        treatment_classes = median_value(successful_treatment, "classes_added")
        signal, reason, paired_runs = case_verdict(
            cases.get(case, {}), control + treatment
        )
        verdict = LABELS[signal] + " · " + reason
        contract_cell = (
            f'<td data-label="実験条件" class=detail>{render_eval_contract(cases.get(case))}</td>'
            if include_contract
            else ""
        )
        rows.append(
            f'<tr class=data-row data-eval-skill="{html.escape(skill)}">'
            f'<td data-label="Skill / Case"><strong>{skill_link(skill, locations)}</strong><small>{html.escape(case)} · {skill_status(skill, locations)}</small></td>'
            f'<td data-label="エージェント">{html.escape(agent)}</td><td data-label="モデル">{html.escape(model)}<small>{html.escape(experiment_id[:8])} · {html.escape(skill_version[:19])}</small></td>'
            f'<td data-label="なし成功">{control_success}/{len(control)}</td>'
            f'<td data-label="あり成功">{treatment_success}/{len(treatment)}</td>'
            f'<td data-label="成功率差">{(treatment_rate - control_rate) * 100:+.0f}pt</td>'
            f'<td data-label="判定">{html.escape(verdict)}</td>'
            f'<td data-label="変更行 なし→あり">{control_lines:.0f} → {treatment_lines:.0f}</td>'
            f'<td data-label="追加class なし→あり">{control_classes:.0f} → {treatment_classes:.0f}</td>'
            f'{contract_cell}<td data-label="失敗詳細" class=detail>{render_eval_details(control + treatment)}</td></tr>'
        )
    return (
        "".join(rows)
        or f'<tr><td colspan="{11 if include_contract else 10}" class=empty>表示期間内に比較評価の結果がありません。</td></tr>'
    )


def build_turns(events: list[dict[str, object]]) -> list[Turn]:
    turns: list[Turn] = []
    active: dict[tuple[str, str, str], Turn] = {}
    counters: dict[tuple[str, str, str], int] = {}

    for event in events:
        agent = str(event.get("agent", "unknown"))
        session = str(event.get("session_id", "unknown"))
        agent_id = str(event.get("agent_id", "root"))
        owner = (agent, session, agent_id)
        name = str(event.get("event", ""))
        timestamp = parse_time(event.get("ts"))
        if not timestamp:
            continue

        if name == "agent_started":
            counters[owner] = counters.get(owner, 0) + 1
            turn_id = str(event.get("turn_id") or counters[owner])
            turn = Turn(
                agent=agent,
                session_id=session,
                turn_id=turn_id,
                project=pathlib.Path(str(event.get("cwd", ""))).name or "?",
                model=str(event.get("model", "?")),
                started=timestamp,
                schema_version=(
                    cast(int, event["schema_version"])
                    if isinstance(event.get("schema_version"), int)
                    else None
                ),
            )
            active[owner] = turn
            turns.append(turn)
            continue

        turn = active.get(owner)
        event_turn_id = event.get("turn_id")
        if event_turn_id and turn and turn.turn_id != str(event_turn_id):
            turn = None
        if not turn and name not in {"session_started", "session_ended"}:
            turn = Turn(
                agent=agent,
                session_id=session,
                turn_id=str(event_turn_id or "unknown"),
                project=pathlib.Path(str(event.get("cwd", ""))).name or "?",
                model=str(event.get("model", "?")),
                started=timestamp,
                schema_version=(
                    cast(int, event["schema_version"])
                    if isinstance(event.get("schema_version"), int)
                    else None
                ),
            )
            active[owner] = turn
            turns.append(turn)
        if not turn:
            continue

        if name == "skill_activated" and isinstance(event.get("skill"), str):
            skill = str(event["skill"])
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
            if isinstance(verification, str) and status in {"passed", "failed"}:
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
            if turn.schema_version != 2:
                stats.legacy += 1
            elif not turn.ended:
                stats.ongoing += 1
            elif turn.verification_status and all(
                status == "passed" for status in turn.verification_status.values()
            ):
                stats.verified += 1
            elif turn.verification_status:
                stats.failed += 1
            else:
                stats.unverified += 1
            if turn.ended:
                stats.durations.append((turn.ended - turn.started).total_seconds())
    return result


PAGE_STYLE = """
:root { color-scheme: light; font-family: ui-sans-serif, system-ui, sans-serif; --line: #dce3ed; --panel: #f6f8fc; --muted: #526179; }
* { box-sizing: border-box; }
body { color: #17253c; background: #f9fafc; max-width: 1440px; margin: 0 auto; padding: 40px 24px 64px; line-height: 1.5; }
h1 { margin: 0 0 4px; letter-spacing: -.03em; } h2 { margin: 40px 0 8px; }
.meta, small, .note, .empty { color: var(--muted); }
nav { display: flex; gap: 16px; margin: 20px 0; border-bottom: 1px solid var(--line); }
nav a { padding: 8px 2px; color: inherit; text-decoration: none; }
nav a.active { border-bottom: 2px solid currentColor; font-weight: 700; }
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 24px 0; }
.card, .attention, .case { border: 1px solid var(--line); border-radius: 12px; padding: 16px 18px; background: var(--panel); }
.card strong { display: block; margin-top: 4px; font-size: 2rem; line-height: 1; }
.attention ul { margin: 8px 0 0; padding-left: 20px; }
.table-scroll { width: 100%; overflow-x: auto; border: 1px solid var(--line); border-radius: 12px; }
table { width: 100%; border-collapse: collapse; }
.skill-table { min-width: 760px; } .recent-table { min-width: 680px; }
th, td { border-bottom: 1px solid var(--line); padding: 11px 12px; text-align: right; vertical-align: top; }
th { background: var(--panel); font-size: .75rem; white-space: nowrap; cursor: pointer; }
tbody tr:last-child td { border-bottom: 0; } tbody tr:hover { background: var(--panel); }
td:first-child, .recent-table th:nth-child(-n+5), .recent-table td:nth-child(-n+5) { text-align: left; }
td small { display: block; font-size: .7rem; } a { color: inherit; text-underline-offset: 2px; }
.good { color: #22a06b; } .bad { color: #d74c4c; }
.detail { text-align: left; overflow-wrap: anywhere; }
.detail details { min-width: 0; max-width: 100%; } .detail summary, .case summary { cursor: pointer; overflow-wrap: anywhere; }
.detail details[open] { max-height: 360px; overflow: auto; padding: 8px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); }
.detail details[open] summary { position: sticky; top: -8px; z-index: 1; padding-bottom: 6px; background: var(--panel); }
.detail-panel ul { margin: 8px 0 0; padding-left: 18px; } .detail-panel li { margin: 6px 0; } .detail-panel li small { overflow-wrap: anywhere; }
.contract dl { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 6px 10px; margin: 10px 0 0; } .contract dt { font-weight: 700; } .contract dd { min-width: 0; margin: 0; overflow-wrap: anywhere; }
.note { max-width: 80ch; margin: 0 0 12px; }
.toolbar { display: flex; align-items: center; gap: 10px; margin: 24px 0 12px; }
.toolbar input { width: min(420px, 100%); padding: 9px 12px; border: 1px solid var(--line); border-radius: 8px; background: transparent; color: inherit; }
.case-list { display: grid; gap: 12px; } .case { padding: 0; overflow: hidden; }
.case > summary { display: grid; grid-template-columns: 2fr 1fr repeat(3, minmax(80px, .6fr)); gap: 12px; padding: 14px 16px; align-items: center; }
.case > summary small { display: block; } .case-body { padding: 0 16px 16px; border-top: 1px solid var(--line); }
.case-body table { margin-top: 12px; } .toggle { margin-top: 10px; }
th[aria-sort=ascending]::after { content: " ↑"; } th[aria-sort=descending]::after { content: " ↓"; }
th:focus-visible, input:focus-visible, summary:focus-visible { outline: 2px solid #4b9; outline-offset: 2px; }
[hidden] { display: none !important; }
@media (max-width: 900px) {
  body { padding: 24px 14px 48px; } .cards { grid-template-columns: repeat(2, 1fr); }
  .table-scroll { overflow: visible; border: 0; }
  table, tbody { display: block; min-width: 0 !important; } thead { display: none; }
  tbody { display: grid; gap: 12px; }
  tbody tr { display: block; overflow: hidden; border: 1px solid var(--line); border-radius: 12px; background: var(--panel); }
  tbody td { display: grid; grid-template-columns: minmax(110px, 34%) 1fr; gap: 12px; width: 100%; max-width: none; padding: 10px 12px; text-align: left !important; overflow-wrap: anywhere; }
  tbody td[data-label]::before { content: attr(data-label); color: var(--muted); font-size: .75rem; font-weight: 700; }
  tbody td:last-child { border-bottom: 0; }
  .case > summary { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 520px) { .cards { grid-template-columns: 1fr; } .case > summary, tbody td { grid-template-columns: 1fr; gap: 2px; } }
nav { gap: 6px; padding: 6px; background: #edf1f7; border: 0; border-radius: 12px; width: fit-content; }
nav a { padding: 10px 18px; border-radius: 8px; }
nav a.active { background: white; box-shadow: 0 1px 4px #17253c15; border: 0; color: #254eb8; }
.card { background: white; text-align: left; color: inherit; font: inherit; }
button.card { cursor: pointer; }
.card[aria-pressed=true] { border-color: #315bd2; box-shadow: 0 0 0 2px #315bd225; }
.cards { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
button, select, input { font: inherit; } button, select { cursor: pointer; }
.toolbar { flex-wrap: wrap; background: white; padding: 16px; border: 1px solid var(--line); border-radius: 12px; }
.toolbar select, .toolbar button { padding: 9px 12px; border: 1px solid var(--line); background: white; border-radius: 8px; color: inherit; }
.skill-profile > summary { grid-template-columns: minmax(0, 1fr) auto; }
.case-list { margin-top: 16px; }
details[id] { scroll-margin-top: 20px; }
.operations-table { table-layout: fixed; background: white; }
.operations-table th, .operations-table td { text-align: left; padding: 18px; }
.operations-table th { cursor: default; }
.operations-table td { overflow-wrap: anywhere; }
.operations-table th:first-child { width: 28%; }
.operations-table small { font-size: .8rem; line-height: 1.65; margin-top: 8px; }
.operations-table details { margin-top: 10px; }
.operations-table details[open] { background: #f6f8fc; padding: 12px; border-radius: 8px; }
.operations-table summary { cursor: pointer; color: #31549b; font-size: .85rem; }
.operations-table ul { padding-left: 20px; max-height: 260px; overflow: auto; font-size: .85rem; }
.status-badge { display: inline-block; font-size: .8rem; padding: 4px 9px; background: #fff3db; color: #76500c; border-radius: 6px; font-weight: 600; }
[data-group=ready] .status-badge { background: #e9efff; color: #294ca7; }
[data-group=decided] .status-badge { background: #e4f5ed; color: #236449; }
.empty-results { padding: 32px; text-align: center; border: 1px dashed var(--line); border-radius: 12px; }
:focus-visible { outline: 3px solid #315bd2; outline-offset: 3px; }
@media(max-width:900px) {
 .operations-table td { display: block; }
 .operations-table td[data-label]::before { display: block; margin-bottom: 8px; }
 .operations-table tr { background: white; }
 .toolbar input { flex: 1 1 180px; }
}
@media(prefers-reduced-motion:reduce) { * { scroll-behavior: auto !important; } }

"""

PAGE_SCRIPT = """
(() => {
  const rows = [...document.querySelectorAll('.search-row')];
  const search = document.querySelector('#search');
  const count = document.querySelector('#result-count');
  const filter = document.querySelector('#state-filter');
  const empty = document.querySelector('#empty-results');
  const update = () => {
    const query = search ? search.value.trim().toLocaleLowerCase() : '';
    let visible = 0;
    rows.forEach(row => {
      const matches = (!query || row.textContent.toLocaleLowerCase().includes(query)) && (!filter || filter.value === 'all' || row.dataset.group === filter.value);
      row.hidden = !matches || (!query && row.classList.contains('recent-extra'));
      if (!row.hidden) visible++;
    });
    if (count) count.textContent = filter ? `${visible} / ${rows.length}ラウンド` : query ? `${visible}件` : '';
    if (empty) empty.hidden = visible !== 0 || rows.length === 0;
    document.querySelectorAll('[data-filter]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.filter === filter?.value)));
  };
  search?.addEventListener('input', update);
  filter?.addEventListener('change', update);
  document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => { filter.value = button.dataset.filter; update(); }));
  document.querySelector('#reset-filters')?.addEventListener('click', () => { search.value = ''; filter.value = 'all'; update(); search.focus(); });
  update();
  const revealAnchor = () => {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const target = id && document.getElementById(id);
    if (!target) return;
    if (search) search.value = '';
    if (filter) filter.value = 'all';
    update();
    for (let node = target; node; node = node.parentElement) {
      if (node.tagName === 'DETAILS') node.open = true;
    }
    target.scrollIntoView({block: 'start'});
  };
  if (typeof window !== 'undefined') {
    window.addEventListener('hashchange', revealAnchor);
    document.querySelectorAll('a[href^="#"]').forEach(link => link.addEventListener('click', () => setTimeout(revealAnchor, 0)));
    revealAnchor();
  }
  document.querySelectorAll('table:not(.operations-table)').forEach(table => {
    table.querySelectorAll('thead th').forEach((header, index) => {
      header.tabIndex = 0;
      header.title = 'クリックで並び替え';
      const sort = () => {
        const body = table.tBodies[0];
        const order = header.dataset.order === 'asc' ? 'desc' : 'asc';
        [...body.rows].filter(row => row.cells.length > index).sort((a, b) => a.cells[index].textContent.trim().localeCompare(b.cells[index].textContent.trim(), 'ja', { numeric: true }) * (order === 'desc' ? -1 : 1)).forEach(row => body.append(row));
        table.querySelectorAll('th').forEach(item => item.removeAttribute('aria-sort'));
        header.dataset.order = order;
        header.setAttribute('aria-sort', order === 'asc' ? 'ascending' : 'descending');
      };
      header.addEventListener('click', sort);
      header.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); sort(); } });
    });
  });
  document.querySelector('#show-all')?.addEventListener('click', event => {
    document.querySelectorAll('.recent-extra').forEach(row => { row.classList.remove('recent-extra'); row.hidden = false; });
    event.currentTarget.hidden = true;
  });
})();
"""


def render_page(title: str, days: int, generated: str, active: str, body: str) -> str:
    nav = (
        f'<nav><a href="report.html" class="{"active" if active == "operations" else ""}">改善状況</a>'
        f'<a href="usage.html" class="{"active" if active == "overview" else ""}">利用履歴</a>'
        f'<a href="evals.html" class="{"active" if active == "evaluations" else ""}">比較評価</a></nav>'
    )
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html.escape(title)}</title><style>{PAGE_STYLE}</style></head><body>
<h1>{html.escape(title)}</h1><div class=meta>{"保存済みの全ラウンド" if active == "operations" else f"直近{days}日"} · 更新 {html.escape(generated)} · 自動更新なし</div>
{nav}{body}<script>{PAGE_SCRIPT}</script></body></html>"""


def render_overview(days: int, turns: list[Turn], stats: dict[str, SkillStats]) -> str:
    generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    locations = load_skill_locations()
    total_uses = sum(item.uses for item in stats.values())
    total_verified = sum(item.verified for item in stats.values())
    total_failed = sum(item.failed for item in stats.values())
    total_unverified = sum(item.unverified for item in stats.values())

    skill_rows = []
    for skill, item in sorted(stats.items(), key=lambda pair: (-pair[1].uses, pair[0])):
        finished = item.verified + item.failed + item.unverified
        rate = f"{item.verified / finished:.0%}" if finished else "—"
        version = next(iter(sorted(item.versions)), "—")
        last_used = (
            item.last_used.astimezone().strftime("%m-%d %H:%M")
            if item.last_used
            else "—"
        )
        median_seconds = statistics.median(item.durations) if item.durations else 0
        detail = (
            "<details><summary>詳細</summary>"
            f"<small>{html.escape(version[:19])} · {skill_status(skill, locations)}</small>"
            f"<small>平均tool {item.tools / item.uses:.1f} · 時間中央値 {median_seconds:.0f}s · 旧形式 {item.legacy}</small>"
            f"<small>{format_tool_counts(item.tool_counts)}</small></details>"
        )
        skill_rows.append(
            f'<tr class="data-row search-row"><td data-label="スキル"><strong>{skill_link(skill, locations)}</strong>{detail}</td>'
            f'<td data-label="利用回数">{item.uses}</td><td data-label="検証済" class=good>{item.verified}</td>'
            f'<td data-label="失敗" class=bad>{item.failed}</td><td data-label="未検証">{item.unverified}</td>'
            f'<td data-label="作業検証の成功率">{rate}</td><td data-label="最終利用">{last_used}</td></tr>'
        )
    if not skill_rows:
        skill_rows.append(
            '<tr><td colspan="7" class=empty>skill利用データはまだありません。</td></tr>'
        )

    relevant = sorted(
        (turn for turn in turns if turn.skills),
        key=lambda turn: turn.started,
        reverse=True,
    )
    attention = [
        turn for turn in relevant if turn_outcome(turn) in {"検証失敗", "未検証"}
    ][:5]
    attention_html = (
        "<ul>"
        + "".join(
            f"<li><strong>{html.escape(turn_outcome(turn))}</strong> · {html.escape(', '.join(sorted(turn.skills)))} · {html.escape(turn.project)}</li>"
            for turn in attention
        )
        + "</ul>"
        if attention
        else "<p class=note>表示期間内に検証失敗・未検証の作業記録はありません。</p>"
    )

    recent_rows = []
    for index, turn in enumerate(relevant[:50]):
        extra = " recent-extra" if index >= 10 else ""
        hidden = " hidden" if index >= 10 else ""
        recent_rows.append(
            f'<tr class="data-row search-row{extra}"{hidden}>'
            f'<td data-label="時刻">{turn.started.astimezone().strftime("%m-%d %H:%M")}</td>'
            f'<td data-label="エージェント">{html.escape(turn.agent)}</td><td data-label="プロジェクト">{html.escape(turn.project)}</td>'
            f'<td data-label="スキル">{html.escape(", ".join(sorted(turn.skills)))}</td>'
            f'<td data-label="結果">{html.escape(turn_outcome(turn))}<small>{format_verifications(turn)}</small><details><summary>tool {turn.tools}</summary><small>{format_tool_counts(turn.tool_counts)}</small></details></td></tr>'
        )
    if not recent_rows:
        recent_rows.append(
            '<tr><td colspan="5" class=empty>該当する作業記録はありません。</td></tr>'
        )
    toggle = (
        f"<button id=show-all class=toggle>{min(len(relevant), 50)}件すべて表示</button>"
        if len(relevant) > 10
        else ""
    )

    body = f"""
<div class=cards><div class=card><span>利用回数</span><strong>{total_uses}</strong></div>
<div class=card><span>検証済</span><strong>{total_verified}</strong></div>
<div class=card><span>検証失敗</span><strong class=bad>{total_failed}</strong></div>
<div class=card><span>未検証</span><strong>{total_unverified}</strong></div></div>
<section class=attention><strong>要確認</strong>{attention_html}</section>
<div class=toolbar><label for=search>検索</label><input id=search type=search placeholder="スキル名・プロジェクト名・エージェント名を検索…"><span id=result-count class=note></span></div>
<h2>スキル別の利用と作業検証</h2><div class=table-scroll><table class=skill-table><thead><tr><th>スキル</th><th>利用回数</th><th>検証済</th><th>失敗</th><th>未検証</th><th>作業検証の成功率</th><th>最終利用</th></tr></thead>
<tbody>{"".join(skill_rows)}</tbody></table></div>
<h2>最近の利用</h2><div class=table-scroll><table class=recent-table><thead><tr><th>時刻</th><th>エージェント</th><th>プロジェクト</th><th>スキル</th><th>結果</th></tr></thead>
<tbody>{"".join(recent_rows)}</tbody></table></div>{toggle}
<p class=note>利用回数はスキルごとの作業記録数です。1つの作業で複数のスキルを使うと、その分を重複して数えます。作業検証の成功率は、新形式（schema v2）の終了済み記録のうち、記録された全検証カテゴリの最終結果が成功した割合です。検証記録がない作業も分母に含み、旧形式・終了記録なしは含みません。スキル自体の有用性を表す数値ではありません。</p>"""
    return render_page("利用履歴", days, generated, "overview", body)


def render_artifacts(items):
    groups = {}
    for item in items:
        if item.get("artifacts"):
            groups.setdefault(
                (str(item.get("experiment_id")), item.get("run")), []
            ).append(item)
    sections = []
    for (experiment, run), values in groups.items():
        links = []
        for item in values:
            directory = pathlib.Path(item["artifacts"])
            if not directory.is_absolute():
                continue
            label = html.escape(str(item["variant"]))
            links.append(
                f'<li>{label}: <a href="{html.escape((directory / "index.html").as_uri(), quote=True)}">アウトプットとtrace</a> · <a href="{html.escape((directory / "review.json").as_uri(), quote=True)}">採点票</a> · 目的採点 {"未採点" if item.get("success") is None else "合格" if item.get("success") else "不合格"} · tokens {item.get("total_tokens") if item.get("total_tokens") is not None else "不明"}</li>'
            )
        sections.append(
            f"<details><summary>比較 {html.escape(experiment[:8])} / {run}</summary><ul>{''.join(links)}</ul></details>"
        )
    return (
        "<h3>アウトプット比較</h3>" + "".join(sections)
        if sections
        else "<p>保存済みアウトプットなし</p>"
    )


def read_round_states(root):
    spec = importlib.util.spec_from_file_location("current_skill_loop", pathlib.Path(__file__).resolve().with_name("skill-loop.py"))
    loop = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loop)
    return collect_rounds(root, loop.status)


def render_skill_dashboard(cases, results, locations, *, root=None, link_prefix=""):
    root = ROOT if root is None else root
    rounds = read_round_states(root)
    cases_dir = pathlib.Path(
        os.environ.get(
            "AGENT_EVAL_CASES_DIR",
            str(pathlib.Path(__file__).resolve().parents[1] / ".agents/evals"),
        )
    )
    catalog = load_catalog()
    source_root = pathlib.Path(__file__).resolve().parents[1] / ".agents"
    catalog = {name: profile for name, profile in catalog.items() if (source_root / profile['path']).is_file()}
    rows = skill_summary(catalog, cases, results, cases_dir)
    cards = []
    for row in rows:
        profile_path = (
            pathlib.Path(__file__).resolve().parents[1] / ".agents" / row["path"]
        )
        case_links = (
            "".join(
                f'<li><a href="{link_prefix}#{html.escape(c["case"])}">{html.escape(c["case"])}</a>: {html.escape(c["reason"])}</li>'
                for c in row["cases"]
            )
            or "<li>目的別ケース未作成</li>"
        )
        matching = [r for r in rounds if r["skill"] == row["skill"]]
        judgment, valid = decision_state(matching)
        decision_details = "".join(
            '<li><a href="' + html.escape((r['directory'] / 'decision.json').resolve().as_uri()) + '">判断記録</a>：' + html.escape(str(r['decision'].get('reason', ''))) +
            '<br>適用上の限界：' + html.escape(str(r['decision'].get('limitations', ''))) +
            '<br>次の確認条件：' + html.escape(str(r['decision'].get('next_check', ''))) + '</li>' for r in valid)
        invalid_count = len(matching) - len(valid)
        placement = deployment_state(profile_path, locations.get(row['skill']))
        search_class = "" if link_prefix else " search-row"
        cards.append(
            f'<details class="case skill-profile{search_class}"><summary><strong>{html.escape(row["skill"])}</strong><span>{html.escape(judgment)}</span></summary><div class=case-body>'
            f'<p><b>現在の配置</b> {html.escape(placement)}</p><p><b>有効な判断</b> {html.escape(judgment)}</p><ul>{decision_details}</ul><p>現行条件で判断に使えない記録：{invalid_count}件。古い計画・証拠不足を含みます。</p>'
            f"<p><b>目的</b> {html.escape(row['purpose'])}</p><p><b>評価する証拠</b> {html.escape(row['evidence'])}</p>"
            f"<p><b>比較評価の信号</b> {LABELS[row['recommendation']]}：{html.escape(row['reason'])}</p><p><b>共有台帳の記載（各ラウンドの判断は改善状況へ）</b> {LABELS.get(row['decision'], row['decision'])}: {html.escape(row['decision_reason'])}</p>"
            f'<p><b>スクリプト化候補</b> {html.escape(row["script_candidate"])}</p><p><a href="{profile_path.as_uri()}">Skill本文</a> · {html.escape(row["source"])}</p><ul>{case_links}</ul></div></details>'
        )
    return (
        "<h2>スキルごとの評価状況</h2><p>未評価は不要を意味しません。旧ケース、採点待ち、変更後の古い結果から採否を決めません。採否は根拠と代替手段を確認し、各ラウンドの判断記録へ残します。</p>"
        + "".join(cards)
    )


def render_evaluations(days: int, results: list[dict[str, object]]) -> str:
    generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    locations = load_skill_locations()
    cases = load_eval_cases()
    result_cases = {str(item.get("case")) for item in results if item.get("case")}
    case_ids = sorted(set(cases) | result_cases)
    cards = []
    statuses: dict[str, int] = {"継続候補": 0, "要レビュー": 0, "結果未記録": 0, "判断保留": 0}

    for case_id in case_ids:
        case = cases.get(case_id)
        items = [item for item in results if str(item.get("case")) == case_id]
        experiments: dict[str, list[dict[str, object]]] = {}
        for item in items:
            experiments.setdefault(str(item.get("experiment_id", "legacy")), []).append(
                item
            )
        latest_items = (
            max(
                experiments.values(),
                key=lambda group: max(str(item.get("ts", "")) for item in group),
            )
            if experiments
            else []
        )
        control = [item for item in latest_items if item.get("variant") == "control"]
        treatment = [
            item for item in latest_items if item.get("variant") == "treatment"
        ]
        cases_dir = pathlib.Path(os.environ.get("AGENT_EVAL_CASES_DIR", str(pathlib.Path(__file__).resolve().parents[1] / ".agents/evals")))
        try:
            current_version = contract_version(case, cases_dir / (case_id + ".json")) if case else "missing"
        except (OSError, KeyError, TypeError, ValueError):
            current_version = "invalid"
        signal, reason, _ = case_verdict(case or {}, latest_items, current_version=current_version)
        status = {
            "unassessed": "結果未記録",
            "keep": "継続候補",
            "revise": "要レビュー",
            "hold": "判断保留",
            "neutral": "判断保留",
        }[signal]
        statuses[status] += 1
        skill = (
            str(case.get("skill", "?"))
            if case
            else str(items[0].get("skill", "?"))
            if items
            else "?"
        )
        latest = max((str(item.get("ts", "")) for item in latest_items), default="—")[
            :10
        ]
        experiment_rows = render_eval_rows(
            items, locations, cases, include_contract=False
        )
        contract = render_eval_contract(case)
        cards.append(
            f'<details class="case search-row" id="{html.escape(case_id, quote=True)}"><summary>'
            f"<span><strong>{html.escape(case_id)}</strong><small>{skill_link(skill, locations)}</small></span>"
            f"<span>{html.escape(status)}</span><span>なし {len(control)}</span><span>あり {len(treatment)}</span><span>{html.escape(latest)}</span></summary>"
            f"<div class=case-body><p><b>判定理由</b> {html.escape(reason)}</p><p>{html.escape(str((case or {}).get('evaluation', {}).get('reason', '目的別評価')))}</p>{contract}{render_artifacts(items)}<h3>実験履歴</h3><div class=table-scroll><table><thead><tr><th>スキル / ケース</th><th>エージェント</th><th>モデル / 実験</th><th>スキルなし・成功</th><th>スキルあり・成功</th><th>成功率差</th><th>判定</th><th>変更行</th><th>追加クラス数</th><th>失敗詳細</th></tr></thead>"
            f"<tbody>{experiment_rows}</tbody></table></div></div></details>"
        )

    skill_dashboard = render_skill_dashboard(cases, results, locations)
    body = f"""
<p class=note>比較評価は自動実行されません。保存済み結果の閲覧と、モデルを呼ばない計画確認は利用できます。</p><details><summary>評価を実行するには</summary><p>計画・入力・隔離環境を確認し、許可された範囲で明示的に実行してください。</p></details>
<div class=toolbar><label for=search>検索</label><input id=search type=search placeholder="ケース名・スキル名・モデル名を検索…"><span id=result-count class=note></span></div>
{skill_dashboard}
<h2>ケースと履歴</h2>
<div class=cards><div class=card><span>評価ケース数</span><strong>{len(case_ids)}</strong></div>
<div class=card><span>継続候補</span><strong class=good>{statuses["継続候補"]}</strong></div>
<div class=card><span>要レビュー</span><strong class=bad>{statuses["要レビュー"]}</strong></div>
<div class=card><span>結果未記録 / 判断保留</span><strong>{statuses["結果未記録"] + statuses["判断保留"]}</strong></div></div>
<p class=note>同じテストデータ・課題・検証プログラムで、対象スキルの有無を比較します。「継続候補」は比較結果からの候補であり、採用決定ではありません。「結果未記録」は表示期間内に結果がない状態で、未実行とは限りません。</p>

<div class=case-list>{"".join(cards) or "<p class=empty>評価ケースはまだありません。</p>"}</div>"""
    return render_page("比較評価", days, generated, "evaluations", body)


def render_operations(days: int, root: pathlib.Path) -> str:
    """Read existing rounds without running models or changing evaluation state."""
    skill_loop = pathlib.Path(__file__).resolve().parent / "skill-loop.py"
    spec = importlib.util.spec_from_file_location("dashboard_skill_loop", skill_loop)
    loop = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loop)
    labels = {"needs-plan": "計画の修正待ち", "ready": "評価の実行待ち",
              "execution-incomplete": "実行記録の確認待ち", "needs-review": "採点待ち",
              "needs-decision": "判断待ち", "decided": "判断済み", "invalid": "記録を読めません"}
    actions = {"repair-plan": "計画の不足・条件変更を確認", "run": "許可された範囲で評価を実行",
               "inspect-logs-no-retry": "部分結果と消費済み呼び出しを確認（自動再試行なし）",
               "review-artifacts-and-trace": "成果物と実行記録を採点", "record-decision": "判断と根拠を記録",
               "repair-decision": "判断の不足を修正", "next-round-or-stop": "次の評価へ進むか終了する"}
    decisions = {"keep": "継続", "revise": "修正継続", "adopt": "採用", "disable": "無効化", "hold": "保留"}
    rows = []
    counts = {"attention": 0, "ready": 0, "decided": 0}
    unidentified = 0
    catalog = load_catalog()
    source_root = pathlib.Path(__file__).resolve().parents[1] / ".agents"
    current_names = {name for name, profile in catalog.items() if (source_root / profile['path']).is_file()}
    for directory in sorted((root / "eval-loops").glob("*")):
        if not directory.is_dir():
            continue
        try:
            state = loop.status(directory)
        except Exception as error:
            state = {"state": "invalid", "errors": [str(error)], "skill": directory.name}
        if state.get("skill") not in current_names:
            if not state.get('skill') or state.get('state') == 'invalid':
                unidentified += 1
            continue
        key = state["state"]
        counts[key if key in ("ready", "decided") else "attention"] += 1
        decision = {}
        try:
            decision = json.loads((directory / "decision.json").read_text())
            if not isinstance(decision, dict):
                decision = {}
        except (OSError, ValueError):
            pass
        escape = lambda value: html.escape(str(value))
        evidence = "".join("<li>" + escape(value) + "</li>" for value in state.get("errors", []))
        detail = '<details><summary>不足・条件の確認（' + str(len(state.get('errors', []))) + '件）</summary><ul>' + evidence + '</ul></details>' if evidence else ''
        reason = escape(decision.get("reason", "判断の記録なし"))
        if decision:
            reason = escape(decisions.get(decision.get("action"), decision.get("action", ""))) + "：" + reason
            if key != "decided":
                reason = "未確定の記録：" + reason
        links = ' · '.join('<a href="' + escape((directory / name).resolve().as_uri()) + '">' + label + '</a>'
                           for name, label in [("plan.json", "計画"), ("decision.json", "判断の原本")]
                           if (directory / name).is_file())
        group = key if key in ("ready", "decided") else "attention"
        rows.append('<tr class="search-row" data-group="' + group + '"><td data-label="スキル"><strong>' + escape(state.get("skill") or directory.name) + '</strong><details><summary>ラウンド・記録</summary><small>' + escape(directory.name) + '</small><small>' + links + '</small></details></td><td data-label="次の作業"><span class="status-badge">' + labels.get(key, escape(key)) + '</span><small>' + escape(actions.get(state.get("next_action"), "記録形式を確認")) + '</small>' + detail + '</td><td data-label="判断"><details><summary>' + ('判断の根拠を見る' if key == 'decided' else '未確定の記録を見る' if decision else '判断の記録なし') + '</summary><p>' + reason + '</p></details></td></tr>')
    body = '<p>実作業で見つかった課題を、比較・採点・判断へつなぐ入口です。利用回数や通常作業のテスト成功は、スキルの有用性を示す評価ではありません。</p>'
    body += '<div class="cards">' + ''.join('<button type="button" class="card" data-filter="' + key + '" aria-pressed="false"><span>' + label + '</span><strong>' + str(counts[key]) + '</strong></button>' for key, label in [("attention", "確認・修正待ち"), ("ready", "実行待ち"), ("decided", "判断済み")]) + '</div>'
    body += '<p class="note">ラウンド（1つの計画に基づく比較評価）単位の件数です。同じスキルの複数ラウンドも別に表示します。状態は生成時点の検査結果で、実行中かどうかは推測しません。</p>'
    body += '<div class="toolbar"><label for="search">絞り込み</label><input id="search" type="search" placeholder="スキル・状態・判断を検索"><select id="state-filter" aria-label="状態で絞り込み"><option value="all">すべての状態</option><option value="attention">確認・修正待ち</option><option value="ready">実行待ち</option><option value="decided">判断済み</option></select><button id="reset-filters" type="button">条件をクリア</button><span id="result-count" role="status" aria-live="polite"></span></div><h2>改善の進捗と次の作業</h2><div class="table-scroll"><table class="operations-table"><thead><tr><th>スキル / 評価計画</th><th>状態と次の作業</th><th>判断と根拠</th></tr></thead><tbody>'
    body += ''.join(rows) or '<tr><td colspan="3">評価ラウンドはありません。実作業で再現できる課題が見つかったら、既存ケースを確認して計画を作成します。</td></tr>'
    body += '</tbody></table></div><p id="empty-results" class="empty-results" hidden>条件に一致するラウンドはありません。検索語か状態を変更するか、条件をクリアしてください。</p><details><summary>運用の流れと表示範囲</summary><p>実作業で課題を発見し、再現可能で重複しないケースを追加。許可された比較評価、成果物の採点、判断の記録を経て、必要な変更をPRへ反映します。</p><p>外部から導入したスキルは利用判断、自作スキルは利用判断と改善が対象です。状態表示からモデル実行や配置は始まりません。古い条件・欠落した証拠は不足として表示されます。判断済みでも配置済みを意味しません。</p></details>'
    body += '<h2>現行スキルの配置と利用判断</h2><p>版照合は探索対象の共有配置先について行います。全エージェントの読み込み・選択を保証しません。最新順が保証できない判断は勝手に優先せず、複数の有効な判断が競合したら要確認とします。</p>'
    body += render_skill_dashboard(load_eval_cases(), load_eval_results(days), load_skill_locations(), root=root, link_prefix="evals.html")
    if unidentified:
        body += '<p class=note>対象を特定できない記録が' + str(unidentified) + '件あります。記録を読めません。未確定の記録は現在の採否に使いません。</p>'
    return render_page("スキル運用", days, datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"), "operations", body)


def write_report(content: str, output: pathlib.Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".report-", dir=output.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, output)
    finally:
        pathlib.Path(temp_name).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--open", action="store_true", dest="open_report")
    args = parser.parse_args()
    days = max(1, args.days)
    output = ROOT / "report.html"
    eval_output = ROOT / "evals.html"
    turns = build_turns(load_events(days))
    eval_results = load_eval_results(days)
    write_report(render_operations(days, ROOT), output)
    write_report(render_overview(days, turns, aggregate(turns)), ROOT / "usage.html")
    write_report(render_evaluations(days, eval_results), eval_output)
    if args.open_report:
        subprocess.run(["open", str(output)], check=False)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
