import pathlib,sys
w,o=map(pathlib.Path,sys.argv[1:3]);raise SystemExit((w/sys.argv[3]).read_bytes()!=(o/sys.argv[3]).read_bytes())
