import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

spec = importlib.util.spec_from_file_location('input_runner',Path(__file__).with_name('evaluate-skill.py'))
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

def trace(text):
    return json.dumps({'type':'message_end','message':{'role':'user','content':[{'type':'text','text':text}]}})

class InputTest(unittest.TestCase):
    def test_missing_mixed_and_duplicate_input_rejected(self):
        self.assertTrue(runner.input_check(trace('review'), 'review'))
        for output in ['',trace('launcher code\nreview'),trace('review')+'\n'+trace('review')]:
            self.assertFalse(runner.input_check(output,'review'))

    def test_closed_stdin_does_not_inherit_launcher_text(self):
        # Parent gets nonempty input; child receives EOF using the runner's policy.
        code = "import subprocess,sys; assert sys.stdin.read()=='launcher'; r=subprocess.run([sys.executable,'-c','import sys;print(repr(sys.stdin.read()))'],stdin=subprocess.DEVNULL,capture_output=True,text=True); assert r.stdout.strip()==\"''\""
        result=subprocess.run([sys.executable,'-c',code],input='launcher',text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
