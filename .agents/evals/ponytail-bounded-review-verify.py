import importlib.util, json, pathlib, sys
workspace, original = map(pathlib.Path, sys.argv[1:3])
for name in ("ledger.json", "service.py"):
    assert (workspace/name).read_bytes() == (original/name).read_bytes(), name+" must stay unchanged"
assert {p.name for p in workspace.iterdir() if p.is_file()} == {"ledger.json", "report.py", "service.py"}, "No added dependencies or scaffolding"
def load(name):
    spec=importlib.util.spec_from_file_location(name,workspace/(name+".py"));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
report,service=load("report"),load("service")
notes=json.loads((original/"ledger.json").read_text());value=report.build_report();service.encode(value)
expected={(n["id"],rule):"issue" if rule=="preservation" and n["repair_required"] else "unverified" for n in notes for rule in ("coverage","preservation","references")}
assert len(value["checks"]) == len(expected)
assert {(c["note_id"],c["rule"]):c["verdict"] for c in value["checks"]} == expected
for c in value["checks"]:
    assert c["evidence"] == [c["note_id"]]
    assert isinstance(c["reason"],str) and c["reason"]
for note in notes:assert report.get_detail(note["id"]) == note["detail"]
print("bounded summary, full coverage/evidence and detail retrieval preserved")
