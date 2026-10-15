import json
from pathlib import Path
RULES = ("coverage", "preservation", "references")
def records():
    return json.loads(Path(__file__).with_name("ledger.json").read_text())
def get_detail(note_id):
    return next(note["detail"] for note in records() if note["id"] == note_id)
def build_report():
    return {"checks": [{"note_id": note["id"], "rule": rule,
        "verdict": "issue" if rule == "preservation" and note["repair_required"] else "unverified",
        "reason": note["detail"], "evidence": [note["id"]]}
        for note in records() for rule in RULES]}
