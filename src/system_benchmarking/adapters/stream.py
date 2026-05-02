"""STREAM benchmark output parser.

STREAM prints a best-of-NTIMES rate per kernel (Copy/Scale/Add/Triad) in MB/s
where MB = 10^6 bytes (decimal). The parser turns one binary invocation into
one structured sample per kernel. Higher-level callers run the binary multiple
times to build a distribution (median, p99, stddev) for each kernel.
"""

from __future__ import annotations

import re
import statistics
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

KERNELS: tuple[str, ...] = ("copy", "scale", "add", "triad")

_LINE_PATTERN = re.compile(
    r"^(?P<name>Copy|Scale|Add|Triad):\s+"
    r"(?P<rate>[\d.]+)\s+"
    r"(?P<avg>[\d.]+)\s+"
    r"(?P<min>[\d.]+)\s+"
    r"(?P<max>[\d.]+)\s*$",
    re.MULTILINE,
)

ProcessRunner = Callable[[Sequence[str]], str]


@dataclass(frozen=True)
class StreamSample:
    """One invocation's parsed result for a single kernel."""

    kernel: str
    rate_mb_s: float
    avg_time_s: float
    min_time_s: float
    max_time_s: float

    @property
    def rate_gb_s(self) -> float:
        return self.rate_mb_s / 1000.0


@dataclass(frozen=True)
class KernelDistribution:
    kernel: str
    samples_gb_s: list[float]

    @property
    def median(self) -> float:
        return statistics.median(self.samples_gb_s)

    @property
    def stddev(self) -> float:
        if len(self.samples_gb_s) < 2:
            return 0.0
        return statistics.stdev(self.samples_gb_s)

    @property
    def minimum(self) -> float:
        return min(self.samples_gb_s)

    @property
    def maximum(self) -> float:
        return max(self.samples_gb_s)

    @property
    def p99(self) -> float:
        ordered = sorted(self.samples_gb_s)
        if not ordered:
            return 0.0
        index = max(0, int(round(0.99 * (len(ordered) - 1))))
        return ordered[index]

    def to_dict(self) -> dict[str, object]:
        return {
            "samples_gbps": self.samples_gb_s,
            "median_gbps": self.median,
            "stddev_gbps": self.stddev,
            "min_gbps": self.minimum,
            "max_gbps": self.maximum,
            "p99_gbps": self.p99,
            "n": len(self.samples_gb_s),
        }


def parse_stream_output(stdout: str) -> dict[str, StreamSample]:
    """Parse STREAM stdout into one StreamSample per kernel.

    Raises ValueError if any of Copy/Scale/Add/Triad rows are missing —
    the binary almost always prints all four in lockstep, so a missing row
    indicates a corrupt run worth surfacing rather than silently skipping.
    """
    found: dict[str, StreamSample] = {}
    for match in _LINE_PATTERN.finditer(stdout):
        kernel = match.group("name").lower()
        found[kernel] = StreamSample(
            kernel=kernel,
            rate_mb_s=float(match.group("rate")),
            avg_time_s=float(match.group("avg")),
            min_time_s=float(match.group("min")),
            max_time_s=float(match.group("max")),
        )
    missing = [k for k in KERNELS if k not in found]
    if missing:
        raise ValueError(f"STREAM output missing kernels: {missing!r}\n--- stdout ---\n{stdout}")
    return found


def _default_runner(command: Sequence[str]) -> str:
    return subprocess.check_output(list(command), text=True)


def run_stream(binary: Path, iterations: int, runner: ProcessRunner = _default_runner) -> dict[str, KernelDistribution]:
    """Run the STREAM binary `iterations` times, returning one distribution per kernel.

    The binary internally aggregates NTIMES inner iterations into a single
    best-rate sample. Outer iterations capture run-to-run variance from
    scheduler, thermal, and power state — that variance is what callers
    usually care about on laptops.
    """
    if iterations < 1:
        raise ValueError("iterations must be >= 1")

    accumulator: dict[str, list[float]] = {kernel: [] for kernel in KERNELS}
    for _ in range(iterations):
        stdout = runner([str(binary)])
        parsed = parse_stream_output(stdout)
        for kernel, sample in parsed.items():
            accumulator[kernel].append(sample.rate_gb_s)

    return {
        kernel: KernelDistribution(kernel=kernel, samples_gb_s=samples)
        for kernel, samples in accumulator.items()
    }
