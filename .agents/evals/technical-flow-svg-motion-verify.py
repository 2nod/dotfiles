#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import sys


def fail(message: str) -> int:
    print(message)
    return 1


def main() -> int:
    workspace = pathlib.Path(sys.argv[1])
    component = workspace / "FlowDiagram.jsx"
    stylesheet = workspace / "diagram.css"

    try:
        jsx = component.read_text()
        css = stylesheet.read_text()
    except OSError as error:
        print(error)
        return 2

    path_literal = "M 24 96 C 120 32 216 160 312 96"
    if jsx.count(path_literal) != 1:
        return fail("the flow path must have exactly one source")
    if len(re.findall(r"d=\{FLOW_PATH\}", jsx)) != 1:
        return fail("the static wire must use the shared path source")
    if len(re.findall(r"path=\{FLOW_PATH\}", jsx)) != 1:
        return fail("animateMotion must use the shared path source")

    reduced_motion = re.search(
        r"@media \(prefers-reduced-motion: reduce\) \{(.*?)\}", css, re.S
    )
    if not reduced_motion:
        return fail("reduced-motion handling is missing")
    block = reduced_motion.group(1)
    if ".flow-chip" not in block or "display: none" not in block:
        return fail("reduced motion must hide the moving chips only")
    if ".flow-diagram" in block:
        return fail("reduced motion must keep the static diagram visible")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
