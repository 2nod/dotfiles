from copy import deepcopy
from review_session import ReviewSession

originals = [
    {"id": "source-a", "kind": "original", "pixels": "circle", "meta": {"bounds": [2, 3, 8, 9], "scale": 2}},
    {"id": "source-b", "kind": "original", "pixels": "triangle", "meta": {"bounds": [5, 7, 9, 11], "scale": 3}},
]
references = [
    {"id": "reference-a", "kind": "reference", "pixels": "square", "meta": {"parent": "source-a", "bounds": [2, 3, 8, 9]}},
    {"id": "reference-b", "kind": "reference", "pixels": "star", "meta": {"parent": "source-b", "bounds": [5, 7, 9, 11]}},
]
unchanged = deepcopy((originals, references))
session = ReviewSession(originals, references)
assert session.begin() == {"images": originals, "reference_text": None}, "Reference pixels leaked before source observations"
for image in originals:
    assert session.inspect(image["id"]) == image
for image in references:
    try:
        session.inspect(image["id"])
    except ValueError:
        pass
    else:
        raise AssertionError("Inspection bypassed the observation boundary")
try:
    session.record_observations({"source-a": "circle"})
except ValueError:
    pass
else:
    raise AssertionError("Incomplete observations were accepted")
try:
    session.inspect("reference-a")
except ValueError:
    pass
else:
    raise AssertionError("Rejected observations unlocked reference pixels")
packet = session.record_observations({"source-a": "circle", "source-b": "triangle"})
assert packet == {"images": references, "reference_text": "retained label"}
for image in originals + references:
    assert session.inspect(image["id"]) == image, "Pixels or metadata changed after unlock"
assert (originals, references) == unchanged
print("Public image boundary and metadata preservation passed")
