"""Parser for the native pointer-chase memory latency benchmark."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

ProcessRunner = Callable[[Sequence[str]], str]


def parse_pointer_chase(stdout: str) -> list[dict[str, float]]:
    points: list[dict[str, float]] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "bytes" not in payload or "ns_per_access" not in payload:
            continue
        points.append(
            {
                "bytes": int(payload["bytes"]),
                "ns_per_access": float(payload["ns_per_access"]),
                "iterations": int(payload.get("iterations", 0)),
            }
        )
    if not points:
        raise ValueError("pointer_chase binary produced no parseable points")
    return points


def _default_runner(command: Sequence[str]) -> str:
    return subprocess.check_output(list(command), text=True)


def run_pointer_chase(
    binary: Path,
    *,
    iterations: int = 1,
    access_count: int = 40_000_000,
    runner: ProcessRunner = _default_runner,
) -> dict[str, object]:
    """Run pointer_chase. Latency tends to be stable across runs at a given
    working-set size, so a single invocation is usually enough; pass
    ``iterations > 1`` to take a per-size median for additional confidence.
    """
    if iterations < 1:
        raise ValueError("iterations must be >= 1")

    runs: list[list[dict[str, float]]] = []
    for _ in range(iterations):
        runs.append(parse_pointer_chase(runner([str(binary), str(access_count)])))

    sizes = [p["bytes"] for p in runs[0]]
    aggregated: list[dict[str, object]] = []
    for index, size in enumerate(sizes):
        ns_values = [run[index]["ns_per_access"] for run in runs if index < len(run)]
        aggregated.append(
            {
                "bytes": size,
                "ns_per_access_median": sum(sorted(ns_values)[len(ns_values) // 2 : len(ns_values) // 2 + 1]) if ns_values else 0.0,
                "ns_per_access_min": min(ns_values) if ns_values else 0.0,
                "ns_per_access_max": max(ns_values) if ns_values else 0.0,
                "samples_ns": ns_values,
            }
        )
    return {"latency_curve": aggregated, "iterations": iterations, "access_count": access_count}
