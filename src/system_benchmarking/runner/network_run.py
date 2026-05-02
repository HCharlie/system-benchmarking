"""Network benchmark runners (iperf3, ping)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from system_benchmarking.adapters.iperf3 import run_iperf3_client
from system_benchmarking.adapters.ping import run_ping
from system_benchmarking.runner.result_writer import utc_now, write_result

DEFAULT_RESULTS_DIR = Path("results/raw")


def run_iperf3_benchmark(
    *,
    target: str,
    duration: int = 30,
    parallel: int = 1,
    udp: bool = False,
    device_manifest_path: Path,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    now: Callable[[], datetime] = utc_now,
    runner: Callable[..., Any] | None = None,
) -> Path:
    started = now()
    payload = (
        run_iperf3_client(target=target, duration=duration, parallel=parallel, udp=udp, runner=runner)
        if runner
        else run_iperf3_client(target=target, duration=duration, parallel=parallel, udp=udp)
    )
    ended = now()
    return write_result(
        family="network",
        benchmark_name="iperf3",
        benchmark_version=str(payload.get("iperf_version", "unknown")),
        metrics={
            "sender": payload.get("sender"),
            "receiver": payload.get("receiver"),
            "cpu_utilization": payload.get("cpu_utilization"),
        },
        params={
            "target": target,
            "duration": duration,
            "parallel": parallel,
            "udp": udp,
            "protocol": payload.get("protocol"),
        },
        started_at=started,
        ended_at=ended,
        device_manifest_path=device_manifest_path,
        results_dir=results_dir,
    )


def run_ping_benchmark(
    *,
    target: str,
    count: int = 100,
    device_manifest_path: Path,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    now: Callable[[], datetime] = utc_now,
    runner: Callable[..., Any] | None = None,
) -> Path:
    started = now()
    payload = run_ping(target=target, count=count, runner=runner) if runner else run_ping(target=target, count=count)
    ended = now()
    return write_result(
        family="network",
        benchmark_name="ping",
        benchmark_version="0",
        metrics=payload,
        params={"target": target, "count": count},
        started_at=started,
        ended_at=ended,
        device_manifest_path=device_manifest_path,
        results_dir=results_dir,
    )
