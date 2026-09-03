from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr
from io import StringIO
import json
import os
import sys
import threading


def engine(job, first_entered, second_entered, first_exited):
    if job == 0:
        with StringIO() as buffer, redirect_stderr(buffer):
            first_entered.set()
            second_entered.wait()
        first_exited.set()
        return job * job
    if job == 1:
        first_entered.wait()
        with StringIO() as buffer, redirect_stderr(buffer):
            second_entered.set()
            first_exited.wait()
        print("engine complete", file=sys.stderr)
        return job * job
    return job * job


def main():
    first_entered = threading.Event()
    second_entered = threading.Event()
    first_exited = threading.Event()
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(lambda job: engine(job, first_entered, second_entered, first_exited), range(4)))
    print(json.dumps({"mode": "threaded", "workers": 4, "values": values, "parent_pid": os.getpid()}))


if __name__ == "__main__":
    main()
