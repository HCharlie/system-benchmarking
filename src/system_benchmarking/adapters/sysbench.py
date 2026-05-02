"""sysbench cpu output parser.

Parses the human-readable output of `sysbench cpu run`. The headline metric is
"events per second", which sysbench computes from a fixed-time CPU-bound
prime-finding loop. Higher is better. The loop exercises integer arithmetic
and branch prediction more than memory bandwidth — pair with STREAM for a
fuller picture.
"""

from __future__ import annotations

import re
import statistics
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass

ProcessRunner = Callable[[Sequence[str]], str]


@dataclass(frozen=True)
class SysbenchSample:
    events_per_second: float
    total_events: int
    total_time_s: float
    threads: int
    cpu_max_prime: int


_EVENTS_PER_SECOND = re.compile(r"events per second:\s+([\d.]+)")
_TOTAL_EVENTS = re.compile(r"total number of events:\s+(\d+)")
_TOTAL_TIME = re.compile(r"total time:\s+([\d.]+)s")
_THREADS = re.compile(r"Number of threads:\s+(\d+)")
_PRIME = re.compile(r"Prime numbers limit:\s+(\d+)")


def _required_match(pattern: re.Pattern[str], text: str, label: str) -> str:
    match = pattern.search(text)
    if not match:
        raise ValueError(f"sysbench output missing field: {label}\n--- stdout ---\n{text}")
    return match.group(1)


def parse_sysbench_cpu(stdout: str) -> SysbenchSample:
    return SysbenchSample(
        events_per_second=float(_required_match(_EVENTS_PER_SECOND, stdout, "events per second")),
        total_events=int(_required_match(_TOTAL_EVENTS, stdout, "total events")),
        total_time_s=float(_required_match(_TOTAL_TIME, stdout, "total time")),
        threads=int(_required_match(_THREADS, stdout, "threads")),
        cpu_max_prime=int(_required_match(_PRIME, stdout, "prime limit")),
    )


def _default_runner(command: Sequence[str]) -> str:
    return subprocess.check_output(list(command), text=True)


def run_sysbench_cpu(
    *,
    threads: int,
    time_seconds: int = 30,
    cpu_max_prime: int = 20000,
    iterations: int = 5,
    runner: ProcessRunner = _default_runner,
) -> dict[str, object]:
    """Run sysbench cpu `iterations` times and aggregate."""
    samples: list[SysbenchSample] = []
    for _ in range(iterations):
        stdout = runner(
            [
                "sysbench",
                "cpu",
                f"--threads={threads}",
                f"--time={time_seconds}",
                f"--cpu-max-prime={cpu_max_prime}",
                "run",
            ]
        )
        samples.append(parse_sysbench_cpu(stdout))

    eps = [s.events_per_second for s in samples]
    return {
        "events_per_second": {
            "samples": eps,
            "median": statistics.median(eps),
            "stddev": statistics.stdev(eps) if len(eps) > 1 else 0.0,
            "min": min(eps),
            "max": max(eps),
            "n": len(eps),
            "unit": "events/s",
        },
        "params": {
            "threads": threads,
            "time_seconds": time_seconds,
            "cpu_max_prime": cpu_max_prime,
        },
    }
