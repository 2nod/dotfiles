import pathlib,sys,subprocess
w=pathlib.Path(sys.argv[1])
if not (w/"result.md").is_file() or not (w/"result.md").read_text().strip() or not list(w.glob("test*.py")):raise SystemExit(1)
raise SystemExit(subprocess.run([sys.executable,"-m","unittest","discover","-s",str(w)],cwd=w).returncode)
