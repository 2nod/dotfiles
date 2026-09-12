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

    @unittest.skipUnless(shutil.which('node'), 'Node required for JavaScript event tests')
    def test_evidence_filter_deep_link_and_show_all_preserve_search(self):
        import json
        setup = r"""
const assert = require('node:assert/strict'), vm = require('node:vm');
const element = (extra={}) => Object.assign({value:'',hidden:false,events:{},dataset:{},addEventListener(k,f){this.events[k]=f},setAttribute(){},classList:{contains:()=>false},parentElement:null},extra);
const a=element({textContent:'alpha',dataset:{evidence:'recorded'},tagName:'DETAILS'});
const b=element({textContent:'beta',dataset:{evidence:'missing'},tagName:'DETAILS',scrollIntoView(){this.scrolled=true}});
const ga=element({tagName:'DETAILS',querySelectorAll:()=>[a]}),gb=element({tagName:'DETAILS',querySelectorAll:()=>[b]});
a.parentElement=ga;b.parentElement=gb;
const search=element(),evidence=element({value:'all'}),count=element(),show=element();
const document={querySelector:s=>({'#search':search,'#evidence-filter':evidence,'#result-count':count,'#show-all':show}[s]||null),querySelectorAll:s=>s==='.search-row'?[a,b]:s==='.skill-case-group'?[ga,gb]:s==='.recent-extra'?[b]:[],getElementById:id=>id==='beta'?b:null};
const location={hash:''},window=element();
"""
        checks = r"""
evidence.value='recorded';evidence.events.change();
assert.equal(a.hidden,false);assert.equal(b.hidden,true);assert.equal(ga.open,true);assert.equal(gb.hidden,true);assert.equal(count.textContent,'1 / 2ケース');
location.hash='#beta';window.events.hashchange();
assert.equal(evidence.value,'all');assert.equal(b.hidden,false);assert.equal(gb.open,true);assert.equal(b.open,true);assert.equal(b.scrolled,true);
// The usage page's show-all action must keep an unmatched row hidden.
search.value='alpha';search.events.input();
b.classList={contains:()=>true,remove(){this.contains=()=>false}};
show.events.click({currentTarget:show});
assert.equal(b.hidden,true);assert.equal(a.hidden,false);assert.equal(show.hidden,true);
"""
        result = subprocess.run(['node', '-e', setup + '\nvm.runInNewContext(' + json.dumps(report.PAGE_SCRIPT) + ', {document,location,window});\n' + checks], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
