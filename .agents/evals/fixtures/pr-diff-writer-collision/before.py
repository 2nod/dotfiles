from pathlib import Path


def run(root: Path, execute, write):
    summary = root / "summary.json"
    final = root / "final.json"
    if summary.exists() or final.exists():
        return {"status": "held"}
    result = execute()
    write(summary, result)
    write(final, {"result": result})
    return {"status": "complete"}
