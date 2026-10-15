#!/usr/bin/env python3
import json, pathlib, re, sys
workspace, fixture=map(pathlib.Path,sys.argv[1:3])
source=json.loads((fixture/'evidence.json').read_text())
assert json.loads((workspace/'evidence.json').read_text())==source, 'input evidence changed'
data=json.loads((workspace/'report-data.json').read_text())
assert data['details']==source['details'], 'the latest per-case verdicts must be preserved'
expected={'operationCount':source['operationCount'],'supported':sum(r['verdict']=='supported' for r in source['details']),'pending':sum(r['verdict']=='pending' for r in source['details']),'acceptanceComplete':source['acceptanceComplete']}
assert data['summary']==expected, 'summary must preserve uncertainty and distinguish execution from acceptance'
text=(workspace/'report.md').read_text()
labels={'操作件数':expected['operationCount'],'支持':expected['supported'],'保留':expected['pending'],'受入完了':str(expected['acceptanceComplete']).lower()}
for label,value in labels.items():
 assert re.search(r'^'+label+r'\s*[:：]\s*'+str(value)+r'\s*$',text,re.M), 'visible summary mismatch: '+label
for row in source['details']:
 assert re.search(r'\|\s*'+row['id']+r'\s*\|\s*'+row['verdict']+r'\s*\|',text), 'visible detail mismatch'
print('summary, details, uncertainty, and immutable evidence are consistent')
