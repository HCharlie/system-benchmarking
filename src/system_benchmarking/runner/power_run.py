"""powermetrics time-series runner."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from system_benchmarking.adapters.powermetrics import run_powermetrics
from system_benchmarking.runner.result_writer import utc_now, write_result

DEFAULT_RESULTS_DIR = Path("results/raw")


def run_powermetrics_benchmark(
    *,
    samples: int = 60,
    interval_ms: int = 1000,
    sudo: bool = True,
    device_manifest_path: Path,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    now: Callable[[], datetime] = utc_now,
    runner: Callable[..., Any] | None = None,
) -> Path:
    started = now()
    series = (
        run_powermetrics(samples=samples, interval_ms=interval_ms, sudo=sudo, runner=runner)
        if runner
        else run_powermetrics(samples=samples, interval_ms=interval_ms, sudo=sudo)
    )
    ended = now()
    return write_result(
        family="system",
        benchmark_name="powermetrics",
        benchmark_version="0",
        metrics={"samples": series, "n": len(series)},
        params={"samples": samples, "interval_ms": interval_ms, "sudo": sudo},
        started_at=started,
        ended_at=ended,
        device_manifest_path=device_manifest_path,
        results_dir=results_dir,
    )
