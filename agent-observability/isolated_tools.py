"""Credential-free eval tool worker. No host mounts, network, or model calls.

The paid runner remains paused until fresh case/input plans are verified.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import selectors
import time
import uuid

IMAGE = "sha256:0d9e9a8dcd5a83ea737ed92227a6591a31ad70c8bb722b0c51aff7ae23a88b6a"
MAX_BYTES = 8 * 1024 * 1024

# Runs inside the container. Paths are checked there, including symlinks.
WORKER = r"""
import base64, json, os, pathlib, stat, sys
request = json.load(sys.stdin)
def path(value, write=False):
    p = pathlib.Path(value)
    if not p.is_absolute(): p = pathlib.Path('/workspace') / p
    p = p.resolve()
    roots = [pathlib.Path('/workspace')] if write else [pathlib.Path('/workspace'), pathlib.Path('/skills')]
    if not any(p == root or root in p.parents for root in roots):
        raise ValueError('path outside evaluation inputs')
    return p
op = request['op']
if op == 'read':
    p = path(request['path'])
    if not p.is_file() or p.stat().st_size > 8*1024*1024: raise ValueError('not a bounded regular file')
    result = base64.b64encode(p.read_bytes()).decode()
elif op == 'write':
    p = path(request['path'], True)
    data = base64.b64decode(request['data'], validate=True)
    if len(data) > 8*1024*1024: raise ValueError('file too large')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    result = True
elif op == 'snapshot':
    result = {}; total = 0
    for p in sorted(pathlib.Path('/workspace').rglob('*')):
        mode = p.lstat().st_mode
        if stat.S_ISDIR(mode): continue
        if not stat.S_ISREG(mode) or p.stat().st_nlink != 1:
            raise ValueError('non-regular artifact rejected')
        total += p.stat().st_size
        if total > 8*1024*1024: raise ValueError('artifacts too large')
        result[str(p.relative_to('/workspace'))] = base64.b64encode(p.read_bytes()).decode()
else:
    raise ValueError('unsupported operation')
print(json.dumps(result))
"""


def fixture_files(root: Path) -> dict[str, bytes]:
    """Reject aliases and devices before copying approved synthetic inputs."""
    files = {}
    total = 0
    if root.is_symlink() or not root.is_dir():
        raise ValueError("fixture must be a real directory")
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("symlink input rejected")
        if path.is_dir():
            continue
        if not path.is_file() or path.stat().st_nlink != 1:
            raise ValueError("non-regular input rejected")
        total += path.stat().st_size
        if total > MAX_BYTES:
            raise ValueError("input bundle too large")
        files[str(path.relative_to(root))] = path.read_bytes()
    return files


class ToolSandbox:
    """One disposable Linux worker per variant; never receives host auth/env."""

    def __init__(self, docker: str, image: str = IMAGE):
        if not Path(docker).is_absolute():
            raise ValueError("docker executable must be an absolute trusted path")
        if image != IMAGE:
            raise ValueError("unverified runtime image")
        self.docker = docker
        self.name = "skill-eval-offline-" + uuid.uuid4().hex
        self.created = False
        # Docker may need client settings to find Colima. These stay on the HOST.
        self.client_env = {
            key: os.environ[key]
            for key in (
                "HOME",
                "PATH",
                "DOCKER_HOST",
                "DOCKER_CONTEXT",
                "DOCKER_CONFIG",
            )
            if key in os.environ
        }

    def _docker(self, args, *, data=None, timeout=30):
        command = [self.docker, *args]
        chunks = {"stdout": bytearray(), "stderr": bytearray()}
        pending = memoryview(data or b"")
        deadline = time.monotonic() + timeout
        with subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.client_env,
        ) as process:
            try:
                with selectors.DefaultSelector() as selector:
                    for stream, name in (
                        (process.stdout, "stdout"),
                        (process.stderr, "stderr"),
                    ):
                        os.set_blocking(stream.fileno(), False)
                        selector.register(stream, selectors.EVENT_READ, name)
                    if pending:
                        os.set_blocking(process.stdin.fileno(), False)
                        selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
                    else:
                        process.stdin.close()
                    while selector.get_map():
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise subprocess.TimeoutExpired(command, timeout)
                        for key, _ in selector.select(min(remaining, 0.2)):
                            if key.data == "stdin":
                                count = os.write(key.fd, pending[:65536])
                                pending = pending[count:]
                                if not pending:
                                    selector.unregister(key.fileobj)
                                    key.fileobj.close()
                            else:
                                data = os.read(key.fd, 65536)
                                if not data:
                                    selector.unregister(key.fileobj)
                                else:
                                    chunks[key.data].extend(data)
                                    if sum(map(len, chunks.values())) > MAX_BYTES * 2:
                                        raise ValueError("worker output limit exceeded")
                code = process.wait(timeout=max(0.01, deadline - time.monotonic()))
            except BaseException:
                process.kill()
                process.wait()
                raise
        stdout, stderr = bytes(chunks["stdout"]), bytes(chunks["stderr"])
        if code:
            raise subprocess.CalledProcessError(code, command, stdout, stderr)
        return subprocess.CompletedProcess(command, code, stdout, stderr)

    def __enter__(self):
        args = [
            "create",
            "--pull=never",
            "--name",
            self.name,
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit=64",
            "--memory=256m",
            "--memory-swap=256m",
            "--cpus=1",
            "--user=65534:65534",
            "--workdir=/workspace",
            "--tmpfs=/workspace:rw,exec,nosuid,nodev,size=32m,mode=1777",
            "--tmpfs=/tmp:rw,nosuid,nodev,size=16m,mode=1777",
            "--tmpfs=/skills:rw,exec,nosuid,nodev,size=16m,mode=755",
            "--env=HOME=/tmp",
            "--env=LANG=C.UTF-8",
            "--entrypoint=/bin/sleep",
            IMAGE,
            "infinity",
        ]
        self._docker(args)
        self.created = True
        try:
            self._docker(["start", self.name])
        except BaseException:
            self.close()
            raise
        return self

    def close(self):
        if self.created:
            self._docker(["rm", "--force", self.name])
            self.created = False

    def __exit__(self, *_):
        self.close()

    def request(self, request):
        raw = json.dumps(request).encode()
        if len(raw) > MAX_BYTES * 2:
            raise ValueError("request too large")
        result = self._docker(
            ["exec", "-i", self.name, "/usr/bin/python3", "-I", "-c", WORKER], data=raw
        )
        return json.loads(result.stdout)

    def read(self, path):
        return base64.b64decode(self.request({"op": "read", "path": str(path)}))

    def write(self, path, data):
        return self.request(
            {"op": "write", "path": str(path), "data": base64.b64encode(data).decode()}
        )

    def load_fixture(self, root: Path):
        for name, data in fixture_files(root).items():
            self.write(name, data)

    def load_skill(self, root: Path):
        # Bootstrap is trusted, never exposed as a model tool. No symlinks copied.
        self.load_readonly(
            fixture_files(root),
            {
                str(p.relative_to(root))
                for p in root.rglob("*")
                if p.is_file() and p.stat().st_mode & 0o111
            },
        )

    def load_readonly(self, contents, executable=()):
        if any(
            Path(name).is_absolute() or ".." in Path(name).parts for name in contents
        ):
            raise ValueError("invalid bundle path")
        files = {
            name: base64.b64encode(data).decode() for name, data in contents.items()
        }
        script = f"import base64,json,pathlib,sys\nfor n,d in json.load(sys.stdin).items():\n p=pathlib.Path('/skills')/n; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(base64.b64decode(d)); p.chmod(0o555 if n in {set(executable)!r} else 0o444)\n"
        self._docker(
            [
                "exec",
                "-i",
                "--user=0:0",
                self.name,
                "/usr/bin/python3",
                "-I",
                "-c",
                script,
            ],
            data=json.dumps(files).encode(),
        )

    def bash(self, command: str, timeout=10):
        # Only the shell INSIDE the worker interprets model-supplied text.
        # env -i prevents even the generic image's environment from being inherited.
        try:
            return self._docker(
                [
                    "exec",
                    self.name,
                    "/usr/bin/timeout",
                    "--kill-after=1",
                    str(timeout),
                    "/usr/bin/env",
                    "-i",
                    "PATH=/usr/local/bin:/usr/bin:/bin",
                    "HOME=/tmp",
                    "LANG=C.UTF-8",
                    "/bin/bash",
                    "--noprofile",
                    "--norc",
                    "-c",
                    command,
                ],
                timeout=timeout + 5,
            )
        except subprocess.CalledProcessError as exc:
            return subprocess.CompletedProcess(
                exc.cmd, exc.returncode, exc.stdout, exc.stderr
            )

    def snapshot(self):
        return {
            name: base64.b64decode(data)
            for name, data in self.request({"op": "snapshot"}).items()
        }


def tool_request(worker, request):
    """Only these four requests are exposed; bootstrap and Docker APIs are not."""
    op = request["op"]
    if op == "bash":
        timeout = request.get("timeout", 30)
        if not isinstance(timeout, int) or not 1 <= timeout <= 60:
            raise ValueError("invalid tool timeout")
        result = worker.bash(request["command"], timeout)
        return {
            "text": (result.stdout + result.stderr).decode(errors="replace")[:100000],
            "isError": result.returncode != 0,
        }
    if op == "read":
        lines = worker.read(request["path"]).decode("utf-8").splitlines(keepends=True)
        offset, limit = request.get("offset", 1), request.get("limit", 2000)
        if (
            not isinstance(offset, int)
            or not isinstance(limit, int)
            or offset < 1
            or limit < 1
        ):
            raise ValueError("invalid line range")
        return {"text": "".join(lines[offset - 1 : offset - 1 + limit])[:100000]}
    if op == "write":
        worker.write(request["path"], request["content"].encode())
        return {"text": "Written in isolated workspace."}
    if op == "edit":
        original = worker.read(request["path"]).decode("utf-8")
        old = request["oldText"]
        if not old or original.count(old) != 1:
            raise ValueError("edit requires exactly one matching block")
        worker.write(
            request["path"], original.replace(old, request["newText"]).encode()
        )
        return {"text": "Edited in isolated workspace."}
    raise ValueError("unsupported model tool")


if __name__ == "__main__":
    import argparse
    import re
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", required=True)
    parser.add_argument("--docker", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"skill-eval-offline-[a-f0-9]{32}", args.worker):
        parser.error("invalid worker name")
    worker = ToolSandbox(args.docker)
    worker.name = args.worker
    # Only attach to an already-created worker. Never starts a container/model.
    request = json.loads(sys.stdin.read(MAX_BYTES * 2 + 1))
    print(json.dumps(tool_request(worker, request)))
