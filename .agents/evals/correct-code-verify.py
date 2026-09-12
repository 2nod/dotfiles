import pathlib,sys,subprocess,importlib.util,os
w=pathlib.Path(sys.argv[1]);kind=sys.argv[2];name="parser" if kind=="parser" else "inventory"
spec=importlib.util.spec_from_file_location(name,w/(name+".py"));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
if kind=="parser":
 for x,y in [("0",0),("-2",-2),(" 12 ",12)]:
  if m.parse_count(x)!=y:raise SystemExit(1)
 for x in ["", "3x", "1.2"]:
  try:m.parse_count(x)
  except ValueError:pass
  else:raise SystemExit(1)
 if not (w/"diagnosis.md").is_file():raise SystemExit(1)
else:
 for x in [0,-1,11]:
  v=m.Inventory(10)
  try:v.reserve(x)
  except ValueError:pass
  else:raise SystemExit(1)
  if v.stock!=10:raise SystemExit(1)
 v=m.Inventory(10)
 if v.reserve(3)!=7 or v.stock!=7:raise SystemExit(1)
if not list(w.glob("test*.py")):raise SystemExit(1)
r=subprocess.run([sys.executable,"-m","unittest","discover","-s",str(w)],cwd=w,env={**os.environ,"PYTHONPYCACHEPREFIX":"/tmp/negative-code-cache"})
raise SystemExit(r.returncode)
