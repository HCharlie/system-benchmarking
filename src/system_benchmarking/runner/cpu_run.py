"""CPU benchmark runners (sysbench, stress-ng, native scalar)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from system_benchmarking.adapters.scalar_native import run_scalar
from system_benchmarking.adapters.stress_ng import run_stress_ng_cpu
from system_benchmarking.adapters.sysbench import run_sysbench_cpu
from system_benchmarking.runner.result_writer import utc_now, write_result

DEFAULT_RESULTS_DIR = Path("results/raw")
DEFAULT_SCALAR_BINARY = Path(".build/scalar/scalar")


def run_sysbench_benchmark(
    *,
    threads: int,
    time_seconds: int = 30,
    cpu_max_prime: int = 20000,
    iterations: int = 5,
    device_manifest_path: Path,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    now: Callable[[], datetime] = utc_now,
    runner: Callable[..., Any] | None = None,
) -> Path:
    started = now()
    payload = run_sysbench_cpu(
        threads=threads,
        time_seconds=time_seconds,
        cpu_max_prime=cpu_max_prime,
        iterations=iterations,
        runner=runner,
    ) if runner else run_sysbench_cpu(
        threads=threads,
        time_seconds=time_seconds,
        cpu_max_prime=cpu_max_prime,
        iterations=iterations,
    )
    ended = now()
    return write_result(
        family="cpu",
        benchmark_name="sysbench_cpu",
        benchmark_version="1.0",
        metrics={"events_per_second": payload["events_per_second"]},
        params=payload["params"] | {"iterations": iterations},
        started_at=started,
        ended_at=ended,
        device_manifest_path=device_manifest_path,
        results_dir=results_dir,
    )


def run_stress_ng_benchmark(
    *,
    workers: int,
    seconds: int = 30,
    method: str = "all",
    iterations: int = 3,
    device_manifest_path: Path,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    now: Callable[[], datetime] = utc_now,
    runner: Callable[..., Any] | None = None,
) -> Path:
    started = now()
    payload = run_stress_ng_cpu(
        workers=workers,
        seconds=seconds,
        method=method,
        iterations=iterations,
        runner=runner,
    ) if runner else run_stress_ng_cpu(
        workers=workers,
        seconds=seconds,
        method=method,
        iterations=iterations,
    )
    ended = now()
    return write_result(
        family="cpu",
        benchmark_name="stress_ng_cpu",
        benchmark_version="0.18",
        metrics={"bogo_ops_per_second": payload["bogo_ops_per_second"]},
        params=payload["params"] | {"iterations": iterations},
        started_at=started,
        ended_at=ended,
        device_manifest_path=device_manifest_path,
        results_dir=results_dir,
    )


def run_scalar_benchmark(
    *,
    binary: Path = DEFAULT_SCALAR_BINARY,
    iterations: int = 5,
    inner_iters: int = 1_000_000_000,
    device_manifest_path: Path,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    now: Callable[[], datetime] = utc_now,
    runner: Callable[..., Any] | None = None,
) -> Path:
    if not binary.exists():
        raise FileNotFoundError(
            f"Scalar binary not found at {binary}. Build with scripts/build-scalar.sh"
        )
    started = now()
    metrics = (
        run_scalar(binary, iterations=iterations, inner_iters=inner_iters, runner=runner)
        if runner
        else run_scalar(binary, iterations=iterations, inner_iters=inner_iters)
    )
    ended = now()
    return write_result(
        family="cpu",
        benchmark_name="scalar_native",
        benchmark_version="0.1",
        metrics=metrics,
        params={"iterations": iterations, "inner_iters": inner_iters, "binary": str(binary)},
        started_at=started,
        ended_at=ended,
        device_manifest_path=device_manifest_path,
        results_dir=results_dir,
    )
