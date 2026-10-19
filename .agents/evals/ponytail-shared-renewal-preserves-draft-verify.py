import pathlib, subprocess, sys
workspace, pristine = map(pathlib.Path, sys.argv[1:3])
for name in ['scenario.cjs', 'viewer.cjs']:
    assert (workspace / name).read_bytes() == (pristine / name).read_bytes(), name + ' must remain unchanged'
result = subprocess.run(['node', 'scenario.cjs'], cwd=workspace, text=True, capture_output=True, timeout=10)
print(result.stdout, end='')
print(result.stderr, end='', file=sys.stderr)
sys.exit(result.returncode)
