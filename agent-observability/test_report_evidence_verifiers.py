"""Check shared CSS preservation with only declared verifier inputs."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


CASES = Path(__file__).resolve().parents[1] / ".agents/evals"


class ReportEvidenceVerifiers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def workspace(self, case, label):
        target = self.root / case / label
        shutil.copytree(CASES / "fixtures" / case, target)
        return target

    def assert_verdict(self, case, workspace, passed):
        definition = json.loads((CASES / f"{case}.json").read_text())
        # The runner distributes only verifier inputs named in the command.
        verifier_root = self.root / "verifiers" / case
        command = []
        for part in definition["verifiers"][0]:
            if part.startswith("{case_dir}/"):
                relative = part[len("{case_dir}/"):]
                source, target = CASES / relative, verifier_root / relative
                if source.is_dir():
                    shutil.copytree(source, target, dirs_exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                command.append(str(target))
            else:
                command.append(part.replace("{workspace}", str(workspace)))
        command[0] = sys.executable
        result = subprocess.run(command, cwd=workspace, capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, passed, result.stdout + result.stderr)

    def test_shared_css_is_bundled_and_loaded(self):
        case = "implementation-report-shared-assets"
        workspace = self.workspace(case, "report")
        report = workspace / "report"
        report.mkdir()
        page = report / "index.html"
        shutil.copyfile(workspace / "legacy-report.html", page)
        (workspace / "result.md").write_text("[レポート](report/index.html)\n")
        self.assert_verdict(case, workspace, False)

        shutil.copyfile(workspace / "shared-assets/document.css", report / "document.css")
        page.write_text('<!doctype html><html><head><link rel="stylesheet" '
                        'href="document.css"></head><body>Report</body></html>')
        self.assert_verdict(case, workspace, True)


if __name__ == "__main__":
    unittest.main()
