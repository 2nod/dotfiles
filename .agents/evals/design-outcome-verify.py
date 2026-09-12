import pathlib,sys
w,o=map(pathlib.Path,sys.argv[1:3]);kind=sys.argv[3];artifact=sys.argv[4]
if not (w/"result.md").is_file() or not (w/"result.md").read_text().strip():raise SystemExit(1)
if (w/"scenario.json").read_bytes()!=(o/"scenario.json").read_bytes():raise SystemExit(1)
if kind=="negative":
 if any(p.suffix.lower() in (".html",".svg",".png") for p in w.rglob("*") if p.is_file()):raise SystemExit(1)
elif artifact=="html":
 if not (w/"index.html").is_file() or not (w/"index.html").read_text().strip():raise SystemExit(1)
