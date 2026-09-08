"""Purpose-aware evaluation contracts shared by the runner, audit and HTML report."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
LABELS = {
    "unassessed": "未評価",
    "keep": "継続候補",
    "revise": "修正候補",
    "disable": "無効化候補",
    "hold": "保留",
    "neutral": "同等",
}


def digest_files(paths):
    digest = hashlib.sha256()
    for name, data in sorted(paths):
        digest.update(name.encode() + b"\0" + data + b"\0")
    return "sha256:" + digest.hexdigest()


def tree_version(path):
    return digest_files(
        (str(p.relative_to(path)), p.read_bytes())
        for p in path.rglob("*")
        if p.is_file()
        and not p.is_symlink()
        and not {".git", "__pycache__"}.intersection(p.parts)
    )


def resolve(case_path, value):
    return (case_path.parent / value).resolve()


def contract_version(case, case_path, skill_path=None):
    """Include fixture, local verifier files, full skill bundle and runner implementation."""
    skill_path = skill_path or resolve(case_path, case["skill_path"])
    if not skill_path.is_file() or not resolve(case_path, case["fixture"]).is_dir():
        raise OSError("skill or fixture is missing")
    files = [
        ("case", json.dumps(case, sort_keys=True, ensure_ascii=False).encode()),
        ("fixture", tree_version(resolve(case_path, case["fixture"])).encode()),
        ("skill", tree_version(skill_path.parent).encode()),
    ]
    for cmd in case["verifiers"]:
        for token in cmd:
            if "{case_dir}" in token:
                p = pathlib.Path(token.replace("{case_dir}", str(case_path.parent)))
                if p.is_file():
                    files.append((token, p.read_bytes()))
    catalog_path = case_path.parent.parent / "eval-catalog.json"
    if catalog_path.is_file():
        profile = json.loads(catalog_path.read_text())["skills"].get(
            case.get("skill"), {}
        )
        files.append(
            (
                "purpose",
                json.dumps(
                    {key: profile.get(key) for key in ("purpose", "evidence")},
                    sort_keys=True,
                    ensure_ascii=False,
                ).encode(),
            )
        )
    for name in ("evaluate-skill.py", "eval_contracts.py", "isolated_tools.py", "isolated-pi-tools.mjs"):
        files.append((name, (pathlib.Path(__file__).parent / name).read_bytes()))
    return digest_files(files)


def load_catalog(path=None):
    path = path or REPO / ".agents/eval-catalog.json"
    catalog = json.loads(path.read_text())["skills"]
    for directory in (path.parent / "skills", path.parent / "installed-skills"):
        for skill in directory.glob("**/SKILL.md"):
            name = skill.parent.name
            if name not in catalog:
                catalog[name] = {
                    "purpose": "目的を台帳へ追加してください",
                    "evidence": "未定義",
                    "script_candidate": "未検討",
                    "decision": "unassessed",
                    "decision_reason": "新規skill",
                    "required_scenarios": ["typical", "boundary", "negative"],
                    "path": str(skill.relative_to(path.parent)),
                    "source": "installed" if directory.name == "installed-skills" else "authored",
                }
    return catalog


def case_verdict(case, items, min_pairs=3, current_version=None):
    """A case signal is never a skill retirement decision. Missing evidence stays unknown."""
    if case.get("evaluation", {}).get("status") != "ready":
        return "hold", "旧ケース・目的との整合を再設計", 0
    if current_version == "invalid":
        return "hold", "skillまたはfixtureの参照が壊れている", 0
    if not items:
        return "unassessed", "実測なし", 0
    # Never pool legacy records, revisions, models, or partial experiments.
    latest = max(items, key=lambda x: x.get("ts", ""))
    key = tuple(
        latest.get(k)
        for k in (
            "experiment_id",
            "contract_version",
            "model",
            "agent",
            "agent_version",
        )
    )
    group = [
        x
        for x in items
        if tuple(
            x.get(k)
            for k in (
                "experiment_id",
                "contract_version",
                "model",
                "agent",
                "agent_version",
            )
        )
        == key
    ]
    if not all(key) or (
        current_version and latest.get("contract_version") != current_version
    ):
        return "hold", "条件不明または評価対象が更新済み", 0
    if any(
        x.get("experiment_id") == key[0]
        and tuple(
            x.get(k)
            for k in (
                "experiment_id",
                "contract_version",
                "model",
                "agent",
                "agent_version",
            )
        )
        != key
        for x in items
    ):
        return "hold", "同じ実験内で実行条件が混在", 0
    pairs = {}
    for item in group:
        variant = item.get("variant")
        if variant not in ("control", "treatment"):
            continue
        pair = pairs.setdefault(item.get("run"), {})
        if variant in pair:
            return "hold", "runの重複", 0
        pair[variant] = item
    complete = [p for p in pairs.values() if set(p) == {"control", "treatment"}]
    if len(complete) != len(pairs) or len(complete) < min_pairs:
        return (
            "hold",
            f"完全な比較ペアが不足 ({len(complete)}/{min_pairs})",
            len(complete),
        )
    measured = [x for p in complete for x in p.values()]
    if any(
        x.get("failure_kind") in ("timeout", "agent_failed", "verifier_error")
        for x in measured
    ):
        return "hold", "環境・実行エラーを品質の悪化と区別して再実行", len(complete)
    if any(
        x.get("success") not in (True, False) or x.get("success") is None
        for x in measured
    ):
        return "hold", "目的の採点が未完了", len(complete)
    wins = sum(
        p["treatment"]["success"] and not p["control"]["success"] for p in complete
    )
    losses = sum(
        p["control"]["success"] and not p["treatment"]["success"] for p in complete
    )
    if losses:
        return "revise", f"{wins}勝/{losses}敗。失敗の根拠を確認", len(complete)
    if wins:
        return "keep", f"{wins}勝/0敗。このケースでの改善信号", len(complete)
    if all(x["success"] for x in measured):
        return "neutral", "両条件で目的を達成。不要とは判定しない", len(complete)
    return "hold", "品質差を確認できない。不要とは判定しない", len(complete)


def skill_summary(catalog, cases, results, cases_dir):
    rows = []
    for name, profile in sorted(catalog.items()):
        related = [c for c in cases.values() if c.get("skill") == name]
        signals = []
        for case in related:
            p = cases_dir / (case["id"] + ".json")
            try:
                version = contract_version(case, p)
            except (OSError, KeyError, TypeError):
                version = "invalid"
            signal, reason, count = case_verdict(
                case,
                [r for r in results if r.get("case") == case["id"]],
                current_version=version,
            )
            signals.append(
                {
                    "case": case["id"],
                    "scenario": case.get("scenario"),
                    "status": signal,
                    "reason": reason,
                    "pairs": count,
                    "contract_version": version,
                }
            )
        ready = [
            s
            for s in signals
            if cases[s["case"]].get("evaluation", {}).get("status") == "ready"
        ]
        tested = {
            s["scenario"]
            for s in ready
            if s["pairs"] >= 3 and s["status"] in ("keep", "neutral")
        }
        if any(s["status"] == "revise" for s in ready):
            status, reason = "revise", "目的に沿う評価で悪化。成果物を確認"
        elif (
            set(profile["required_scenarios"]) <= tested
            and all(s["status"] in ("keep", "neutral") for s in ready)
            and any(s["status"] == "keep" for s in ready)
        ):
            status, reason = (
                "keep",
                "代表・境界・負例で改善信号あり。採用判断は人が記録する",
            )
        elif not ready or all(s["status"] == "unassessed" for s in ready):
            status, reason = "unassessed", "目的に沿うケースまたは実測が不足"
        else:
            status, reason = "hold", "評価範囲または証拠が不足"
        rows.append(
            {
                "skill": name,
                **profile,
                "recommendation": status,
                "reason": reason,
                "cases": signals,
            }
        )
    return rows


def reviewed_result(item, review=None):
    """Apply local evidence-backed rubric scores; never let a review override failed execution."""
    item = dict(item)
    if not item.get("rubric") or item.get("failure_kind") != "passed":
        return item
    item["success"] = None
    try:
        directory = pathlib.Path(item["artifacts"])
        if review is None:
            review = json.loads((directory / "review.json").read_text())
        version = digest_files(
            (str(p.relative_to(directory)), p.read_bytes())
            for p in directory.rglob("*")
            if p.is_file()
            and p.name != "review.json"
            and not p.is_symlink()
            and not {".git", "__pycache__"}.intersection(p.parts)
        )
        criteria = review["criteria"]
        expected = {r["id"] for r in item["rubric"]}
        if (
            version != item["artifact_version"]
            or review["artifact_version"] != version
            or not review.get("reviewer", "").strip()
            or len(criteria) != len(expected)
            or {c["id"] for c in criteria} != expected
            or any(
                type(c["pass"]) is not bool or not c["evidence"].strip()
                for c in criteria
            )
        ):
            return item
        item["success"] = all(c["pass"] for c in criteria)
        item["reviewer"] = review["reviewer"]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return item


EVALUATION_PAUSE_REASON = (
    "実評価は停止中: 隔離検証と入力確認後の明示指定が必要。"
    "承認済みの新規計画ではSKILL_EVAL_ISOLATED_RUN=1を指定する。"
    "dry-runと保存済み成果物の確認は利用可能。"
)


def execution_preflight():
    """Explicit opt-in after offline isolation checks; the runner enforces isolation."""
    if os.environ.get("SKILL_EVAL_ISOLATED_RUN") != "1":
        raise ValueError(EVALUATION_PAUSE_REASON)
