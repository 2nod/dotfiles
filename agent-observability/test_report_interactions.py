"""Exercise filtering event handlers without a browser or private report data."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

spec = importlib.util.spec_from_file_location('interaction_report', Path(__file__).with_name('generate-report.py'))
report = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = report
spec.loader.exec_module(report)

class ReportInteractions(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node required for JavaScript event tests')
    def test_filter_search_clear_and_empty_state(self):
        setup = r'''
const assert = require('node:assert/strict');
const vm = require('node:vm');
function element(extra={}) { return Object.assign({value:'',hidden:false,textContent:'',dataset:{},events:{},classList:{contains:()=>false},addEventListener(k,f){this.events[k]=f},setAttribute(k,v){this[k]=v},focus(){this.focused=true}}, extra); }
const rows = [element({textContent:'alpha awaiting',dataset:{group:'attention'}}),element({textContent:'beta adopted',dataset:{group:'decided'}})];
const input=element(), filter=element({value:'all'}), count=element(), empty=element(), reset=element();
const card=element({dataset:{filter:'decided'}});
const elements={'#search':input,'#state-filter':filter,'#result-count':count,'#empty-results':empty,'#reset-filters':reset};
const document={querySelector:s=>elements[s]||null,querySelectorAll:s=>s==='.search-row'?rows:s==='[data-filter]'?[card]:[]};
'''
        import json
        code = setup + '\nvm.runInNewContext(' + json.dumps(report.PAGE_SCRIPT) + ', {document});\n' + r'''
assert.equal(count.textContent,'2 / 2ラウンド');
card.events.click(); assert.equal(filter.value,'decided'); assert.equal(rows[0].hidden,true); assert.equal(rows[1].hidden,false); assert.equal(card['aria-pressed'],'true');
input.value='alpha'; input.events.input(); assert.equal(empty.hidden,false); assert.equal(count.textContent,'0 / 2ラウンド');
reset.events.click(); assert.equal(filter.value,'all'); assert.equal(input.value,''); assert.equal(input.focused,true); assert.equal(empty.hidden,true); assert.ok(rows.every(r=>!r.hidden));
input.value='BETA'; input.events.input(); assert.equal(rows[1].hidden,false); assert.equal(rows[0].hidden,true);
'''
        result = subprocess.run(['node', '-e', code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
