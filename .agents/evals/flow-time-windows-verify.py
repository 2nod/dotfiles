"""Interpret output SMIL attributes; no generated code is executed."""
import json
import math
from pathlib import Path
import sys


def sample(attrs, seconds, cycle, values_key):
    assert attrs['begin'] == '0s' and float(attrs['dur'][:-1]) == cycle
    assert attrs['dur'].endswith('s') and attrs['repeatCount'] == 'indefinite'
    times = list(map(float, attrs['keyTimes'].split(';')))
    values = list(map(float, attrs[values_key].split(';')))
    assert len(times) == len(values) >= 2
    assert times[0] == 0 and times[-1] == 1
    assert all(math.isfinite(x) for x in times + values)
    assert all(a < b for a, b in zip(times, times[1:]))
    time = seconds / cycle
    if values_key == 'values':
        assert attrs['calcMode'] == 'discrete'
        return values[max(i for i, t in enumerate(times) if t <= time)]
    assert attrs['calcMode'] == 'linear'
    for i in range(1, len(times)):
        if time <= times[i]:
            return values[i-1] + (values[i]-values[i-1]) * (time-times[i-1]) / (times[i]-times[i-1])
    return values[-1]


def verify(workspace, original):
    assert (workspace/'input.json').read_bytes() == (original/'input.json').read_bytes()
    source = json.loads((workspace/'input.json').read_text())
    frames = json.loads((workspace/'frames.json').read_text())
    assert frames.keys() == source['windows'].keys()
    cycle = source['cycle']
    for name, (start, end) in source['windows'].items():
        # Sample start/end, midpoints, queue gap, and both sides of boundaries.
        probes = [cycle*i/100 for i in range(100)] + [start, end, (start+end)/2]
        for t in probes:
            expected = min(1, max(0, (t-start)/(end-start)))
            assert abs(sample(frames[name]['motion'], t, cycle, 'keyPoints')-expected) < 1e-8
            assert sample(frames[name]['opacity'], t, cycle, 'values') == int(start <= t < end)


if __name__ == '__main__':
    try:
        verify(Path(sys.argv[1]), Path(sys.argv[2]))
    except (AssertionError, OSError, ValueError, KeyError, TypeError, IndexError):
        raise SystemExit(1)
