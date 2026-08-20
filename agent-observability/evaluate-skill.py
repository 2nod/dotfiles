#!/usr/bin/env python3
"""Run isolated skill-on/skill-off evaluations and persist objective results."""

from __future__ import annotations

import argparse
import difflib
import fcntl
import hashlib
import json
import os
import pathlib
import random
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from typing import cast

ROOT = pathlib.Path(
    os.environ.get(
        "AGENT_OBSERVABILITY_DIR",
        pathlib.Path.home() / ".local/share/agent-observability",
    )
)


def load_case(path: pathlib.Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid case {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("case must be a JSON object")
    case = cast(dict[str, object], raw)
    for key in ("id", "skill", "skill_path", "fixture", "prompt", "verifiers"):
        if not case.get(key):
            raise ValueError(f"missing case field: {key}")
    if not isinstance(case["verifiers"], list):
        raise ValueError("verifiers must be an array")
    return case


def resolve_case_path(case_path: pathlib.Path, value: object) -> pathlib.Path:
    path = pathlib.Path(str(value)).expanduser()
    return path if path.is_absolute() else (case_path.parent / path).resolve()


def snapshot(root: pathlib.Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
        and not {
            ".agent-observability",
            ".ruff_cache",
            "__pycache__",
            ".git",
        }.intersection(path.parts)
        and path.suffix != ".pyc"
    }


def diff_metrics(
    before: dict[str, bytes], after: dict[str, bytes]
) -> dict[str, object]:
    changed = sorted(set(before) | set(after))
    changed = [path for path in changed if before.get(path) != after.get(path)]
    lines = 0
    for path in changed:
        old = before.get(path, b"").decode("utf-8", errors="replace").splitlines()
        new = after.get(path, b"").decode("utf-8", errors="replace").splitlines()
        for tag, old_start, old_end, new_start, new_end in difflib.SequenceMatcher(
            None, old, new
        ).get_opcodes():
            if tag != "equal":
                lines += old_end - old_start + new_end - new_start
    class_pattern = re.compile(r"^\s*class\s+\w+", re.MULTILINE)
    classes_before = sum(
        len(class_pattern.findall(data.decode("utf-8", errors="ignore")))
        for data in before.values()
    )
    classes_after = sum(
        len(class_pattern.findall(data.decode("utf-8", errors="ignore")))
        for data in after.values()
    )
    return {
        "changed_files": len(changed),
        "changed_lines": lines,
        "new_files": sum(path not in before for path in changed),
        "classes_added": max(0, classes_after - classes_before),
        "changed_paths": changed,
    }


def pi_command(
    prompt: str, skill_path: pathlib.Path | None, model: str | None
) -> list[str]:
    command = [
        "pi",
        "--no-session",
        "-p",
        "--no-skills",
        "--tools",
        "read,write,edit,bash",
    ]
    append_prompt = pathlib.Path.home() / ".pi/agent/system-append.md"
    if append_prompt.is_file():
        command += ["--append-system-prompt", str(append_prompt)]
    command += [
        "--append-system-prompt",
        "This is an automated skill evaluation run. Do not create or modify eval cases.",
    ]
    if model:
        command += ["--model", model]
    if skill_path:
        command += ["--skill", str(skill_path)]
    return [*command, prompt]


def verifier_commands(
    case: dict[str, object], case_path: pathlib.Path, workspace: pathlib.Path
) -> list[list[str]]:
    commands: list[list[str]] = []
    for raw in cast(list[object], case["verifiers"]):
        if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
            raise ValueError("each verifier must be an array of strings")
        commands.append(
            [
                cast(str, item)
                .replace("{workspace}", str(workspace))
                .replace("{case_dir}", str(case_path.parent))
                for item in raw
            ]
        )
    return commands


def safe_detail(text: str) -> str:
    text = " ".join(text.split())
    text = re.sub(r"(?:/private|/var|/tmp|/Users|/home)/[^ ]+", "<path>", text)
    return text[:240]


def append_result(result: dict[str, object]) -> None:
    directory = ROOT / "eval-results"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{datetime.now(timezone.utc).date().isoformat()}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.write(
            json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        handle.flush()
        os.fsync(handle.fileno())


def run_once(
    case: dict[str, object],
    case_path: pathlib.Path,
    variant: str,
    run_number: int,
    model: str | None,
    timeout: int,
    experiment_id: str,
) -> dict[str, object]:
    fixture = resolve_case_path(case_path, case["fixture"])
    skill_path = resolve_case_path(case_path, case["skill_path"])
    if not fixture.is_dir() or not skill_path.is_file():
        raise ValueError("fixture directory or skill file does not exist")

    with tempfile.TemporaryDirectory(prefix="skill-eval-") as temp:
        workspace = pathlib.Path(temp) / "workspace"
        shutil.copytree(fixture, workspace)
        before = snapshot(workspace)
        command = pi_command(
            str(case["prompt"]),
            skill_path if variant == "treatment" else None,
            model,
        )
        env = {
            **os.environ,
            "AGENT_OBSERVABILITY_DIR": str(pathlib.Path(temp) / ".agent-observability"),
        }
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                cwd=workspace,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            agent_exit = completed.returncode
            agent_stderr = safe_detail(completed.stderr)
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            agent_exit = -1
            agent_stderr = safe_detail(str(exc))
            timed_out = True

        verifier_results = []
        for verifier in verifier_commands(case, case_path, workspace):
            checked = subprocess.run(
                verifier,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            verifier_results.append(
                {
                    "name": pathlib.Path(verifier[0]).name,
                    "exit": checked.returncode,
                    **(
                        {"detail": safe_detail(checked.stderr or checked.stdout)}
                        if checked.returncode
                        else {}
                    ),
                }
            )
        metrics = diff_metrics(before, snapshot(workspace))
        verifiers_passed = bool(verifier_results) and all(
            item["exit"] == 0 for item in verifier_results
        )
        if timed_out:
            failure_kind = "timeout"
            failure_detail = agent_stderr
        elif agent_exit != 0:
            failure_kind = "agent_failed"
            failure_detail = agent_stderr or f"agent exit {agent_exit}"
        elif not verifiers_passed:
            failure_kind = "verifier_failed"
            failure_detail = next(
                (
                    str(item["detail"])
                    for item in verifier_results
                    if item["exit"] != 0 and item.get("detail")
                ),
                "verifier returned non-zero",
            )
        elif not metrics["changed_files"]:
            failure_kind = "no_changes"
            failure_detail = "verifier passed but workspace did not change"
        else:
            failure_kind = "passed"
            failure_detail = ""
        success = failure_kind == "passed"
        failure_phase = {
            "timeout": "agent",
            "agent_failed": "agent",
            "verifier_failed": "verifier",
            "no_changes": "snapshot",
            "passed": "completed",
        }[failure_kind]
        observed_model = model or "default"
        for path in (pathlib.Path(temp) / ".agent-observability/events").glob(
            "*.jsonl"
        ):
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    observed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(observed, dict) and isinstance(
                    observed.get("model"), str
                ):
                    observed_model = str(observed["model"])

        return {
            "ts": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "case": str(case["id"]),
            "skill": str(case["skill"]),
            "agent": "pi",
            "variant": variant,
            "run": run_number,
            "experiment_id": experiment_id,
            "model": observed_model,
            "skill_version": "sha256:"
            + hashlib.sha256(skill_path.read_bytes()).hexdigest(),
            "success": success,
            "agent_exit": agent_exit,
            "timed_out": timed_out,
            "failure_kind": failure_kind,
            "failure_phase": failure_phase,
            **({"failure_detail": failure_detail} if failure_detail else {}),
            **{
                key: case[key]
                for key in ("failure_conditions", "expected_behavior")
                if case.get(key)
            },
            **metrics,
            "duration_seconds": round(time.monotonic() - started, 3),
            "verifiers": verifier_results,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=pathlib.Path)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    case_path = args.case.expanduser().resolve()
    case = load_case(case_path)
    fixture = resolve_case_path(case_path, case["fixture"])
    skill_path = resolve_case_path(case_path, case["skill_path"])
    if not fixture.is_dir() or not skill_path.is_file():
        raise ValueError("fixture directory or skill file does not exist")

    plan = [
        (run, variant)
        for run in range(1, max(1, args.runs) + 1)
        for variant in ("control", "treatment")
    ]
    random.Random(args.seed).shuffle(plan)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "case": case["id"],
                    "skill": case["skill"],
                    "fixture": str(fixture),
                    "runs": plan,
                    "treatment_command": pi_command(
                        str(case["prompt"]), skill_path, args.model
                    ),
                    "control_command": pi_command(
                        str(case["prompt"]), None, args.model
                    ),
                    "verifiers": verifier_commands(
                        case, case_path, pathlib.Path("<workspace>")
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    experiment_id = uuid.uuid4().hex
    for run_number, variant in plan:
        result = run_once(
            case,
            case_path,
            variant,
            run_number,
            args.model,
            max(1, args.timeout),
            experiment_id,
        )
        append_result(result)
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
