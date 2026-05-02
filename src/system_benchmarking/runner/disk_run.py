"""fio disk benchmark runner."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from system_benchmarking.adapters.fio import run_fio
from system_benchmarking.runner.result_writer import utc_now, write_result

DEFAULT_RESULTS_DIR = Path("results/raw")


def run_fio_benchmark(
    *,
    profile: Path,
    extra_args: list[str] | None = None,
    workdir: Path | None = None,
    device_manifest_path: Path,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    now: Callable[[], datetime] = utc_now,
    runner: Callable[..., Any] | None = None,
) -> Path:
    if not profile.exists():
        raise FileNotFoundError(f"fio profile not found at {profile}")

    profile_args = [str(profile)]
    if workdir is not None:
        profile_args += [f"--directory={workdir}"]
    if extra_args:
        profile_args += extra_args

    started = now()
    payload = run_fio(profile_args=profile_args, runner=runner) if runner else run_fio(profile_args=profile_args)
    ended = now()

    return write_result(
        family="disk",
        benchmark_name=f"fio_{profile.stem}",
        benchmark_version=str(payload.get("fio_version", "unknown")),
        metrics={"jobs": payload["jobs"]},
        params={
            "profile": str(profile),
            "extra_args": extra_args or [],
            "workdir": str(workdir) if workdir else None,
            "global_options": payload.get("global_options", {}),
        },
        started_at=started,
        ended_at=ended,
        device_manifest_path=device_manifest_path,
        results_dir=results_dir,
    )
