"""Exercise report verifiers through their CLI with valid and misleading HTML."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


CASES = Path(__file__).resolve().parents[1] / ".agents/evals"
TEXT_CASES = (
    "experiment-client-skill-load-evidence",
    "experiment-input-schema-evidence",
    "experiment-report-completion-levels",
    "experiment-report-page-identity",
)
CSS_CASE = "implementation-report-shared-assets"


def corrected_report(case, workspace):
    if case == TEXT_CASES[0]:
        data = {
            "cliSuccessCases": 3,
            "definitionLoadedCases": 2,
            "cases": [
                {"id": "case-a", "status": "confirmed", "evidence": "skill_tool"},
                {"id": "case-b", "status": "confirmed", "evidence": "command_expansion"},
                {"id": "case-c", "status": "unconfirmed", "evidence": "none"},
            ],
        }
        body = "<table>" + "".join(
            f'<tr data-case="{r["id"]}" data-status="{r["status"]}" '
            f'data-evidence="{r["evidence"]}"><td>{r["id"]}</td>'
            f'<td>{r["status"]}</td><td>{r["evidence"]}</td></tr>'
            for r in data["cases"]
        ) + "</table>"
    elif case == TEXT_CASES[1]:
        data = {
            "calls": 3, "passed": 1, "failed": 2,
            "records": [
                {"id": "nested-range", "passed": False},
                {"id": "optional-limit", "passed": True},
                {"id": "empty-arguments", "passed": False},
            ],
        }
        body = "<p>登録済み入力契約でmock観測を評価。実サービスは未検証。</p><table>"
        body += "".join(
            f'<tr data-case="{r["id"]}" data-passed="{str(r["passed"]).lower()}">'
            f'<td>{r["id"]}</td><td>{str(r["passed"]).lower()}</td></tr>'
            for r in data["records"]
        ) + "</table>"
    elif case == TEXT_CASES[2]:
        data = {
            "reference_status": "historical_unapproved",
            "runs": [
                {"id": "run-a", "harness_success": True, "workflow_status": "not_saved"},
                {"id": "run-b", "harness_success": True, "workflow_status": "failed"},
                {"id": "run-c", "harness_success": True, "workflow_status": "submitted"},
            ],
        }
        body = "<table>" + "".join(
            f'<tr data-run-id="{r["id"]}"><td>{r["id"]}</td>'
            f'<td>{r["workflow_status"]}</td></tr>' for r in data["runs"]
        ) + '</table><p id="reference-status">historical_unapproved</p>'
    elif case == TEXT_CASES[3]:
        source = json.loads((workspace / "experiment-source.json").read_text())
        data = {"cases": source["pages"]}
        body = "".join(
            f'<figure data-case-id="{r["case_id"]}"><img src="{r["source_file"]}">'
            f'<figcaption>Manuscript {r["manuscript_number"]}; Folio {r["printed_folio"]}; '
            f'{Path(r["source_file"]).name}. {r["public_note"]}</figcaption></figure>'
            for r in source["pages"]
        )
    else:
        report = workspace / "report"
        report.mkdir()
        shutil.copyfile(workspace / "shared-assets/document.css", report / "document.css")
        page = report / "index.html"
        page.write_text('<!doctype html><html><head><link rel="stylesheet" '
                        'href="document.css"></head><body>Report</body></html>')
        (workspace / "result.md").write_text("[レポート](report/index.html)\n")
        return page
    (workspace / "report-data.json").write_text(json.dumps(data))
    page = workspace / ("index.html" if case in TEXT_CASES[:2] else "report.html")
    page.write_text("<!doctype html><html><head><meta charset='utf-8'></head><body>"
                    + body + "</body></html>")
    (workspace / "result.md").write_text(f"[レポート]({page.name})\n")
    return page


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

    def test_unmodified_fixtures_fail_and_corrected_reports_pass(self):
        for case in (*TEXT_CASES, CSS_CASE):
            with self.subTest(case=case):
                workspace = self.workspace(case, "baseline")
                self.assert_verdict(case, workspace, False)
                corrected_report(case, workspace)
                self.assert_verdict(case, workspace, True)

    def test_valid_single_quotes_spacing_and_uppercase_tags(self):
        for case in (*TEXT_CASES, CSS_CASE):
            with self.subTest(case=case):
                workspace = self.workspace(case, "alternate-markup")
                page = corrected_report(case, workspace)
                text = page.read_text().replace('="', " = '").replace('"', "'")
                for tag in ("tr", "td", "link", "figure", "figcaption", "img"):
                    text = text.replace("<" + tag, "<" + tag.upper())
                    text = text.replace("</" + tag, "</" + tag.upper())
                page.write_text(text)
                self.assert_verdict(case, workspace, True)

    def test_results_hidden_by_ancestors_fail(self):
        for case in TEXT_CASES:
            for index, attribute in enumerate(("hidden", 'style="display: none"', 'style="visibility: hidden"')):
                with self.subTest(case=case, attribute=attribute):
                    workspace = self.workspace(case, str(index))
                    page = corrected_report(case, workspace)
                    page.write_text(page.read_text().replace("<body>", f"<body {attribute}>"))
                    self.assert_verdict(case, workspace, False)

    def test_script_style_template_and_noscript_are_not_visible_results(self):
        for case in TEXT_CASES:
            for tag in ("script", "style", "template", "noscript"):
                with self.subTest(case=case, tag=tag):
                    workspace = self.workspace(case, tag)
                    page = corrected_report(case, workspace)
                    text = page.read_text()
                    if case == TEXT_CASES[0]:
                        text = text.replace("<td>confirmed</td>", f"<td>unconfirmed<{tag}>confirmed</{tag}></td>")
                    elif case == TEXT_CASES[1]:
                        text = text.replace("<td>false</td>", f"<td>true<{tag}>false</{tag}></td>")
                    elif case == TEXT_CASES[2]:
                        text = text.replace("<td>not_saved</td>", f"<td>submitted<{tag}>not_saved</{tag}></td>")
                    else:
                        text = text.replace("<figcaption>", f"<figcaption>Wrong figure.<{tag}>")
                        text = text.replace("</figcaption>", f"</{tag}></figcaption>")
                    page.write_text(text)
                    self.assert_verdict(case, workspace, False)

    def test_inactive_and_inert_stylesheets_fail(self):
        invalid_links = (
            '<link rel="alternate stylesheet" title="Other" href="document.css">',
            '<template><link rel="stylesheet" href="document.css"></template>',
            '<noscript><link rel="stylesheet" href="document.css"></noscript>',
            '<link rel="stylesheet" disabled href="document.css">',
            '<link rel="stylesheet" media="print" href="document.css">',
        )
        for index, link in enumerate(invalid_links):
            with self.subTest(link=link):
                workspace = self.workspace(CSS_CASE, str(index))
                page = corrected_report(CSS_CASE, workspace)
                page.write_text(page.read_text().replace('<link rel="stylesheet" href="document.css">', link))
                self.assert_verdict(CSS_CASE, workspace, False)


if __name__ == "__main__":
    unittest.main()
