"""Parser for the native scalar CPU microbenchmark.

The binary prints one JSON object per kernel on its own line. We parse them
into structured samples and aggregate across multiple binary invocations.
"""

from __future__ import annotations

import json
import statistics
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

ProcessRunner = Callable[[Sequence[str]], str]


def parse_scalar_output(stdout: str) -> dict[str, dict[str, float]]:
    """Return {kernel_name: {ops_per_second, seconds, ops}} from one invocation."""
    out: dict[str, dict[str, float]] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        kernel = payload.get("kernel")
        if not kernel:
            continue
        out[kernel] = {
            "ops_per_second": float(payload["ops_per_second"]),
            "seconds": float(payload["seconds"]),
            "ops": float(payload["ops"]),
        }
    if not out:
        raise ValueError("scalar binary produced no parseable kernel lines")
    return out


def _default_runner(command: Sequence[str]) -> str:
    return subprocess.check_output(list(command), text=True)


def run_scalar(
    binary: Path,
    *,
    iterations: int,
    inner_iters: int = 1_000_000_000,
    runner: ProcessRunner = _default_runner,
) -> dict[str, dict[str, object]]:
    """Run the scalar binary `iterations` times and aggregate per kernel."""
    if iterations < 1:
        raise ValueError("iterations must be >= 1")

    accumulator: dict[str, list[float]] = {}
    for _ in range(iterations):
        stdout = runner([str(binary), str(inner_iters)])
        parsed = parse_scalar_output(stdout)
        for kernel, sample in parsed.items():
            accumulator.setdefault(kernel, []).append(sample["ops_per_second"])

    return {
        kernel: {
            "samples": rates,
            "median": statistics.median(rates),
            "stddev": statistics.stdev(rates) if len(rates) > 1 else 0.0,
            "min": min(rates),
            "max": max(rates),
            "n": len(rates),
            "unit": "ops/s",
        }
        for kernel, rates in accumulator.items()
    }
