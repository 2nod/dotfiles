#!/usr/bin/env python3
"""Run isolated skill-on/skill-off evaluations and persist objective results."""

from __future__ import annotations

import argparse
import difflib
import fcntl
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
import uuid
import html
import sys
import shlex

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from eval_contracts import contract_version, tree_version, execution_preflight, dependency_paths
from isolated_tools import ToolSandbox, fixture_files, IMAGE
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
    if case.get("evaluation", {}).get("status") == "ready":
        rubric = case.get("rubric")
        if (
            not isinstance(rubric, list)
            or not rubric
            or any(
                not isinstance(r, dict) or not r.get("id") or not r.get("criterion")
                for r in rubric
            )
            or len({r["id"] for r in rubric}) != len(rubric)
        ):
            raise ValueError("ready cases require unique purpose rubric criteria")
        if case.get("scenario") not in ("typical", "boundary", "negative"):
            raise ValueError("ready case requires a scenario category")
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
        and not path.is_symlink()
        and root.resolve() in path.resolve().parents
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
    prompt: str, skill_path: pathlib.Path | None, model: str | None, skill_root="/skills"
) -> list[str]:
    command = [
        "pi",
        "--no-session",
        "-p",
        "--no-skills",
        "--no-builtin-tools",
        "--extension",
        str(pathlib.Path(__file__).with_name("isolated-pi-tools.mjs")),
    ]
    command += [
        "--no-extensions",
        "--no-context-files",
        "--no-prompt-templates",
        "--no-themes",
        "--mode",
        "json",
    ]
    command += [
        "--append-system-prompt",
        "This is an automated skill evaluation run. Do not create or modify eval cases. "
        "Tools run inside a container: use /workspace as the working directory. "
        "Host paths in runtime context are not tool paths.",
    ]
    if model:
        command += ["--model", model]
    if skill_path:
        command += [
            "--append-system-prompt",
            "Apply this skill for this task. Supporting files are relative to "
            + skill_root + " (read-only; workspace is /workspace)"
            + ". The skill entry is " + skill_root + "/SKILL.md; for example, "
            + "references/example.md resolves to " + skill_root + "/references/example.md. "
            + "Resolve sibling references relative to this directory. "
            + "If a reference is missing, list /skills before assuming it is absent."
            + "\n"
            + skill_path.read_text(),
        ]
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


def persist_artifacts(
    case, before, after, output, stderr, experiment_id, run_number, variant
):
    directory = ROOT / "eval-artifacts" / experiment_id / f"{run_number}-{variant}"
    directory.mkdir(parents=True, exist_ok=False)
    for label, files in (("before", before), ("after", after)):
        for name, data in files.items():
            path = directory / label / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    (directory / "trace.jsonl").write_text(output)
    (directory / "stderr.txt").write_text(stderr)
    (directory / "case.json").write_text(json.dumps(case, ensure_ascii=False, indent=2))
    diff = "\n".join(
        line
        for name in sorted(before.keys() | after.keys())
        for line in difflib.unified_diff(
            before.get(name, b"").decode(errors="replace").splitlines(),
            after.get(name, b"").decode(errors="replace").splitlines(),
            fromfile="before/" + name,
            tofile="after/" + name,
        )
    )
    (directory / "changes.diff").write_text(diff)
    # Show generated text as escaped text; never execute generated HTML in this report.
    sections = "".join(
        "<details><summary>"
        + html.escape(name)
        + "</summary><pre>"
        + html.escape(data.decode(errors="replace"))
        + "</pre></details>"
        for name, data in sorted(after.items())
    )
    (directory / "index.html").write_text(
        '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        "<title>評価アウトプット</title><style>body{max-width:1000px;margin:2rem auto;padding:1rem;font-family:sans-serif}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>"
        "<h1>評価アウトプット</h1><p>合成fixtureの実行結果。採点はreview.jsonに証拠付きで記録します。</p>"
        "<h2>差分</h2><pre>"
        + html.escape(diff)
        + "</pre><h2>成果物</h2>"
        + sections
        + "<h2>実行trace</h2><pre>"
        + html.escape(output)
        + "</pre></html>"
    )
    version = tree_version(directory)
    review = {
        "artifact_version": version,
        "reviewer": "",
        "criteria": [
            {"id": r["id"], "criterion": r["criterion"], "pass": None, "evidence": ""}
            for r in case.get("rubric", [])
        ],
    }
    (directory / "review.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2)
    )
    return str(directory), version


def load_case_skills(worker, case, case_path, target, variant):
    dependencies = dependency_paths(case, case_path, target)
    if variant == "control":
        return "/skills"
    if not dependencies:
        worker.load_skill(target.parent)
        return "/skills"
    bundles = {target.parent.name: target.parent, **dependencies}
    contents, executable = {}, set()
    for name, root in bundles.items():
        for relative, data in fixture_files(root).items():
            key = name + "/" + relative
            contents[key] = data
            if (root / relative).stat().st_mode & 0o111:
                executable.add(key)
    worker.load_readonly(contents, executable)
    return "/skills/" + target.parent.name


def run_once(
    case,
    case_path,
    variant,
    run_number,
    model,
    timeout,
    experiment_id,
    candidate=None,
    agent_version="unknown",
):
    fixture = resolve_case_path(case_path, case["fixture"])
    target = (
        candidate
        if variant == "candidate"
        else resolve_case_path(case_path, case["skill_path"])
    )
    version = contract_version(case, case_path)
    fixture_files(fixture)  # Reject aliases before any model or host copy.
    for dependency in dependency_paths(case, case_path, target).values():
        fixture_files(dependency)
    with (
        tempfile.TemporaryDirectory(prefix="skill-eval-") as temp,
        ToolSandbox(shutil.which("docker") or "") as worker,
    ):
        workspace = pathlib.Path(temp) / "workspace"
        shutil.copytree(fixture, workspace)
        worker.load_fixture(fixture)
        skill_root = load_case_skills(worker, case, case_path, target, variant)
        before = worker.snapshot()
        command = pi_command(
            str(case["prompt"]), target if variant != "control" else None, model, skill_root
        )
        env = {
            **os.environ,
            "AGENT_OBSERVABILITY_DIR": str(pathlib.Path(temp) / ".agent-observability"),
            "SKILL_EVAL_CONTAINER": worker.name,
            "SKILL_EVAL_DOCKER": worker.docker,
            "SKILL_EVAL_PYTHON": sys.executable,
        }
        started = time.monotonic()
        output, stderr, timed_out = "", "", False
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
            agent_exit, output, stderr = (
                completed.returncode,
                completed.stdout,
                completed.stderr,
            )
        except subprocess.TimeoutExpired as exc:
            agent_exit, timed_out = -1, True
            output = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(output, bytes):
                output = output.decode(errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
        except OSError as exc:
            agent_exit, stderr = -1, str(exc)
        artifact_error = ""
        try:
            after = worker.snapshot()  # Export regular files only, before verification.
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            after, artifact_error = {}, safe_detail(str(exc))
            stderr += "\nArtifact export rejected: " + artifact_error
        agent_seconds = time.monotonic() - started
        directory, artifact_version = persist_artifacts(
            case, before, after, output, stderr, experiment_id, run_number, variant
        )
        verifier_results = []
        for verifier in (
            [] if artifact_error else verifier_commands(case, case_path, workspace)
        ):
            try:
                # A fresh worker prevents surviving agent processes from affecting grading.
                with ToolSandbox(shutil.which("docker") or "") as checker:
                    for name, data in after.items():
                        checker.write(name, data)
                    verification_files = {}
                    translated = []
                    for token in verifier:
                        if token.startswith(str(case_path.parent) + "/"):
                            source = pathlib.Path(token)
                            relative = source.relative_to(case_path.parent).as_posix()
                            if source.is_dir():
                                verification_files.update(
                                    {
                                        relative + "/" + n: d
                                        for n, d in fixture_files(source).items()
                                    }
                                )
                            elif source.is_file() and not source.is_symlink():
                                verification_files[relative] = source.read_bytes()
                            else:
                                raise ValueError("invalid verifier input")
                            translated.append("/skills/" + relative)
                        else:
                            translated.append(
                                token.replace(str(workspace), "/workspace")
                            )
                    checker.load_readonly(verification_files)
                    raw = checker.bash(shlex.join(translated), timeout=60)
                    checked = subprocess.CompletedProcess(
                        translated,
                        raw.returncode,
                        raw.stdout.decode(errors="replace"),
                        raw.stderr.decode(errors="replace"),
                    )
                code, detail = checked.returncode, checked.stderr or checked.stdout
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                code, detail = 2, str(exc)
            verifier_results.append(
                {
                    "name": pathlib.Path(verifier[0]).name,
                    "exit": code,
                    "detail": safe_detail(detail) if code else "",
                }
            )
        metrics = diff_metrics(before, after)
        outcome = bool(verifier_results) and all(
            v["exit"] == 0 for v in verifier_results
        )
        kind = (
            "artifact_error"
            if artifact_error
            else "timeout"
            if timed_out
            else "agent_failed"
            if agent_exit
            else "verifier_error"
            if any(v["exit"] not in (0, 1) for v in verifier_results)
            else "verifier_failed"
            if not outcome
            else "passed"
        )
        # Machine checks establish outcome only. Purpose rubrics need evidence-based review.
        success = None if kind == "passed" and case.get("rubric") else kind == "passed"
        usage = []
        for line in output.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            message = event.get("message", {}) if isinstance(event, dict) else {}
            if (
                isinstance(event, dict)
                and event.get("type") == "message_end"
                and message.get("role") == "assistant"
            ):
                if isinstance(message.get("usage"), dict):
                    usage.append(message["usage"])
        tokens = (
            sum(u["totalTokens"] for u in usage)
            if usage
            and all(isinstance(u.get("totalTokens"), (int, float)) for u in usage)
            else None
        )
        return {
            "schema_version": 2,
            "ts": datetime.now(timezone.utc).isoformat(),
            "case": case["id"],
            "skill": case["skill"],
            "agent": "pi",
            "agent_version": agent_version,
            "isolation": "docker-no-host-mounts-v1",
            "runtime_image": IMAGE,
            "model": model,
            "variant": variant,
            "run": run_number,
            "experiment_id": experiment_id,
            "contract_version": version,
            "skill_version": tree_version(target.parent),
            "dependency_versions": {name: tree_version(path) for name, path in dependency_paths(case, case_path, target).items()},
            "candidate_version": tree_version(candidate.parent) if candidate else None,
            "success": success,
            "outcome_success": outcome,
            "agent_exit": agent_exit,
            "failure_kind": kind,
            "failure_phase": "completed" if kind == "passed" else "execution",
            "failure_detail": safe_detail(stderr),
            "timed_out": timed_out,
            "duration_seconds": round(time.monotonic() - started, 3),
            "agent_seconds": round(agent_seconds, 3),
            "total_tokens": tokens,
            "artifacts": directory,
            "artifact_version": artifact_version,
            "rubric": case.get("rubric", []),
            "verifiers": verifier_results,
            **metrics,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=pathlib.Path)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--candidate",
        type=pathlib.Path,
        help="Compare a revised skill as a third variant",
    )
    parser.add_argument(
        "--allow-legacy",
        action="store_true",
        help="Exploratory only; excluded from adoption decisions",
    )
    args = parser.parse_args()

    case_path = args.case.expanduser().resolve()
    case = load_case(case_path)
    fixture = resolve_case_path(case_path, case["fixture"])
    skill_path = resolve_case_path(case_path, case["skill_path"])
    if not fixture.is_dir() or not skill_path.is_file():
        raise ValueError("fixture directory or skill file does not exist")

    variants = ["control", "treatment"] + (["candidate"] if args.candidate else [])
    candidate = args.candidate.expanduser().resolve() if args.candidate else None
    if candidate and not candidate.is_file():
        raise ValueError("candidate SKILL.md does not exist")
    plan = []
    for run in range(1, max(1, args.runs) + 1):
        order = variants[run % len(variants) :] + variants[: run % len(variants)]
        plan.extend((run, variant) for variant in order)
    if not args.dry_run and not args.model:
        parser.error("--model is required for reproducible comparisons")
    if (
        not args.dry_run
        and case.get("evaluation", {}).get("status") != "ready"
        and not args.allow_legacy
    ):
        parser.error(
            "legacy case: redesign around the skill purpose, or use --allow-legacy for exploration"
        )
    if args.dry_run:
        print(
            json.dumps(
                {
                    "case": case["id"],
                    "skill": case["skill"],
                    "fixture": str(fixture),
                    "evaluation": case.get("evaluation"),
                    "contract_version": contract_version(case, case_path),
                    "rubric": case.get("rubric", []),
                    "candidate_command": pi_command(
                        str(case["prompt"]), candidate, args.model,
                        "/skills/" + candidate.parent.name if dependency_paths(case, case_path, candidate) else "/skills"
                    )
                    if candidate
                    else None,
                    "runs": plan,
                    "treatment_command": pi_command(
                        str(case["prompt"]), skill_path, args.model,
                        "/skills/" + skill_path.parent.name if dependency_paths(case, case_path, skill_path) else "/skills"
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

    try:
        execution_preflight()
    except ValueError as exc:
        parser.error(str(exc))

    agent_version = subprocess.run(
        ["pi", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
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
            candidate,
            agent_version,
        )
        append_result(result)
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
