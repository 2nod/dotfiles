#!/usr/bin/env python3
"""Generate a local HTML report from agent observability JSONL events."""

from __future__ import annotations

import argparse
import importlib.util
import html
import json
import math
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
    load_catalog,
    skill_summary,
    case_verdict,
    contract_version,
    reviewed_result,
    LABELS,
)

from report_validation import validate_pages
from report_evidence import EvidenceSnapshot, load_reference_runs, result_counts
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


def load_eval_results(days: int, root=None) -> list[dict[str, object]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    results: list[dict[str, object]] = []
    for path in sorted(((ROOT if root is None else root) / "eval-results").glob("*.jsonl")):
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


def number_value(value: object, default: float = 0) -> float:
    try:
        return float(value) if isinstance(value, (int, float)) else default
    except (TypeError, ValueError):
        return default


def format_median(values):
    measured = [value for value in values if type(value) in (int, float) and math.isfinite(value)]
    return f"{statistics.median(measured):.0f}" if measured else "—"


def format_duration(value):
    return f"{value:.1f}秒" if type(value) in (int, float) and math.isfinite(value) and value >= 0 else "未記録"


def local_artifact_link(path, label):
    if path.is_file():
        return '<a href="' + html.escape(path.resolve().as_uri(), quote=True) + '">' + html.escape(label) + '</a>'
    return '<span class="note">' + html.escape(label) + '：未保存・参照先なし</span>'


def render_eval_details(items: list[dict[str, object]]) -> str:
    counts = result_counts(items)
    failures = [item for item in items if item.get("success") is False]
    pending = f'<p class="note">{counts["pending"]}件の未採点・確認不明</p>' if counts["pending"] else ""
    if not failures:
        return '<span class="note">確認済みの失敗なし</span>' + pending
    entries = []
    for item in sorted(
        failures,
        key=lambda value: (
            str(value.get("variant")),
            number_value(value.get("run")),
        ),
    ):
        kind = str(item.get("failure_kind", "原因未記録"))
        if kind == "passed":
            kind = "実行は正常終了・目的採点は不合格"
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
            f"{html.escape(kind)} · {format_duration(item.get('duration_seconds'))}"
            f"{f'<small>{html.escape(facts)}</small>' if facts else ''}</li>"
        )
    return f"<details class=detail-panel><summary>{len(failures)}件の失敗</summary><ul>{''.join(entries)}</ul></details>" + pending


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
        "<details class=contract><summary>登録ケースの条件を見る</summary><p class=note>現在登録されている定義です。過去の実行条件や参考検証の変更点は、履歴・元レポートで確認してください。</p>"
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
        control_success = result_counts(control)["passed"]
        treatment_success = result_counts(treatment)["passed"]
        fully_scored = bool(control and treatment) and all(
            type(item.get("success")) is bool for item in control + treatment
        )
        rate_difference = (
            f"{(treatment_success / len(treatment) - control_success / len(control)) * 100:+.0f}pt"
            if fully_scored else "—（未採点・片側欠落）"
        )
        def score_label(items):
            counts = result_counts(items)
            passed, pending = counts["passed"], counts["pending"]
            return f"{passed}/{len(items)}" + (f"（未採点 {pending}）" if pending else "")
        successful_control = [item for item in control if item.get("success") is True]
        successful_treatment = [item for item in treatment if item.get("success") is True]
        control_lines = format_median([item.get("changed_lines") for item in successful_control])
        treatment_lines = format_median([item.get("changed_lines") for item in successful_treatment])
        control_classes = format_median([item.get("classes_added") for item in successful_control])
        treatment_classes = format_median([item.get("classes_added") for item in successful_treatment])
        cases_dir = pathlib.Path(os.environ.get("AGENT_EVAL_CASES_DIR", str(pathlib.Path(__file__).resolve().parents[1] / ".agents/evals")))
        try:
            current_version = contract_version(cases[case], cases_dir / (case + ".json")) if case in cases else "missing"
        except (OSError, KeyError, TypeError, ValueError):
            current_version = "invalid"
        signal, reason, paired_runs = case_verdict(
            cases.get(case, {}), control + treatment, current_version=current_version
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
            f'<td data-label="なし成功">{score_label(control)}</td>'
            f'<td data-label="あり成功">{score_label(treatment)}</td>'
            f'<td data-label="成功率差">{rate_difference}</td>'
            f'<td data-label="判定">{html.escape(verdict)}</td>'
            f'<td data-label="変更行 なし→あり">{control_lines} → {treatment_lines}</td>'
            f'<td data-label="追加class なし→あり">{control_classes} → {treatment_classes}</td>'
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
 .skill-case-group { margin: 12px 0; border: 1px solid var(--line); border-radius: 10px; background: var(--panel); }
.skill-case-group > summary { display: flex; justify-content: space-between; gap: 16px; padding: 16px; cursor: pointer; overflow-wrap: anywhere; }
.skill-case-group > summary::before { content: "▸"; }
.skill-case-group[open] > summary::before { content: "▾"; }
.skill-case-group > summary strong { flex: 1; }
.skill-case-body { padding: 0 12px 12px; }
.case[data-evidence="recorded"] { border: 2px solid #4772c3; margin: 10px 0; }
.case[data-evidence="recorded"] > summary { background: #eef4ff; }
.case[data-evidence="recorded"] .status-badge { background: #244f9e; color: #fff; }
.case[data-evidence="missing"] > summary { background: #f5f6f8; color: #525c69; }
.case[data-evidence="missing"] .status-badge { background: #e5e8ec; color: #525c69; }
.skill-case-group[data-has-records="true"] > summary { border-left: 5px solid #244f9e; background: #eef4ff; }

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
  const evidenceFilter = document.querySelector('#evidence-filter');
  const empty = document.querySelector('#empty-results');
  const update = () => {
    const query = search ? search.value.trim().toLocaleLowerCase() : '';
    let visible = 0;
    rows.forEach(row => {
      const matches = (!query || row.textContent.toLocaleLowerCase().includes(query)) && (!filter || filter.value === 'all' || row.dataset.group === filter.value) && (!evidenceFilter || evidenceFilter.value === 'all' || row.dataset.evidence === evidenceFilter.value);
      row.hidden = !matches || (!query && row.classList.contains('recent-extra'));
      if (!row.hidden) visible++;
    });
    document.querySelectorAll('.skill-case-group').forEach(group => {
      const matches = [...group.querySelectorAll('.search-row')].some(row => !row.hidden);
      group.hidden = !matches;
      if ((query || (evidenceFilter && evidenceFilter.value !== 'all')) && matches) group.open = true;
    });
    if (count) count.textContent = evidenceFilter ? `${visible} / ${rows.length}ケース` : filter ? `${visible} / ${rows.length}ラウンド` : query ? `${visible}件` : '';
    if (empty) empty.hidden = visible !== 0 || rows.length === 0;
    document.querySelectorAll('[data-filter]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.filter === filter?.value)));
  };
  search?.addEventListener('input', update);
  filter?.addEventListener('change', update);
  evidenceFilter?.addEventListener('change', update);
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
    if (evidenceFilter) evidenceFilter.value = 'all';
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
    update();
  });
})();
"""


SOURCE_LABELS = {"authored": "自作スキル", "installed": "外部導入スキル（installed）", "unknown": "区分未確認・複数区分"}


def source_group(catalog, skill):
    source = catalog.get(skill, {}).get("source")
    return source if source in ("authored", "installed") else "unknown"


def render_source_sections(groups, prefix, unit, before="", after=""):
    sections = []
    for source, label in SOURCE_LABELS.items():
        items = groups[source]
        if source == "unknown" and not items:
            continue
        content = before + "".join(items) + after if items else '<p class="empty">該当する記録はありません。</p>'
        sections.append(
            f'<section data-source="{source}"><h3 id="{prefix}-{source}">{label} <span class="note">{len(items)}{unit}</span></h3>{content}</section>'
        )
    links = " · ".join(
        f'<a href="#{prefix}-{source}">{label}（{len(groups[source])}{unit}）</a>'
        for source, label in SOURCE_LABELS.items() if source != "unknown" or groups[source]
    )
    return '<p class="source-links">' + links + '</p>' + "".join(sections)


def render_page(title: str, days: int, generated: str, active: str, body: str) -> str:
    nav = (
        f'<nav><a href="report.html" class="{"active" if active == "operations" else ""}">スキル一覧</a>'
        f'<a href="usage.html" class="{"active" if active == "overview" else ""}">利用履歴</a>'
        f'<a href="evals.html" class="{"active" if active == "evaluations" else ""}">検証結果</a></nav>'
    )
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html.escape(title)}</title><style>{PAGE_STYLE}</style></head><body>
<h1>{html.escape(title)}</h1><div class=meta>{"現在の管理スキル・保存済みの全ラウンド" if active == "operations" else f"ケース履歴は直近{days}日・保存済みレポートは全期間" if active == "evaluations" else f"直近{days}日"} · 更新 {html.escape(generated)} · 自動更新なし</div>
{nav}{body}<script>{PAGE_SCRIPT}</script></body></html>"""


def render_overview(days: int, turns: list[Turn], stats: dict[str, SkillStats]) -> str:
    generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    locations = load_skill_locations()
    total_uses = sum(item.uses for item in stats.values())
    total_verified = sum(item.verified for item in stats.values())
    total_failed = sum(item.failed for item in stats.values())
    total_unverified = sum(item.unverified for item in stats.values())
    total_no_end = sum(item.ongoing for item in stats.values())
    total_legacy = sum(item.legacy for item in stats.values())

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
        median_seconds = format_median(item.durations)
        duration_label = median_seconds + "秒" if median_seconds != "—" else "未記録"
        detail = (
            "<details><summary>詳細</summary>"
            f"<small>{html.escape(version[:19])} · {skill_status(skill, locations)}</small>"
            f"<small>平均tool {item.tools / item.uses:.1f} · 時間中央値 {duration_label} · 旧形式 {item.legacy}</small>"
            f"<small>{format_tool_counts(item.tool_counts)}</small></details>"
        )
        skill_rows.append(
            f'<tr class="data-row search-row"><td data-label="スキル"><strong>{skill_link(skill, locations)}</strong>{detail}</td>'
            f'<td data-label="利用回数">{item.uses}</td><td data-label="検証済" class=good>{item.verified}</td>'
            f'<td data-label="失敗" class=bad>{item.failed}</td><td data-label="未検証">{item.unverified}</td>'
            f'<td data-label="終了記録なし">{item.ongoing}</td><td data-label="旧形式">{item.legacy}</td>'
            f'<td data-label="作業検証の成功率">{rate}</td><td data-label="最終利用">{last_used}</td></tr>'
        )
    if not skill_rows:
        skill_rows.append(
            '<tr><td colspan="9" class=empty>skill利用データはまだありません。</td></tr>'
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
<div class=cards><div class=card><span>利用回数</span><strong data-metric="usage-total">{total_uses}</strong></div>
<div class=card><span>検証済</span><strong data-metric="usage-passed">{total_verified}</strong></div>
<div class=card><span>検証失敗</span><strong class=bad data-metric="usage-failed">{total_failed}</strong></div>
<div class=card><span>未検証</span><strong data-metric="usage-unverified">{total_unverified}</strong></div>
<div class=card><span>終了記録なし</span><strong data-metric="usage-no-end">{total_no_end}</strong></div>
<div class=card><span>旧形式</span><strong data-metric="usage-legacy">{total_legacy}</strong></div></div>
<section class=attention><strong>要確認</strong>{attention_html}</section>
<div class=toolbar><label for=search>検索</label><input id=search type=search placeholder="スキル名・プロジェクト名・エージェント名を検索…"><span id=result-count class=note></span></div>
<h2>スキル別の利用と作業検証</h2><div class=table-scroll><table class=skill-table><thead><tr><th>スキル</th><th>利用回数</th><th>検証済</th><th>失敗</th><th>未検証</th><th>終了記録なし</th><th>旧形式</th><th>作業検証の成功率</th><th>最終利用</th></tr></thead>
<tbody>{"".join(skill_rows)}</tbody></table></div>
<h2>最近の利用</h2><div class=table-scroll><table class=recent-table><thead><tr><th>時刻</th><th>エージェント</th><th>プロジェクト</th><th>スキル</th><th>結果</th></tr></thead>
<tbody>{"".join(recent_rows)}</tbody></table></div>{toggle}
<p class=note>利用回数はスキルごとの作業記録数で、検証済・検証失敗・未検証・終了記録なし・旧形式の合計です。終了記録なしは実行中とは限りません。1つの作業で複数のスキルを使うと、その分を重複して数えます。作業検証の成功率は、新形式（schema v2）の終了済み記録のうち、記録された全検証カテゴリの最終結果が成功した割合です。検証記録がない作業も分母に含み、旧形式・終了記録なしは含みません。スキル自体の有用性を表す数値ではありません。</p>"""
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
            label = html.escape(str(item.get("variant", "不明")))
            value = item.get("artifacts")
            if not isinstance(value, str) or not pathlib.Path(value).is_absolute():
                links.append(f'<li>{label}: 保存先のパスを確認できません</li>')
                continue
            directory = pathlib.Path(value)
            output_link = local_artifact_link(directory / "index.html", "アウトプットとtrace")
            review_link = local_artifact_link(directory / "review.json", "採点票")
            grade = "合格" if item.get("success") is True else "不合格" if item.get("success") is False else "未採点・確認不明"
            tokens = item.get("total_tokens")
            token_text = str(tokens) if type(tokens) in (int, float) and math.isfinite(tokens) else "不明"
            links.append(f'<li>{label}: {output_link} · {review_link} · 目的採点 {grade} · tokens {token_text}</li>')
        sections.append(
            f"<details><summary>比較 {html.escape(experiment[:8])} / {run}</summary><ul>{''.join(links)}</ul></details>"
        )
    return (
        "<h3>アウトプット比較</h3>" + "".join(sections)
        if sections
        else "<p>成果物の保存先は記録されていません。</p>"
    )


def read_round_states(root):
    spec = importlib.util.spec_from_file_location("current_skill_loop", pathlib.Path(__file__).resolve().with_name("skill-loop.py"))
    loop = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loop)
    return collect_rounds(root, loop.status)


def render_skill_dashboard(cases, results, locations, *, root=None, days=30, evidence=None):
    root = ROOT if root is None else root
    evidence = evidence or EvidenceSnapshot(root, cases, results, load_catalog(), locations)
    rounds = read_round_states(root)
    cases_dir = pathlib.Path(
        os.environ.get(
            "AGENT_EVAL_CASES_DIR",
            str(pathlib.Path(__file__).resolve().parents[1] / ".agents/evals"),
        )
    )
    catalog = evidence.catalog
    source_root = pathlib.Path(__file__).resolve().parents[1] / ".agents"
    catalog = {name: profile for name, profile in catalog.items() if (source_root / profile['path']).is_file()}
    rows = skill_summary(catalog, cases, results, cases_dir)
    cards = {source: [] for source in SOURCE_LABELS}
    for row in rows:
        profile_path = (
            pathlib.Path(__file__).resolve().parents[1] / ".agents" / row["path"]
        )
        case_links = (
            "".join(
                f'<li><a href="evals.html#{html.escape(c["case"])}">{html.escape(c["case"])}</a>: {html.escape(c["reason"])}</li>'
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
        coverage = evidence.coverage_label(row["skill"])
        comparison_label = LABELS[row["recommendation"]] if any(evidence.comparisons.get(case) for case in evidence.by_skill.get(row["skill"], [])) else "比較記録なし"
        cards[source_group(catalog, row["skill"])].append(
            f'<details class="case skill-profile" data-skill="{html.escape(row["skill"], quote=True)}"><summary><strong>{html.escape(row["skill"])}</strong><span>{html.escape(judgment)}</span><span>{coverage}</span></summary><div class=case-body>'
            f'<p><b>現在の配置</b> {html.escape(placement)}</p><p><b>有効な判断</b> {html.escape(judgment)}</p><ul>{decision_details}</ul><p>現行条件で判断に使えない記録：{invalid_count}件。古い計画・証拠不足を含みます。</p>'
            f"<p><b>目的</b> {html.escape(row['purpose'])}</p><p><b>評価する証拠</b> {html.escape(row['evidence'])}</p>"
            f"<p><b>実行記録</b> {coverage}。直近{days}日の比較と全期間の参考検証。採否とは別です。</p><p><b>直近{days}日のケース比較</b> {comparison_label}：{html.escape(row['reason'])}</p><p><b>共有台帳の記載（評価による採否とは別）</b> {LABELS.get(row['decision'], row['decision'])}: {html.escape(row['decision_reason'])}</p>"
            f'<p><b>スクリプト化候補</b> {html.escape(row["script_candidate"])}</p><p><a href="{profile_path.as_uri()}">Skill本文</a> · {SOURCE_LABELS[source_group(catalog, row["skill"])]}</p><ul>{case_links}</ul></div></details>'
        )
    return (
        '<h2 id="skill-status">採否と配置</h2><p>未評価は不要を意味しません。旧ケース、採点待ち、変更後の古い結果から採否を決めません。採否は根拠と代替手段を確認し、各ラウンドの判断記録へ残します。</p>'
        + render_source_sections(cards, "skills", "スキル")
    )


def render_saved_reports(root, evidence=None):
    cards = {source: [] for source in SOURCE_LABELS}
    evidence = evidence or EvidenceSnapshot(root, load_eval_cases(), [], load_catalog(), load_skill_locations())
    catalog, cases = evidence.catalog, evidence.cases
    for json_path, metadata in evidence.saved_reports:
        path = json_path.with_suffix(".md")
        if not path.is_file():
            path = json_path
        if not path.is_file():
            continue
        plan = metadata.get("plan", metadata.get("context", {}))
        plan = plan if isinstance(plan, dict) else {}
        conditions = " · ".join(str(plan[key]) for key in ("runtime", "model", "mode") if key in plan)
        if "runs" in plan:
            conditions += f" · 各条件{plan['runs']}回"
        conclusion = metadata.get("conclusion", {})
        conclusion = conclusion if isinstance(conclusion, dict) else {}
        reason = conclusion.get("reason", "条件・結果・限界はレポート本文を確認してください。")
        limitations = conclusion.get("limitations", [])
        limitations = limitations if isinstance(limitations, list) else [limitations]
        details = "".join("<li>" + html.escape(str(item)) + "</li>" for item in limitations)
        skills = {plan["skill"]} if isinstance(plan.get("skill"), str) else set()
        results = metadata.get("results", [])
        if isinstance(results, list):
            for result in results:
                if isinstance(result, dict):
                    skill = result.get("skill") or cases.get(str(result.get("case")), {}).get("skill")
                    if isinstance(skill, str):
                        skills.add(skill)
        sources = {source_group(catalog, skill) for skill in skills}
        source = next(iter(sources)) if len(sources) == 1 else "unknown"
        cards[source].append(
            '<details class="case"><summary><strong>' + html.escape(path.parent.name) + '</strong></summary><div class="case-body">'
            + '<p>' + html.escape(conditions) + '</p><p><b>記録された結論</b> ' + html.escape(str(reason)) + '</p>'
            + ('<p><b>評価の限界</b></p><ul>' + details + '</ul>' if details else '')
            + '<p><a href="' + html.escape(path.resolve().as_uri(), quote=True) + '">検証レポートを読む</a></p></div></details>'
        )
    return (
        '<h2 id="saved-reports">保存済みの検証レポート（全期間）</h2>'
        '<p>各レポートの実行条件・採点・限界を確認できます。単発の確認実験も含み、結果の成功は採用決定を意味しません。'
        'Codexなど別形式で保存した検証は、下のケース集計には含まれない場合があります。</p>'
        + render_source_sections(cards, "reports", "件")
    )



def render_execution_history(case_id, evidence):
    items = evidence.history.get(case_id, [])
    if not items:
        return '<h3>実行履歴（0件）</h3><p>表示範囲内の実行記録はありません。</p>'
    rows = []
    variants = {"control": "対象スキルなし", "treatment": "変更前スキル", "candidate": "修正版スキル"}
    for item in items:
        success = item.get("success")
        outcome = "成功" if success is True else "失敗" if success is False else "確認不明・未採点"
        status_class = "good" if success is True else "bad" if success is False else "note"
        seconds = item.get("duration_seconds")
        duration = format_duration(seconds)
        paths = []
        value = item.get("artifacts")
        if isinstance(value, str) and pathlib.Path(value).is_absolute():
            folder = pathlib.Path(value)
            paths.extend((folder / name, label) for name, label in (("final.txt", "最終出力"), ("trace.jsonl", "実行ログ"), ("review.json", "確認記録"), ("index.html", "成果物")))
        if item.get("report"):
            paths.append((pathlib.Path(item["report"]), "元レポート"))
        links = " · ".join('<a href="' + html.escape(path.resolve().as_uri(), quote=True) + '">' + label + '</a>' for path, label in paths if path.is_file()) or "参照できる成果物なし"
        kind = "参考検証" if item["kind"] == "reference" else "比較評価"
        variant = variants.get(item.get("variant"), str(item.get("variant", "不明")))
        if item.get("variant") == "treatment" and not any(row.get("variant") == "candidate" and row["kind"] == item["kind"] for row in items):
            variant = "対象スキルあり"
        rows.append(
            f'<tr data-history-case="{html.escape(case_id, quote=True)}" data-history-kind="{item["kind"]}">'
            f'<td>{kind}</td><td>{html.escape(variant)}</td><td class="{status_class}">{outcome}</td>'
            f'<td>{html.escape(str(item.get("model", "不明")))}<small>{html.escape(str(item.get("agent", "不明")))}</small></td>'
            f'<td>{duration}</td><td>{links}</td></tr>'
        )
    return (f'<h3>実行履歴（{len(items)}件）</h3><p>参考検証の成功は保存時点の成果物確認です。採用や現在の版の優位性を意味しません。</p>'
            '<div class="table-scroll"><table><thead><tr><th>種類</th><th>実行条件</th><th>記録上の結果</th><th>モデル / 実行環境</th><th>所要時間</th><th>成果物・記録</th></tr></thead><tbody>'
            + "".join(rows) + '</tbody></table></div>')


def render_evaluations(days: int, results: list[dict[str, object]], *, evidence=None) -> str:
    generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    evidence = evidence or EvidenceSnapshot(ROOT, load_eval_cases(), results, load_catalog(), load_skill_locations())
    locations, cases, catalog = evidence.locations, evidence.cases, evidence.catalog
    references, recorded_cases, case_ids = evidence.references, evidence.recorded_cases, evidence.case_ids
    cards = {source: {} for source in SOURCE_LABELS}
    statuses: dict[str, int] = {"継続候補": 0, "要レビュー": 0, "結果未記録": 0, "判断保留": 0}

    for case_id in case_ids:
        case = cases.get(case_id)
        items = evidence.comparisons.get(case_id, [])
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
        skill = evidence.case_skills[case_id]
        reference_rows = references.get(case_id, [])
        reference_html = ""
        if reference_rows:
            reference_counts = result_counts(reference_rows)
            passed, unknown = reference_counts["passed"], reference_counts["pending"]
            outcome = f"参考検証 {passed}/{len(reference_rows)}成功" + (f"・確認不明 {unknown}" if unknown else "")
            links = " · ".join('<a href="' + html.escape(path.resolve().as_uri(), quote=True) + '">元レポート</a>' for path in sorted({r["report"] for r in reference_rows}))
            models = " / ".join(sorted({str(r["model"]) for r in reference_rows}))
            reference_html = f'<p><b>{html.escape(outcome)}</b> · {html.escape(models)} · {links}</p><p>保存時点の成果物確認の記録です。各条件1回などの参考検証を含み、現在の版の比較成立・優位性・採用を保証しません。</p>'
        if items:
            counts = result_counts(items)
            passed, pending = counts["passed"], counts["pending"]
            outcome = (outcome + " · " if reference_rows else "") + f"比較記録 {passed}/{len(items)}成功" + (f"・未採点 {pending}" if pending else "")
        elif not reference_rows:
            outcome = "成功・失敗は未確認"
        evidence_state = "recorded" if case_id in recorded_cases else "missing"
        execution = f"実行記録あり · {len(evidence.history[case_id])}件" if case_id in recorded_cases else "実行記録なし"
        comparison = status if items else "比較判定なし"
        latest = max((str(item.get("ts", "")) for item in latest_items), default="—")[
            :10
        ]
        if reference_rows and not items:
            latest = "全期間の参考記録"
        experiment_rows = render_eval_rows(
            items, locations, cases, include_contract=False
        )
        history = render_execution_history(case_id, evidence)
        comparison_html = ""
        if items:
            comparison_html = (
                '<details><summary>比較評価の集計</summary>' + render_artifacts(items)
                + '<div class="table-scroll"><table><thead><tr><th>スキル / ケース</th><th>エージェント</th><th>モデル / 実験</th><th>スキルなし・成功</th><th>スキルあり・成功</th><th>成功率差</th><th>判定</th><th>変更行</th><th>追加クラス数</th><th>失敗詳細</th></tr></thead>'
                + '<tbody>' + experiment_rows + '</tbody></table></div></details>'
            )
        contract = render_eval_contract(case)
        cards[source_group(catalog, skill)].setdefault(skill, []).append(
            f'<details class="case search-row" data-evidence="{evidence_state}" id="{html.escape(case_id, quote=True)}"><summary>'
            f"<span><strong>{html.escape(case_id)}</strong><small>{skill_link(skill, locations)}</small></span>"
            f'<span class="status-badge">{execution}</span><span>{html.escape(outcome)}</span><span>{html.escape(comparison)}</span><span>{html.escape(latest)}</span></summary>'
            f"<div class=case-body>{reference_html}{history}<p><b>ケース比較の判定理由</b> {html.escape(reason)}</p><p>{html.escape(str((case or {}).get('evaluation', {}).get('reason', '目的別評価')))}</p>{contract}{comparison_html}</div></details>"
        )

    skill_groups = {source: [] for source in SOURCE_LABELS}
    for source, skills in cards.items():
        for skill, case_cards in sorted(skills.items(), key=lambda pair: (-evidence.coverage(pair[0])[0], pair[0])):
            skill_groups[source].append(
                f'<details class="skill-case-group" data-skill="{html.escape(skill, quote=True)}" data-has-records="{str(evidence.coverage(skill)[0] > 0).lower()}">'
                f'<summary><strong>{html.escape(skill)}</strong><span class="note">{evidence.coverage_label(skill)} · 記録なし {len(case_cards) - evidence.coverage(skill)[0]}</span></summary>'
                f'<div class="skill-case-body">{"".join(case_cards)}</div></details>'
            )

    body = f"""
<p class=note>ここでは「どんな条件で試し、何が成功・失敗したか」を確認します。実験の結果と成果物を示すページで、採用の決定はスキル一覧で確認できます。</p><details><summary>評価を実行するには</summary><p>計画・入力・隔離環境を確認し、許可された範囲で明示的に実行してください。</p></details>
<p>スキルごとの採否・配置状況は<a href="report.html#skill-status">スキル一覧</a>で確認できます。</p>
<h2>スキル別のケースと履歴</h2><p>自作／外部導入の中でスキル別にまとめています。スキル名を開くと、そのスキルのケースを確認できます。</p>
<div class=toolbar><label for=search>検索</label><input id=search type=search placeholder="ケース名・スキル名・モデル名を検索…"><select id="evidence-filter" aria-label="実行記録で絞り込み"><option value="all">すべてのケース</option><option value="recorded">実行記録あり</option><option value="missing">実行記録なし</option></select><span id=result-count class=note></span></div>
<div class=cards><div class=card><span>全区分の評価ケース数</span><strong data-metric="total-cases">{len(case_ids)}</strong></div>
<div class=card><span>実行記録あり</span><strong data-metric="recorded-cases">{len(recorded_cases)}</strong></div>
<div class=card><span>実行記録なし</span><strong data-metric="missing-cases">{len(case_ids) - len(recorded_cases)}</strong></div>
<div class=card><span>比較結果の要レビュー</span><strong>{statuses["要レビュー"]}</strong></div></div>
<p class=note>実行記録は、直近{days}日のケース比較と全期間の参考検証を合わせて表示します。「成功」は保存された確認結果で、スキルの優位性や採用決定とは別です。「実行記録なし」はこの表示範囲に記録がない状態で、未実行とは限りません。参考検証は比較判定へ混ぜません。</p>

<div class=case-list>{render_source_sections(skill_groups, "cases", "スキル")}</div>
{render_saved_reports(evidence.root, evidence=evidence)}"""
    return render_page("検証結果", days, generated, "evaluations", body)


def render_operations(days: int, root: pathlib.Path, *, evidence=None) -> str:
    """Read existing rounds without running models or changing evaluation state."""
    evidence = evidence or EvidenceSnapshot(root, load_eval_cases(), load_eval_results(days, root), load_catalog(), load_skill_locations())
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
    rows = {source: [] for source in SOURCE_LABELS}
    counts = {"attention": 0, "ready": 0, "decided": 0}
    unidentified = 0
    catalog = evidence.catalog
    source_root = pathlib.Path(__file__).resolve().parents[1] / ".agents"
    current_names = {name for name, profile in catalog.items() if (source_root / profile['path']).is_file()}
    for directory in sorted((root / "eval-loops").glob("*")):
        if not directory.is_dir() or directory in evidence.reference_directories:
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
        rows[source_group(catalog, state.get("skill"))].append('<tr class="search-row" data-group="' + group + '"><td data-label="スキル"><strong>' + escape(state.get("skill") or directory.name) + '</strong><details><summary>ラウンド・記録</summary><small>' + escape(directory.name) + '</small><small>' + links + '</small></details></td><td data-label="次の作業"><span class="status-badge">' + labels.get(key, escape(key)) + '</span><small>' + escape(actions.get(state.get("next_action"), "記録形式を確認")) + '</small>' + detail + '</td><td data-label="判断"><details><summary>' + ('判断の根拠を見る' if key == 'decided' else '未確定の記録を見る' if decision else '判断の記録なし') + '</summary><p>' + reason + '</p></details></td></tr>')
    body = '<p>ここでは「どのスキルを使うか、今の配置はどうか、判断に何が残っているか」を確認します。実験条件や成果物は<a href="evals.html">検証結果</a>にまとめています。</p><p>自作スキルは自分で保守するスキル、外部導入スキル（installed）は外部から取り込んだスキルです。区分は管理台帳に基づき、配置済みかどうかとは別に表示します。</p>'
    body += render_skill_dashboard(evidence.cases, evidence.results, evidence.locations, root=root, days=days, evidence=evidence)
    body += '<h2 id="remaining-work">判断までの進捗と残作業</h2>'
    body += '<div class="cards">' + ''.join('<button type="button" class="card" data-filter="' + key + '" aria-pressed="false"><span>' + label + '</span><strong>' + str(counts[key]) + '</strong></button>' for key, label in [("attention", "確認・修正待ち"), ("ready", "実行待ち"), ("decided", "判断済み")]) + '</div>'
    body += '<p class="note">上の件数は全区分のラウンド（1つの計画に基づく比較評価）数です。同じスキルの複数ラウンドも別に表示します。状態は生成時点の検査結果で、実行中かどうかは推測しません。</p>'
    body += '<div class="toolbar"><label for="search">絞り込み</label><input id="search" type="search" placeholder="スキル・状態・判断を検索"><select id="state-filter" aria-label="状態で絞り込み"><option value="all">すべての状態</option><option value="attention">確認・修正待ち</option><option value="ready">実行待ち</option><option value="decided">判断済み</option></select><button id="reset-filters" type="button">条件をクリア</button><span id="result-count" role="status" aria-live="polite"></span></div>'
    body += render_source_sections(rows, "rounds", "ラウンド", '<div class="table-scroll"><table class="operations-table"><thead><tr><th>スキル / 評価計画</th><th>状態と次の作業</th><th>判断と根拠</th></tr></thead><tbody>', "</tbody></table></div>")
    if not any(rows.values()):
        body += "<p>評価ラウンドはありません。実作業で再現できる課題が見つかったら、既存ケースを確認して計画を作成します。</p>"
    body += '<p id="empty-results" class="empty-results" hidden>条件に一致するラウンドはありません。検索語か状態を変更するか、条件をクリアしてください。</p><details><summary>運用の流れと表示範囲</summary><p>実作業で課題を発見し、再現可能で重複しないケースを追加。許可された比較評価、成果物の採点、判断の記録を経て、必要な変更をPRへ反映します。</p><p>外部から導入したスキルは利用判断、自作スキルは利用判断と改善が対象です。状態表示からモデル実行や配置は始まりません。古い条件・欠落した証拠は不足として表示されます。判断済みでも配置済みを意味しません。</p></details>'
    body += '<p>版照合は探索対象の共有配置先について行います。全エージェントの読み込み・選択を保証しません。最新順が保証できない判断は勝手に優先せず、複数の有効な判断が競合したら要確認とします。</p>'
    if unidentified:
        body += '<p class=note>通常の評価ラウンドとして扱えない記録が' + str(unidentified) + '件あります。対象不明・破損・別形式の検証を含みます。<a href="evals.html#saved-reports">保存済みレポート</a>も確認してください。未確定の記録は現在の採否に使いません。</p>'
    return render_page("スキル一覧", days, datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"), "operations", body)


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
    parser.add_argument("--preview-dir", type=pathlib.Path, help="同じ検証済み3ページを保存する追加ディレクトリ")
    parser.add_argument("--open", action="store_true", dest="open_report")
    args = parser.parse_args()
    days = max(1, args.days)
    output = ROOT / "report.html"
    eval_output = ROOT / "evals.html"
    turns = build_turns(load_events(days))
    eval_results = load_eval_results(days)
    evidence = EvidenceSnapshot(ROOT, load_eval_cases(), eval_results, load_catalog(), load_skill_locations())
    usage_stats = aggregate(turns)
    pages = {
        "report.html": render_operations(days, ROOT, evidence=evidence),
        "usage.html": render_overview(days, turns, usage_stats),
        "evals.html": render_evaluations(days, eval_results, evidence=evidence),
    }
    validate_pages(pages, evidence, usage_stats=usage_stats)
    destinations = [ROOT] + ([args.preview_dir.expanduser()] if args.preview_dir else [])
    for destination in destinations:
        for name, content in pages.items():
            write_report(content, destination / name)
    if args.open_report:
        subprocess.run(["open", str(output)], check=False)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
