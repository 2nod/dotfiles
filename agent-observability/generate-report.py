#!/usr/bin/env python3
"""Generate a local HTML report from agent observability JSONL events."""

from __future__ import annotations

import argparse
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
    tools: int = 0
    tool_counts: dict[str, int] = field(default_factory=dict)
    durations: list[float] = field(default_factory=list)
    versions: set[str] = field(default_factory=set)
    last_used: datetime | None = None


def turn_outcome(turn: Turn) -> str:
    if not turn.ended:
        return "進行中"
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
                results.append(result)
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
        return "<span class=note>case定義なし</span>"
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
        f"<dt>Control</dt><dd>同じfixture・課題・verifierでskillを読み込まない</dd>"
        f"<dt>Treatment</dt><dd>同じ条件で{html.escape(str(case.get('skill', '?')))}だけを追加読込</dd>"
        f"<dt>課題</dt><dd>{html.escape(str(case.get('prompt', '—')))}</dd>"
        f"<dt>Fixture</dt><dd>{html.escape(pathlib.Path(str(case.get('fixture', '—'))).name)}</dd>"
        f"<dt>成功条件</dt><dd>{html.escape(str(case.get('expected_behavior', '—')))}</dd>"
        f"<dt>失敗条件</dt><dd><ul>{condition_items}</ul></dd>"
        f"<dt>Verifier</dt><dd>{verifier_text}</dd>"
        "<dt>成功判定</dt><dd>agent exit 0・変更あり・全verifier exit 0</dd>"
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
        has_advantage = treatment_rate > control_rate or (
            treatment_rate == control_rate
            and (treatment_lines < control_lines or treatment_classes < control_classes)
        )
        paired_runs = min(len(control), len(treatment))
        if not paired_runs:
            verdict = "要実験"
        elif paired_runs < 3:
            verdict = "暫定"
        elif has_advantage:
            verdict = "効果あり"
        elif treatment_rate < control_rate:
            verdict = "逆効果"
        else:
            verdict = "整理候補"
        contract_cell = (
            f'<td data-label="実験条件" class=detail>{render_eval_contract(cases.get(case))}</td>'
            if include_contract
            else ""
        )
        rows.append(
            f'<tr class=data-row data-eval-skill="{html.escape(skill)}">'
            f'<td data-label="Skill / Case"><strong>{skill_link(skill, locations)}</strong><small>{html.escape(case)} · {skill_status(skill, locations)}</small></td>'
            f'<td data-label="Agent">{html.escape(agent)}</td><td data-label="Model">{html.escape(model)}<small>{html.escape(experiment_id[:8])} · {html.escape(skill_version[:19])}</small></td>'
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
        or f'<tr><td colspan="{11 if include_contract else 10}" class=empty>比較評価はまだ実行されていません。</td></tr>'
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
                    details.append(f"{diagnostics:g}件")
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
            if not turn.ended:
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
:root { color-scheme: light dark; font-family: ui-sans-serif, system-ui, sans-serif; --line: #8884; --panel: #8881; --muted: #777; }
* { box-sizing: border-box; }
body { max-width: 1280px; margin: 0 auto; padding: 40px 24px 64px; line-height: 1.5; }
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
"""

PAGE_SCRIPT = """
(() => {
  const rows = [...document.querySelectorAll('.search-row')];
  const search = document.querySelector('#search');
  const count = document.querySelector('#result-count');
  const update = () => {
    const query = search ? search.value.trim().toLocaleLowerCase() : '';
    let visible = 0;
    rows.forEach(row => {
      const matches = !query || row.textContent.toLocaleLowerCase().includes(query);
      row.hidden = !matches || (!query && row.classList.contains('recent-extra'));
      if (!row.hidden) visible++;
    });
    if (count) count.textContent = query ? `${visible}件` : '';
  };
  search?.addEventListener('input', update);
  document.querySelectorAll('table').forEach(table => {
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
        f'<nav><a href="report.html" class="{"active" if active == "overview" else ""}">Overview</a>'
        f'<a href="evals.html" class="{"active" if active == "evaluations" else ""}">Evaluations</a></nav>'
    )
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html.escape(title)}</title><style>{PAGE_STYLE}</style></head><body>
<h1>{html.escape(title)}</h1><div class=meta>直近{days}日 · 生成 {html.escape(generated)}</div>
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
            f"<small>平均tool {item.tools / item.uses:.1f} · 時間中央値 {median_seconds:.0f}s</small>"
            f"<small>{format_tool_counts(item.tool_counts)}</small></details>"
        )
        skill_rows.append(
            f'<tr class="data-row search-row"><td data-label="Skill"><strong>{skill_link(skill, locations)}</strong>{detail}</td>'
            f'<td data-label="利用turn">{item.uses}</td><td data-label="検証済" class=good>{item.verified}</td>'
            f'<td data-label="失敗" class=bad>{item.failed}</td><td data-label="未検証">{item.unverified}</td>'
            f'<td data-label="検証率">{rate}</td><td data-label="最終利用">{last_used}</td></tr>'
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
        else "<p class=note>要確認のturnはありません。</p>"
    )

    recent_rows = []
    for index, turn in enumerate(relevant[:50]):
        extra = " recent-extra" if index >= 10 else ""
        hidden = " hidden" if index >= 10 else ""
        recent_rows.append(
            f'<tr class="data-row search-row{extra}"{hidden}>'
            f'<td data-label="時刻">{turn.started.astimezone().strftime("%m-%d %H:%M")}</td>'
            f'<td data-label="Agent">{html.escape(turn.agent)}</td><td data-label="Project">{html.escape(turn.project)}</td>'
            f'<td data-label="Skills">{html.escape(", ".join(sorted(turn.skills)))}</td>'
            f'<td data-label="結果">{html.escape(turn_outcome(turn))}<small>{format_verifications(turn)}</small><details><summary>tool {turn.tools}</summary><small>{format_tool_counts(turn.tool_counts)}</small></details></td></tr>'
        )
    if not recent_rows:
        recent_rows.append(
            '<tr><td colspan="5" class=empty>該当するturnはありません。</td></tr>'
        )
    toggle = (
        f"<button id=show-all class=toggle>{min(len(relevant), 50)}件すべて表示</button>"
        if len(relevant) > 10
        else ""
    )

    body = f"""
<div class=cards><div class=card><span>利用turn</span><strong>{total_uses}</strong></div>
<div class=card><span>検証済</span><strong>{total_verified}</strong></div>
<div class=card><span>検証失敗</span><strong class=bad>{total_failed}</strong></div>
<div class=card><span>未検証</span><strong>{total_unverified}</strong></div></div>
<section class=attention><strong>要確認</strong>{attention_html}</section>
<div class=toolbar><label for=search>検索</label><input id=search type=search placeholder="skill、project、agentを検索…"><span id=result-count class=note></span></div>
<h2>Skillを含むturn</h2><div class=table-scroll><table class=skill-table><thead><tr><th>Skill</th><th>利用turn</th><th>検証済</th><th>失敗</th><th>未検証</th><th>検証率</th><th>最終利用</th></tr></thead>
<tbody>{"".join(skill_rows)}</tbody></table></div>
<h2>最近の利用</h2><div class=table-scroll><table class=recent-table><thead><tr><th>時刻</th><th>Agent</th><th>Project</th><th>Skills</th><th>結果</th></tr></thead>
<tbody>{"".join(recent_rows)}</tbody></table></div>{toggle}
<p class=note>検証率は、skillを使った終了済みturnのうち、各検証カテゴリの最後の結果がすべて成功した割合です。</p>"""
    return render_page("Agent Skill Report", days, generated, "overview", body)


def render_evaluations(days: int, results: list[dict[str, object]]) -> str:
    generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    locations = load_skill_locations()
    cases = load_eval_cases()
    result_cases = {str(item.get("case")) for item in results if item.get("case")}
    case_ids = sorted(set(cases) | result_cases)
    cards = []
    statuses: dict[str, int] = {"効果あり": 0, "要レビュー": 0, "未実験": 0, "暫定": 0}

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
        control_rate = (
            sum(bool(item.get("success")) for item in control) / len(control)
            if control
            else 0
        )
        treatment_rate = (
            sum(bool(item.get("success")) for item in treatment) / len(treatment)
            if treatment
            else 0
        )
        paired = min(len(control), len(treatment))
        if not paired:
            status = "未実験"
        elif paired < 3:
            status = "暫定"
        elif treatment_rate > control_rate:
            status = "効果あり"
        elif treatment_rate < control_rate:
            status = "要レビュー"
        else:
            status = "暫定"
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
            f"<div class=case-body>{contract}<h3>実験履歴</h3><div class=table-scroll><table><thead><tr><th>Skill / Case</th><th>Agent</th><th>Model / Experiment</th><th>なし成功</th><th>あり成功</th><th>成功率差</th><th>判定</th><th>変更行</th><th>追加class</th><th>失敗詳細</th></tr></thead>"
            f"<tbody>{experiment_rows}</tbody></table></div></div></details>"
        )

    body = f"""
<div class=cards><div class=card><span>Cases</span><strong>{len(case_ids)}</strong></div>
<div class=card><span>効果あり</span><strong class=good>{statuses["効果あり"]}</strong></div>
<div class=card><span>要レビュー</span><strong class=bad>{statuses["要レビュー"]}</strong></div>
<div class=card><span>未実験 / 暫定</span><strong>{statuses["未実験"] + statuses["暫定"]}</strong></div></div>
<p class=note>同じfixture・課題・verifierで、Controlはskillなし、Treatmentはskillありとして比較します。</p>
<div class=toolbar><label for=search>検索</label><input id=search type=search placeholder="case、skill、modelを検索…"><span id=result-count class=note></span></div>
<div class=case-list>{"".join(cards) or "<p class=empty>caseはまだありません。</p>"}</div>"""
    return render_page("Skill Evaluations", days, generated, "evaluations", body)


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
    write_report(render_overview(days, turns, aggregate(turns)), output)
    write_report(render_evaluations(days, eval_results), eval_output)
    if args.open_report:
        subprocess.run(["open", str(output)], check=False)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
