"""Validate the rendered cross-page contract before replacing report files."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Page(HTMLParser):
    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.skills, self.cases = set(), [], {}, {}
        self.sections, self.details = [], []
        self.summary, self.style = None, []
        self.in_style = False
        self.metrics, self.metric = {}, None
        self.history = {}
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            if attrs["id"] in self.ids:
                raise ValueError("duplicate anchor: " + attrs["id"])
            self.ids.add(attrs["id"])
        if "data-history-case" in attrs:
            key = (attrs["data-history-case"], attrs.get("data-history-kind"))
            self.history[key] = self.history.get(key, 0) + 1
        if "data-metric" in attrs:
            self.metric = (attrs["data-metric"], [])
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag == "style":
            self.in_style = True
        if tag == "section":
            self.sections.append(attrs.get("data-source"))
        if tag == "details":
            self.details.append(attrs)
            if "data-evidence" in attrs:
                self.cases[attrs["id"]] = (attrs["data-evidence"], next((d["data-skill"] for d in reversed(self.details) if "data-skill" in d), None), self.sections[-1] if self.sections else None)
        if tag == "summary" and self.details:
            self.summary = (self.details[-1], [])

    def handle_data(self, data):
        if self.metric:
            self.metric[1].append(data)
        if self.in_style:
            self.style.append(data)
        if self.summary:
            self.summary[1].append(data)

    def handle_endtag(self, tag):
        if tag == "strong" and self.metric:
            self.metrics[self.metric[0]] = "".join(self.metric[1])
            self.metric = None
        if tag == "style":
            self.in_style = False
        if tag == "summary" and self.summary:
            attrs, parts = self.summary
            if "data-skill" in attrs:
                skill = attrs["data-skill"]
                if skill in self.skills:
                    raise ValueError("duplicate skill: " + skill)
                self.skills[skill] = (" ".join(parts), self.sections[-1] if self.sections else None)
            self.summary = None
        if tag == "details":
            self.details.pop()
        if tag == "section":
            self.sections.pop()


def validate_pages(pages, evidence, usage_stats=None):
    parsed = {name: Page(content) for name, content in pages.items()}
    if len({"".join(page.style) for page in parsed.values()}) != 1:
        raise ValueError("report pages use different styles")
    for name, page in parsed.items():
        for link in page.links:
            target = urlsplit(link)
            if not target.scheme and (target.path in parsed or (not target.path and target.fragment)):
                destination = target.path or name
                if target.fragment and unquote(target.fragment) not in parsed[destination].ids:
                    raise ValueError("broken report link: " + name + " -> " + link)
    evaluations = parsed["evals.html"]
    if set(evaluations.cases) != set(evidence.case_ids):
        raise ValueError("case inventory does not match evidence")
    for case, (state, skill, source) in evaluations.cases.items():
        expected_skill = evidence.case_skills[case]
        expected_source = evidence.catalog.get(expected_skill, {}).get("source", "unknown")
        if expected_source not in ("authored", "installed"):
            expected_source = "unknown"
        if state != ("recorded" if case in evidence.recorded_cases else "missing") or skill != expected_skill or source != expected_source:
            raise ValueError("case evidence or provenance mismatch: " + case)
    for page in (parsed["report.html"], evaluations):
        for skill, (summary, source) in page.skills.items():
            if evidence.coverage_label(skill) not in summary:
                raise ValueError("skill coverage mismatch: " + skill)
            expected_source = evidence.catalog.get(skill, {}).get("source", "unknown")
            if expected_source not in ("authored", "installed"):
                expected_source = "unknown"
            if source != expected_source:
                raise ValueError("skill provenance mismatch: " + skill)
    if set(evaluations.skills) != set(evidence.by_skill):
        raise ValueError("skill groups do not match case inventory")

    expected_metrics = {"total-cases": str(len(evidence.case_ids)), "recorded-cases": str(len(evidence.recorded_cases)), "missing-cases": str(len(evidence.case_ids) - len(evidence.recorded_cases))}
    if evaluations.metrics != expected_metrics:
        raise ValueError("overview counts do not match case evidence")
    source_root = Path(__file__).resolve().parents[1] / ".agents"
    managed_skills = {skill for skill, profile in evidence.catalog.items() if (source_root / profile["path"]).is_file()}
    if set(parsed["report.html"].skills) != managed_skills:
        raise ValueError("managed skill inventory is incomplete")

    expected_history = {}
    for case, items in evidence.history.items():
        for item in items:
            key = (case, item["kind"])
            expected_history[key] = expected_history.get(key, 0) + 1
    if evaluations.history != expected_history:
        raise ValueError("execution history does not match recorded evidence")

    usage = parsed["usage.html"].metrics
    keys = {"usage-total": "uses", "usage-passed": "verified", "usage-failed": "failed", "usage-unverified": "unverified", "usage-no-end": "ongoing", "usage-legacy": "legacy"}
    if set(usage) != set(keys) or any(not value.isdigit() for value in usage.values()):
        raise ValueError("usage categories are incomplete")
    if int(usage["usage-total"]) != sum(int(value) for key, value in usage.items() if key != "usage-total"):
        raise ValueError("usage total differs from its categories")
    if usage_stats is not None and usage != {key: str(sum(getattr(item, attr) for item in usage_stats.values())) for key, attr in keys.items()}:
        raise ValueError("usage counts do not match usage records")
