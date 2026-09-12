import json,sys,pathlib
p=pathlib.Path(__file__).with_name("state.json")
s=json.loads(p.read_text());a=sys.argv[1:];action=a[0] if a else "inspect"
if action=="inspect":print(json.dumps(s));raise SystemExit(0)
if action=="cancel_callback":s["jobs"][a[1]]["callback"]="cancelled"
elif action=="release_lease":s["jobs"][a[1]]["lease"]="released"
elif action=="remove_partial":s["jobs"][a[1]]["artifact"]="absent"
elif action=="finish_cancel":s["jobs"][a[1]]["status"]="cancelled"
elif action=="remove_volume":del s["volumes"][a[1]]
elif action=="remove_worktree":del s["worktrees"][a[1]]
elif action=="configure_client":s["client"].update(host=a[1],port=int(a[2]))
elif action=="probe":
 c=s["client"];d=s["db"];ok=c["host"]=="127.0.0.1" and c["port"]==d["published"] and d["healthy"]
 print("connected" if ok else "connection failed")
 with open("events.jsonl","a") as f:f.write(json.dumps({"action":a,"ok":ok})+"\n")
 raise SystemExit(0 if ok else 1)
elif action=="sync_unfinished":s["unfinished"]=sorted(k for k,v in s["tasks"].items() if v["work"]!="accepted done")
else:raise SystemExit("unknown action")
p.write_text(json.dumps(s,indent=2)+"\n")
with open("events.jsonl","a") as f:f.write(json.dumps({"action":a,"ok":True})+"\n")
