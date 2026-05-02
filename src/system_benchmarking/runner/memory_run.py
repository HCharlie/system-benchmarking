"""Memory-latency benchmark runners (tinymembench, pointer-chase)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from system_benchmarking.adapters.pointer_chase import run_pointer_chase
from system_benchmarking.adapters.tinymembench import run_tinymembench
from system_benchmarking.runner.result_writer import utc_now, write_result

DEFAULT_RESULTS_DIR = Path("results/raw")
DEFAULT_POINTER_CHASE_BINARY = Path(".build/pointer_chase/pointer_chase")


def run_tinymembench_benchmark(
    *,
    binary: Path,
    iterations: int = 1,
    device_manifest_path: Path,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    now: Callable[[], datetime] = utc_now,
    runner: Callable[..., Any] | None = None,
) -> Path:
    if not binary.exists():
        raise FileNotFoundError(f"tinymembench binary not found at {binary}")
    started = now()
    metrics = run_tinymembench(binary, iterations=iterations, runner=runner) if runner else run_tinymembench(binary, iterations=iterations)
    ended = now()
    return write_result(
        family="memory",
        benchmark_name="tinymembench",
        benchmark_version="0.4.10",
        metrics=metrics,
        params={"iterations": iterations, "binary": str(binary)},
        started_at=started,
        ended_at=ended,
        device_manifest_path=device_manifest_path,
        results_dir=results_dir,
    )


def run_pointer_chase_benchmark(
    *,
    binary: Path = DEFAULT_POINTER_CHASE_BINARY,
    iterations: int = 1,
    access_count: int = 40_000_000,
    device_manifest_path: Path,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    now: Callable[[], datetime] = utc_now,
    runner: Callable[..., Any] | None = None,
) -> Path:
    if not binary.exists():
        raise FileNotFoundError(
            f"pointer_chase binary not found at {binary}. Build with scripts/build-pointer-chase.sh"
        )
    started = now()
    metrics = (
        run_pointer_chase(binary, iterations=iterations, access_count=access_count, runner=runner)
        if runner
        else run_pointer_chase(binary, iterations=iterations, access_count=access_count)
    )
    ended = now()
    return write_result(
        family="memory",
        benchmark_name="pointer_chase",
        benchmark_version="0.1",
        metrics=metrics,
        params={"iterations": iterations, "access_count": access_count, "binary": str(binary)},
        started_at=started,
        ended_at=ended,
        device_manifest_path=device_manifest_path,
        results_dir=results_dir,
    )
