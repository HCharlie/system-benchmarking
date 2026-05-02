"""stress-ng output parser.

stress-ng prints metrics on stderr when invoked with `--metrics-brief`. We
target the `cpu` stressor specifically so callers can compare against
sysbench (different methods → different numbers, both useful).
"""

from __future__ import annotations

import re
import statistics
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass

ProcessRunner = Callable[[Sequence[str]], tuple[str, str]]


@dataclass(frozen=True)
class StressNgCpuSample:
    bogo_ops: int
    real_time_s: float
    bogo_ops_per_second_real: float
    method: str
    workers: int


_HEADER = re.compile(r"stressor\s+bogo ops\s+real time", re.IGNORECASE)
_CPU_LINE = re.compile(
    r"\bcpu\s+(\d+)\s+([\d.]+)\s+[\d.]+\s+[\d.]+\s+([\d.]+)\s+([\d.]+)",
)


def parse_stress_ng_cpu(stderr: str, method: str = "all", workers: int = 0) -> StressNgCpuSample:
    if not _HEADER.search(stderr):
        raise ValueError("stress-ng output missing metrics header (use --metrics-brief)")
    match = _CPU_LINE.search(stderr)
    if not match:
        raise ValueError("stress-ng output missing 'cpu' stressor row")
    return StressNgCpuSample(
        bogo_ops=int(match.group(1)),
        real_time_s=float(match.group(2)),
        bogo_ops_per_second_real=float(match.group(3)),
        method=method,
        workers=workers,
    )


def _default_runner(command: Sequence[str]) -> tuple[str, str]:
    process = subprocess.run(command, text=True, capture_output=True, check=True)
    return process.stdout, process.stderr


def run_stress_ng_cpu(
    *,
    workers: int,
    seconds: int = 30,
    method: str = "all",
    iterations: int = 3,
    runner: ProcessRunner = _default_runner,
) -> dict[str, object]:
    samples: list[StressNgCpuSample] = []
    for _ in range(iterations):
        _stdout, stderr = runner(
            [
                "stress-ng",
                "--cpu",
                str(workers),
                "--cpu-method",
                method,
                "--metrics-brief",
                "--timeout",
                f"{seconds}s",
            ]
        )
        samples.append(parse_stress_ng_cpu(stderr, method=method, workers=workers))

    rates = [s.bogo_ops_per_second_real for s in samples]
    return {
        "bogo_ops_per_second": {
            "samples": rates,
            "median": statistics.median(rates),
            "stddev": statistics.stdev(rates) if len(rates) > 1 else 0.0,
            "min": min(rates),
            "max": max(rates),
            "n": len(rates),
            "unit": "bogo-ops/s",
        },
        "params": {"workers": workers, "seconds": seconds, "method": method},
    }
