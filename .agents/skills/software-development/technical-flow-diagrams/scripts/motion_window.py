"""Generate SMIL motion/visibility attributes from a window in a common cycle."""
import argparse
import json
import math


def window(cycle, start, end):
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
           for v in (cycle, start, end)) or not 0 <= start < end <= cycle:
        raise ValueError('require finite seconds: 0 <= start < end <= cycle')
    motion = sorted({0: 0, start / cycle: 0, end / cycle: 1, 1: 1}.items())
    opacity = sorted({0: 0, start / cycle: 1, end / cycle: 0, 1: 0}.items())
    common = {'begin': '0s', 'dur': f'{cycle:g}s', 'repeatCount': 'indefinite'}
    def encode(values):
        return ';'.join(f'{v:.15g}' for v in values)
    return {
        'motion': {**common, 'calcMode': 'linear',
                   'keyTimes': encode(t for t, _ in motion),
                   'keyPoints': encode(p for _, p in motion)},
        'opacity': {**common, 'attributeName': 'opacity', 'calcMode': 'discrete',
                    'keyTimes': encode(t for t, _ in opacity),
                    'values': encode(v for _, v in opacity)},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cycle', 'start', 'end'):
        parser.add_argument(name, type=float)
    args = parser.parse_args()
    try:
        print(json.dumps(window(args.cycle, args.start, args.end), indent=2))
    except ValueError as error:
        parser.error(str(error))
