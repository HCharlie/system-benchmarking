"""tinymembench output parser.

tinymembench prints multiple sections. We extract the "memory copy/fill"
bandwidth table and the "memory latency" table separately so callers can
plot each on its own axis. Format is brittle — pin to a known version when
publishing numbers.
"""

from __future__ import annotations

import re
import statistics
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass

ProcessRunner = Callable[[Sequence[str]], str]

_BANDWIDTH_LINE = re.compile(r"^\s*(?P<name>[A-Za-z0-9 _\-/(),]+):\s+(?P<rate>[\d.]+)\s*MB/s", re.MULTILINE)
_LATENCY_LINE = re.compile(
    r"^\s*(?P<size>\d+)\s*(?P<unit>kB|MB)\s*:\s*(?P<latency>[\d.]+)\s*ns",
    re.MULTILINE,
)


@dataclass(frozen=True)
class TinymembenchBandwidth:
    name: str
    mb_per_second: float


@dataclass(frozen=True)
class TinymembenchLatencyPoint:
    bytes: int
    nanoseconds: float


def parse_tinymembench(stdout: str) -> dict[str, list]:
    bandwidth: list[TinymembenchBandwidth] = []
    seen: set[str] = set()
    for match in _BANDWIDTH_LINE.finditer(stdout):
        name = match.group("name").strip()
        if name in seen:
            continue
        seen.add(name)
        bandwidth.append(TinymembenchBandwidth(name=name, mb_per_second=float(match.group("rate"))))

    latency: list[TinymembenchLatencyPoint] = []
    for match in _LATENCY_LINE.finditer(stdout):
        size = int(match.group("size"))
        size_bytes = size * (1024 if match.group("unit") == "kB" else 1024 * 1024)
        latency.append(TinymembenchLatencyPoint(bytes=size_bytes, nanoseconds=float(match.group("latency"))))

    if not bandwidth and not latency:
        raise ValueError("tinymembench output had no bandwidth or latency rows")
    return {"bandwidth": bandwidth, "latency": latency}


def _default_runner(command: Sequence[str]) -> str:
    return subprocess.check_output(list(command), text=True)


def run_tinymembench(binary, *, iterations: int = 1, runner: ProcessRunner = _default_runner) -> dict[str, object]:
    """Run tinymembench, return aggregated bandwidth medians + latency curve.

    The latency curve is taken from the last invocation since it covers the
    full hierarchy in a single run; bandwidth medians are aggregated across
    invocations to suppress jitter.
    """
    bandwidth_acc: dict[str, list[float]] = {}
    last_latency: list[TinymembenchLatencyPoint] = []
    for _ in range(iterations):
        parsed = parse_tinymembench(runner([str(binary)]))
        for entry in parsed["bandwidth"]:
            bandwidth_acc.setdefault(entry.name, []).append(entry.mb_per_second)
        last_latency = parsed["latency"]

    bandwidth = {
        name: {
            "samples_mbps": rates,
            "median_mbps": statistics.median(rates),
            "stddev_mbps": statistics.stdev(rates) if len(rates) > 1 else 0.0,
            "n": len(rates),
        }
        for name, rates in bandwidth_acc.items()
    }
    latency_points = [{"bytes": p.bytes, "nanoseconds": p.nanoseconds} for p in last_latency]
    return {"bandwidth": bandwidth, "latency_curve": latency_points}
