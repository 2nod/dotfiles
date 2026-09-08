"""Offline isolation checks. Docker tests are opt-in and never call a model."""

import json
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from isolated_tools import ToolSandbox, fixture_files


class InputBoundaryTest(unittest.TestCase):
    def test_symlink_and_hardlink_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "file").write_text("synthetic")
            (root / "alias").symlink_to(root / "file")
            with self.assertRaises(ValueError):
                fixture_files(root)
            (root / "alias").unlink()
            os.link(root / "file", root / "alias")
            with self.assertRaises(ValueError):
                fixture_files(root)

    def test_runtime_cannot_be_overridden(self):
        with self.assertRaises(ValueError):
            ToolSandbox("/usr/bin/docker", "arbitrary-image")


@unittest.skipUnless(
    os.environ.get("SKILL_EVAL_OFFLINE_DOCKER") == "1", "offline Docker opt-in required"
)
class DockerBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="eval-canary-")
        self.root = Path(self.temp.name)
        self.canary = self.root / "host-only.txt"
        self.canary.write_text("synthetic-host-file-canary")
        self.env_patch = patch.dict(
            os.environ, {"EVAL_SYNTHETIC_SECRET": "synthetic-env-canary"}
        )
        self.env_patch.start()
        self.worker = ToolSandbox(str(Path(shutil.which("docker")).absolute()))
        self.worker.__enter__()

    def tearDown(self):
        self.worker.close()
        self.env_patch.stop()
        self.temp.cleanup()

    def test_fixture_roundtrip_and_model_style_code_execution(self):
        fixture = self.root / "fixture"
        fixture.mkdir()
        (fixture / "sum.py").write_text("print(2+3)")
        self.worker.load_fixture(fixture)
        self.assertEqual(self.worker.bash("python3 sum.py > result.txt").returncode, 0)
        self.assertEqual(self.worker.snapshot()["result.txt"], b"5\n")
        self.assertEqual(self.worker.read("sum.py"), b"print(2+3)")

    def test_outside_reads_and_symlink_escape_are_denied(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.worker.read(str(self.canary))
        self.assertNotEqual(self.worker.bash("cat " + str(self.canary)).returncode, 0)
        self.worker.bash("ln -s /etc/passwd escape")
        with self.assertRaises(subprocess.CalledProcessError):
            self.worker.read("escape")
        with self.assertRaises(subprocess.CalledProcessError):
            self.worker.snapshot()
        self.assertEqual(self.canary.read_text(), "synthetic-host-file-canary")

    def test_skill_is_read_only_even_through_shell(self):
        skill = self.root / "skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("Synthetic instructions")
        (skill / "check.sh").write_text("#!/bin/sh\necho script-ok")
        (skill / "check.sh").chmod(0o755)
        self.worker.load_skill(skill)
        self.assertEqual(self.worker.bash("/skills/check.sh").stdout, b"script-ok\n")
        self.assertEqual(
            self.worker.read("/skills/SKILL.md"), b"Synthetic instructions"
        )
        self.assertNotEqual(
            self.worker.bash("echo changed > /skills/SKILL.md").returncode, 0
        )
        self.assertNotEqual(self.worker.bash("rm /skills/SKILL.md").returncode, 0)
        with self.assertRaises(subprocess.CalledProcessError):
            self.worker.write("/skills/new", b"changed")

    def test_no_host_environment_socket_or_mounts(self):
        result = self.worker.bash(
            "env; cat /proc/1/environ; test ! -S /var/run/docker.sock"
        )
        self.assertNotIn(b"synthetic-env-canary", result.stdout)
        info = json.loads(self.worker._docker(["inspect", self.worker.name]).stdout)[0]
        self.assertEqual(info["HostConfig"]["Binds"], None)
        self.assertEqual(info["HostConfig"]["NetworkMode"], "none")
        self.assertTrue(info["HostConfig"]["ReadonlyRootfs"])
        self.assertEqual(info["Config"]["User"], "65534:65534")
        self.assertTrue(all(m["Type"] != "bind" for m in info["Mounts"]))

    def test_network_fails_and_host_file_cannot_be_written(self):
        result = self.worker.bash(
            "python3 -c \"import socket; socket.create_connection(('192.0.2.1',443),1)\""
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(
            self.worker.bash("echo changed > " + str(self.canary)).returncode, 0
        )
        self.assertEqual(self.canary.read_text(), "synthetic-host-file-canary")

    def test_pi_adapter_uses_only_the_isolated_worker(self):
        script = r"""
import register from './agent-observability/isolated-pi-tools.mjs';
import assert from 'node:assert/strict';
const tools = {};
register({registerTool: tool => tools[tool.name] = tool});
assert.deepEqual(Object.keys(tools).sort(), ['bash','edit','read','write']);
await tools.write.execute('1', {path:'result.txt', content:'before'});
await tools.edit.execute('2', {path:'result.txt', oldText:'before', newText:'after'});
assert.equal((await tools.read.execute('3', {path:'result.txt'})).content[0].text, 'after');
assert.equal((await tools.bash.execute('4', {command:'cat result.txt'})).content[0].text, 'after');
await assert.rejects(tools.read.execute('5', {path:process.env.TEST_HOST_CANARY}));
delete process.env.SKILL_EVAL_CONTAINER;
assert.throws(() => register({registerTool: () => {throw Error('must not register')}}));
console.log('adapter: 4 isolated tools; denied host read; missing configuration fails closed');
"""
        env = dict(
            os.environ,
            SKILL_EVAL_CONTAINER=self.worker.name,
            SKILL_EVAL_DOCKER=self.worker.docker,
            SKILL_EVAL_PYTHON=sys.executable,
            TEST_HOST_CANARY=str(self.canary),
        )
        script = script.replace("'./agent-observability/isolated-pi-tools.mjs'",
                                json.dumps(Path(__file__).with_name('isolated-pi-tools.mjs').resolve().as_uri()))
        node = shutil.which("node")
        result = subprocess.run(
            [node, "--input-type=module", "-e", script],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_runner_keeps_agent_and_verifier_off_host_without_model_calls(self):
        evaluator_path = Path(__file__).with_name("evaluate-skill.py")
        spec = importlib.util.spec_from_file_location(
            "offline_evaluator", evaluator_path
        )
        evaluator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(evaluator)
        fixture = self.root / "fixture"
        fixture.mkdir()
        (fixture / "input.txt").write_text("synthetic")
        skill = self.root / "skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("Produce result.md")
        (self.root / "verify.py").write_text(
            "import pathlib,sys\n"
            "root=pathlib.Path(sys.argv[1])\n"
            'assert (root / "result.md").read_text() == "synthetic result"\n'
            f"assert not pathlib.Path({str(self.canary)!r}).exists()\n"
        )
        case = dict(
            id="offline-canary",
            skill="synthetic",
            fixture="fixture",
            skill_path="skill/SKILL.md",
            prompt="synthetic prompt",
            verifiers=[["python3", "{case_dir}/verify.py", "{workspace}"]],
        )
        case_path = self.root / "case.json"
        case_path.write_text(json.dumps(case))
        real_run = subprocess.run
        model_calls = []

        def stub_model(command, **kwargs):
            if command[0] != "pi":
                return real_run(command, **kwargs)
            model_calls.append(command)
            self.assertIn("--no-builtin-tools", command)
            attached = ToolSandbox(kwargs["env"]["SKILL_EVAL_DOCKER"])
            attached.name = kwargs["env"]["SKILL_EVAL_CONTAINER"]
            attached.write("result.md", b"synthetic result")
            return subprocess.CompletedProcess(command, 0, "", "")

        with (
            patch.object(evaluator, "ROOT", self.root / "results"),
            patch.object(subprocess, "run", side_effect=stub_model),
        ):
            result = evaluator.run_once(
                case, case_path, "treatment", 1, "offline/stub", 10, "offline"
            )
        self.assertEqual(len(model_calls), 1)  # Intercepted, not executed.
        self.assertTrue(result["success"])
        self.assertEqual(result["isolation"], "docker-no-host-mounts-v1")
        self.assertEqual(result["changed_paths"], ["result.md"])
        self.assertEqual(self.canary.read_text(), "synthetic-host-file-canary")

    def test_actual_pi_loads_only_isolated_tools_without_credentials_or_prompt(self):
        adapter = Path(__file__).with_name("isolated-pi-tools.mjs").resolve().as_uri()
        extension = self.root / "offline-extension.mjs"
        extension.write_text(
            f"import register from {json.dumps(adapter)};\n"
            "export default function(pi) {\n"
            " const registered={}; register({registerTool:t=>{registered[t.name]=t;pi.registerTool(t)}});\n"
            " pi.on('session_start',async()=>{\n"
            "  const names=pi.getActiveTools().sort();\n"
            "  if(JSON.stringify(names)!==JSON.stringify(['bash','edit','read','write'])) throw Error('unexpected tools:'+names);\n"
            "  await registered.write.execute('offline',{path:'actual-pi.txt',content:'offline-loader-ok'});\n"
            "  console.log('OFFLINE_LOADER_OK'); process.exit(0);\n"
            " });\n"
            "}\n"
        )
        home = self.root / "empty-home"
        home.mkdir()
        env = {key: os.environ[key] for key in ("PATH",) if key in os.environ}
        env.update(
            HOME=str(home),
            PI_CODING_AGENT_DIR=str(home / "pi"),
            SKILL_EVAL_CONTAINER=self.worker.name,
            SKILL_EVAL_DOCKER=self.worker.docker,
            SKILL_EVAL_PYTHON=sys.executable,
            DOCKER_HOST=os.environ.get("DOCKER_HOST") or self.worker._docker(
                ["context", "inspect", "--format", "{{.Endpoints.docker.Host}}"]
            ).stdout.decode().strip(),
        )
        command = [
            shutil.which("pi"),
            "--mode",
            "rpc",
            "--no-session",
            "--no-skills",
            "--no-extensions",
            "--no-context-files",
            "--no-prompt-templates",
            "--no-themes",
            "--no-builtin-tools",
            "--extension",
            str(extension),
            "--model",
            "openai-codex/gpt-5.6-sol",
        ]
        result = subprocess.run(
            command,
            cwd=home,
            env=env,
            input="",
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OFFLINE_LOADER_OK", result.stdout, result.stderr)
        self.assertNotIn("message_start", result.stdout)
        self.assertEqual(self.worker.read("actual-pi.txt"), b"offline-loader-ok")

    def test_output_flood_is_bounded(self):
        with self.assertRaisesRegex(ValueError, "output limit"):
            self.worker.bash("python3 -c \"print('x'*20000000)\"")

    def test_timeout_and_removal(self):
        self.assertEqual(self.worker.bash("sleep 20", timeout=1).returncode, 124)
        name = self.worker.name
        self.worker.close()
        with self.assertRaises(subprocess.CalledProcessError):
            self.worker._docker(["inspect", name])


if __name__ == "__main__":
    unittest.main()
