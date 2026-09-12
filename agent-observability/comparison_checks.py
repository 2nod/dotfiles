"""Shared comparison predicates; no I/O or model calls."""
import math


def comparison_pairs(rows):
    pairs = {}
    for row in rows:
        key = (row.get("case"), row.get("run"))
        pair = pairs.setdefault(key, {})
        if row.get("variant") in pair:
            return []
        pair[row.get("variant")] = row
    return list(pairs.values())


def efficiency_quality_ready(pairs, baseline="treatment", target="candidate"):
    return bool(pairs) and all(
        pair.get(baseline, {}).get("success") is True
        and pair.get(target, {}).get("success") is True
        for pair in pairs
    )


def efficiency_passes(policy, pairs):
    """Require the declared reduction in every pair, never trade quality for cost."""
    if not policy or not efficiency_quality_ready(pairs):
        return False
    metric = policy["metric"]
    for pair in pairs:
        current, candidate = pair.get("treatment", {}), pair.get("candidate", {})
        if current.get("success") is not True or candidate.get("success") is not True:
            return False
        baseline, measured = current.get(metric), candidate.get(metric)
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0
               for v in (baseline, measured)):
            return False
        if baseline <= 0 or measured > baseline * (1 - policy["minimum_reduction"]):
            return False
    return True


