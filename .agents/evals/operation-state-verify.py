import pathlib,json,sys
w=pathlib.Path(sys.argv[1]);o=pathlib.Path(sys.argv[2]);expected=json.loads(pathlib.Path(sys.argv[3]).read_text())
for name in ["sandboxctl.py","README.md"]:
 if (w/name).read_bytes()!=(o/name).read_bytes():raise SystemExit(1)
if json.loads((w/"state.json").read_text())!=expected:raise SystemExit(1)
if not (w/"result.md").is_file() or not (w/"result.md").read_text().strip():raise SystemExit(1)
