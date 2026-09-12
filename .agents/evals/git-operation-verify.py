import pathlib,subprocess,sys
w=pathlib.Path(sys.argv[1]);o=pathlib.Path(sys.argv[2]);negative=sys.argv[3]=="negative";r=w/"repo"
def git(*a):return subprocess.check_output(["git","-c","safe.directory=*","-C",str(r),*a],text=True).strip()
if (w/"setup.py").read_bytes()!=(o/"setup.py").read_bytes():raise SystemExit(1)
if (r/"personal.txt").read_text()!="unsaved user note\n":raise SystemExit(1)
if git("show","main:app.txt")!="base" or git("rev-list","--count","main")!="1":raise SystemExit(1)
if git("rev-list","--count","mixed")!="3" or git("show","mixed:unrelated.txt")!="unrelated":raise SystemExit(1)
if negative:
 if git("branch","--format=%(refname:short)").splitlines()!=["main","mixed"]:raise SystemExit(1)
 if git("branch","--show-current")!="mixed":raise SystemExit(1)
else:
 if git("merge-base","main","review")!=git("rev-parse","main"):raise SystemExit(1)
 if git("diff","--name-only","main...review")!="app.txt":raise SystemExit(1)
 if git("show","review:app.txt")!="task":raise SystemExit(1)
if not (w/"result.md").is_file():raise SystemExit(1)
