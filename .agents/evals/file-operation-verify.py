import pathlib,sys,json,importlib.util
w=pathlib.Path(sys.argv[1]);o=pathlib.Path(sys.argv[2]);skill=sys.argv[3];negative=sys.argv[4]=="negative"
if not (w/"result.md").is_file() or not (w/"result.md").read_text().strip():raise SystemExit(1)
if negative:
 for p in o.rglob("*"):
  if p.is_file() and (not (w/p.relative_to(o)).is_file() or p.read_bytes()!=(w/p.relative_to(o)).read_bytes()):raise SystemExit(1)
 extras=[p for p in w.rglob("*") if p.is_file() and p.relative_to(w).as_posix()!="result.md" and not (o/p.relative_to(w)).is_file() and "__pycache__" not in p.parts]
 raise SystemExit(bool(extras))
if skill=="notion-workspace-maintenance":
 if (w/"kb/other.md").read_bytes()!=(o/"kb/other.md").read_bytes() or (w/"evidence.json").read_bytes()!=(o/"evidence.json").read_bytes():raise SystemExit(1)
 for p in ["kb/cache.md","kb/_index.md"]:
  if (w/p).read_bytes()==(o/p).read_bytes():raise SystemExit(1)
 # Semantic claims are reviewed separately; strings are not used as a correctness proxy.
elif skill=="pr-review-fix-workflow":
 for p in ["personal.txt","comments.json"]:
  if (w/p).read_bytes()!=(o/p).read_bytes():raise SystemExit(1)
 spec=importlib.util.spec_from_file_location("parser",w/"parser.py");m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 try:m.normalize(None)
 except ValueError:pass
 else:raise SystemExit(1)
 for v,expected in [("", ""),(" a ","a"),(0,"0")]:
  if m.normalize(v)!=expected:raise SystemExit(1)
 if not (w/"reply.md").is_file():raise SystemExit(1)
elif skill=="skill-maintenance":
 if (w/"installed/keep/SKILL.md").read_bytes()!=(o/"installed/keep/SKILL.md").read_bytes():raise SystemExit(1)
 base=w/"skills/software-development/review-helper"
 for rel in ["SKILL.md","references/checklist.md","templates/findings.md"]:
  if not (base/rel).is_file() or not (base/rel).read_text().strip():raise SystemExit(1)
 expected={str(p.relative_to(base)):p.read_bytes() for p in base.rglob("*") if p.is_file()}
 for name in ["runtime-a","runtime-b"]:
  actual={str(p.relative_to(w/name/"software-development/review-helper")):p.read_bytes() for p in (w/name/"software-development/review-helper").rglob("*") if p.is_file()}
  if actual!=expected:raise SystemExit(1)
