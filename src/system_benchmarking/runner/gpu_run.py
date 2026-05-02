"""GPU benchmark runner (currently: Metal capability probe)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from system_benchmarking.adapters.metal_probe import probe_metal
from system_benchmarking.runner.result_writer import utc_now, write_result

DEFAULT_RESULTS_DIR = Path("results/raw")


def run_metal_probe_benchmark(
    *,
    device_manifest_path: Path,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    now: Callable[[], datetime] = utc_now,
    runner: Callable[..., Any] | None = None,
) -> Path:
    started = now()
    metrics = probe_metal(runner=runner) if runner else probe_metal()
    ended = now()
    return write_result(
        family="gpu",
        benchmark_name="metal_capability",
        benchmark_version="0.1",
        metrics=metrics,
        params={},
        started_at=started,
        ended_at=ended,
        device_manifest_path=device_manifest_path,
        results_dir=results_dir,
    )
