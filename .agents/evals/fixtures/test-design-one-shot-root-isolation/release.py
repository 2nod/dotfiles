from pathlib import Path


def build_dispatch(root: Path) -> dict[str, str]:
    if root.exists():
        raise ValueError("one-shot root must be unused")
    return {"root": str(root), "status": "ready"}
