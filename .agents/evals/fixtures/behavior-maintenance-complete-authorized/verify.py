from pathlib import Path
assert "Run a check" in Path("sample/SKILL.md").read_text()
print("verified")
