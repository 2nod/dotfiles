import hashlib
import json
import random


def _draw(rng, rows, columns):
    return [[rng.gauss(0.0, 0.01) for _ in range(columns)] for _ in range(rows)]


def initialize(seed, extended=False):
    rng = random.Random(seed)
    actor = _draw(rng, 2, 6 if extended else 4)
    critic = [rng.gauss(0.0, 0.01) for _ in range(2)]
    return actor, critic


def fingerprint(model):
    actor, critic = model
    return hashlib.sha256(json.dumps([actor, critic]).encode()).hexdigest()
