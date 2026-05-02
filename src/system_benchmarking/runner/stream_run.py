"""STREAM benchmark runner."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from system_benchmarking.adapters.stream import KernelDistribution, run_stream
from system_benchmarking.runner.result_writer import (
    RESULT_SCHEMA_VERSION,  # re-export for tests
    utc_now,
    write_result,
)

DEFAULT_RESULTS_DIR = Path("results/raw")
DEFAULT_BINARY = Path(".build/stream/stream")

__all__ = ["DEFAULT_BINARY", "DEFAULT_RESULTS_DIR", "RESULT_SCHEMA_VERSION", "run_stream_benchmark"]


def _kernel_dist_to_dict(dist: KernelDistribution) -> dict[str, Any]:
    return dist.to_dict()


def run_stream_benchmark(
    *,
    binary: Path = DEFAULT_BINARY,
    iterations: int = 10,
    device_manifest_path: Path,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    threads: int | None = None,
    array_size: int | None = None,
    binary_version: str = "5.10",
    now: Callable[[], datetime] = utc_now,
    runner: Callable[..., Any] | None = None,
) -> Path:
    """Run STREAM and write a raw JSON result. Returns path to the file written."""
    if not binary.exists():
        raise FileNotFoundError(
            f"STREAM binary not found at {binary}. Build it first with scripts/build-stream.sh"
        )

    started_at = now()
    distributions = (
        run_stream(binary, iterations=iterations, runner=runner)
        if runner
        else run_stream(binary, iterations=iterations)
    )
    ended_at = now()

    metrics = {kernel: _kernel_dist_to_dict(dist) for kernel, dist in distributions.items()}

    return write_result(
        family="memory",
        benchmark_name="stream",
        benchmark_version=binary_version,
        metrics=metrics,
        params={
            "iterations": iterations,
            "threads": threads,
            "array_size_doubles": array_size,
            "binary": str(binary),
        },
        started_at=started_at,
        ended_at=ended_at,
        device_manifest_path=device_manifest_path,
        results_dir=results_dir,
    )
