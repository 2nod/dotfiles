import json
import pathlib
import sys

root = pathlib.Path(__file__).parent
path = root / 'state.json'
state = json.loads(path.read_text())
args = sys.argv[1:] or ['inspect']
action = args[0]
ok = True
if args == ['inspect']:
    print(json.dumps(state))
elif args == ['migrate_dependencies', 'review']:
    state['dependency']['owner'] = 'review'
elif args == ['rebind_service', 'review']:
    state['service']['source'] = 'review'
elif args == ['remove_worktree', 'old']:
    state['worktrees'].pop('old')
elif args == ['probe']:
    ok = (state['dependency']['owner'] in state['worktrees']
          and state['service']['source'] in state['worktrees']
          and state['service']['running']
          and state['service']['volume'] in state['volumes'])
    print(json.dumps({'healthy': ok}))
else:
    raise SystemExit('unknown operation')
if action not in ['inspect', 'probe']:
    path.write_text(json.dumps(state, indent=2) + '\n')
with (root / 'events.jsonl').open('a') as output:
    output.write(json.dumps({'action': args, 'ok': ok}) + '\n')
raise SystemExit(0 if ok else 1)
