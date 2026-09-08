"""Accept alternative report layouts; reject absent artifacts and changed evidence."""

import importlib.util
import pathlib
import shutil
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "report_gate", ROOT / ".agents/evals/report-artifact-verify.py"
)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class ReportArtifactTests(unittest.TestCase):
    def test_original_fails_two_minimal_layouts_pass_and_tampering_fails(self):
        for name in (
            "purpose-build-experiment-report-site-defined-artifact",
            "purpose-build-implementation-report-site-artifact",
        ):
            source = ROOT / ".agents/evals/fixtures" / name
            with self.subTest(case=name), tempfile.TemporaryDirectory() as temp:
                work = pathlib.Path(temp) / "workspace"
                shutil.copytree(source, work)
                self.assertEqual(gate.verify(work, source), 1)
                (work / "result.md").write_text("[Report](index.html)")
                for body in (
                    "<h1>Comparison</h1><p>Results and limitations</p>",
                    "<article><h2>Report</h2><table><tr><td>Evidence</td></tr></table></article>",
                ):
                    (work / "index.html").write_text(
                        "<html><body>" + body + "</body></html>"
                    )
                    self.assertEqual(gate.verify(work, source), 0)
                (work / "scenario.json").write_text("{}")
                self.assertEqual(gate.verify(work, source), 1)


if __name__ == "__main__":
    unittest.main()
