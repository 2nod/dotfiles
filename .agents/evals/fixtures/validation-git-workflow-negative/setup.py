import pathlib,subprocess,os
r=pathlib.Path("repo")
if r.exists():raise SystemExit("already initialized")
r.mkdir()
env={**os.environ,"GIT_AUTHOR_DATE":"2020-01-01T00:00:00Z","GIT_COMMITTER_DATE":"2020-01-01T00:00:00Z"}
def git(*args):return subprocess.check_output(["git","-C",str(r),*args],env=env,text=True).strip()
git("init","-b","main");git("config","user.name","Synthetic");git("config","user.email","synthetic@example.invalid")
(r/"app.txt").write_text("base\n");(r/"personal.txt").write_text("saved\n");git("add","app.txt","personal.txt");git("commit","-m","base")
git("switch","-c","mixed");(r/"unrelated.txt").write_text("unrelated\n");git("add","unrelated.txt");git("commit","-m","unrelated")
(r/"app.txt").write_text("task\n");git("add","app.txt");git("commit","-m","task")
(r/"personal.txt").write_text("unsaved user note\n")
print("Prepared synthetic repo on mixed with an unrelated commit, task commit, and dirty personal.txt")
