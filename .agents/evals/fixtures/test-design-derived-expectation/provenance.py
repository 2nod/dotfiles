import math


def validate(record):
    if record["metric"] != "official_margin_delta":
        return False
    student = float(record["student_margin"])
    teacher = float(record["teacher_margin"])
    delta = float(record["delta"])
    return math.isfinite(delta) and delta == teacher - student
