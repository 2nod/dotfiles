"""Check behavior with immutable original assertions, then check dependency and structure size."""
import ast
from pathlib import Path
import subprocess
import sys

workspace = Path(sys.argv[1])
original = Path(__file__).parent / "fixtures" / "ponytail-lazy-fallback-config"
result = subprocess.run([sys.executable, "-B", "-c", (original / "test_router.py").read_text()], cwd=workspace, capture_output=True, text=True, timeout=5)
print(result.stdout + result.stderr)
if result.returncode:
    raise SystemExit(1)
source = (workspace / "router.py").read_text()
tree = ast.parse(source)
if any(isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef)) for node in ast.walk(tree)):
    raise SystemExit("This configuration choice must not introduce dependencies or a class")
functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
if {node.name for node in functions} != {"read_default", "resolve_destination"} or len(functions) != 2:
    raise SystemExit("Preserve the two existing functions without adding a wrapper")
original_lines = sum(bool(line.strip()) for line in (original / "router.py").read_text().splitlines())
if sum(bool(line.strip()) for line in source.splitlines()) > original_lines + 2:
    raise SystemExit("The shared resolver needs only a small change")
