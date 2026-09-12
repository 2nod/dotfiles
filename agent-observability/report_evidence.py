"""One read-only evidence snapshot shared by inventory, cases and report links.

Reference screens describe recorded execution only. They never enter the
contract-version checks, comparison verdicts or adoption decision validators.
"""
import json


def load_saved_reports(root):
    reports = []
    for path in sorted((root / "eval-loops").glob("*/report.json")):
        try:
            value = json.loads(path.read_text())
        except (OSError, ValueError):
            value = {}
        reports.append((path, value if isinstance(value, dict) else {}))
    known = {path.parent for path, _ in reports}
    for path in sorted((root / "eval-loops").glob("*/report.md")):
        if path.parent not in known:
            reports.append((path.with_suffix(".json"), {}))
    return reports


def load_reference_runs(root, reports=None):
    """Expose saved native screening records without feeding them into adoption gates."""
    by_case = {}
    for path, data in reports if reports is not None else load_saved_reports(root):
        if not isinstance(data, dict):
            continue
        plan = data.get("plan")
        if not isinstance(plan, dict) or plan.get("mode") != "screen" or not plan.get("runtime"):
            continue
        rows = data.get("results", [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("case"), str):
                continue
            checks = ("exact_final_files", "no_unexpected_changes", "timed_out", "verification_required")
            known = all(type(row.get(key)) is bool for key in checks) and type(row.get("exit_code")) is int
            passed = (row["exit_code"] == 0 and not row["timed_out"]
                      and row["exact_final_files"] and row["no_unexpected_changes"]
                      and (not row["verification_required"] or bool(row.get("verification_evidence")))) if known else None
            report_path = path.with_suffix(".md")
            by_case.setdefault(row["case"], []).append({
                "success": passed, "model": plan.get("model", "不明"),
                "variant": row.get("variant", "不明"), "agent": plan.get("runtime", "不明"),
                "duration_seconds": row.get("duration_seconds"), "artifacts": row.get("directory"),
                "report": report_path if report_path.is_file() else path,
            })
    return by_case



class EvidenceSnapshot:
    def __init__(self, root, cases, results, catalog, locations):
        self.root, self.cases, self.results = root, cases, results
        self.catalog, self.locations = catalog, locations
        self.saved_reports = load_saved_reports(root)
        self.references = load_reference_runs(root, self.saved_reports)
        self.reference_directories = {
            path.parent for path, data in self.saved_reports
            if isinstance(data.get("plan"), dict)
            and data["plan"].get("mode") == "screen" and data["plan"].get("runtime")
        }
        self.comparisons = {}
        for result in results:
            case = result.get("case")
            if isinstance(case, str):
                self.comparisons.setdefault(case, []).append(result)
        self.history = {
            case: [dict(row, kind="comparison") for row in self.comparisons.get(case, [])]
                  + [dict(row, kind="reference") for row in self.references.get(case, [])]
            for case in set(self.comparisons) | set(self.references)
        }
        self.recorded_cases = {case for case, rows in self.history.items() if rows}
        self.case_ids = sorted(set(cases) | self.recorded_cases,
                               key=lambda case: (case not in self.recorded_cases, case))
        self.by_skill = {}
        self.case_skills = {}
        for case in self.case_ids:
            rows = self.comparisons.get(case, [])
            skill = cases.get(case, {}).get("skill") or (rows[0].get("skill") if rows else None) or "?"
            self.case_skills[case] = skill
            self.by_skill.setdefault(skill, []).append(case)

    def coverage(self, skill):
        cases = self.by_skill.get(skill, [])
        return sum(case in self.recorded_cases for case in cases), len(cases)

    def coverage_label(self, skill):
        recorded, total = self.coverage(skill)
        return f"実行記録あり {recorded} / {total}ケース"


def result_counts(items):
    """Unknown/ungraded values never count as failures or successes."""
    return {
        "passed": sum(item.get("success") is True for item in items),
        "failed": sum(item.get("success") is False for item in items),
        "pending": sum(type(item.get("success")) is not bool for item in items),
    }
