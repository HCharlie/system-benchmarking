"""STREAM benchmark runner.

Glues the parser/adapter to a device manifest, captures environment context,
and writes a versioned raw JSON result under results/raw/<vendor>/<slug>/.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from system_benchmarking.adapters.stream import KernelDistribution, run_stream

RESULT_SCHEMA_VERSION = "1"
DEFAULT_RESULTS_DIR = Path("results/raw")
DEFAULT_BINARY = Path(".build/stream/stream")


def _read_text(path: Path) -> str:
    return path.read_text()


def _detect_low_power_mode() -> bool | None:
    """Best-effort macOS Low Power Mode probe.

    Returns None when the probe cannot run (e.g. on Linux). The signal is
    advisory — it does not affect the benchmark itself, only the recorded
    environment for later interpretation.
    """
    try:
        output = subprocess.check_output(["pmset", "-g"], text=True, timeout=2)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    for line in output.splitlines():
        if "lowpowermode" in line:
            return line.strip().endswith("1")
    return None


def _detect_ac_power() -> bool | None:
    try:
        output = subprocess.check_output(["pmset", "-g", "batt"], text=True, timeout=2)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    return "AC Power" in output


def _read_loadavg() -> tuple[float, float, float] | None:
    try:
        one, five, fifteen = os.getloadavg()
    except OSError:
        return None
    return (one, five, fifteen)


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
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    runner: Callable[..., Any] | None = None,
) -> Path:
    """Run STREAM and write a raw JSON result. Returns path to the file written."""
    if not binary.exists():
        raise FileNotFoundError(
            f"STREAM binary not found at {binary}. Build it first with scripts/build-stream.sh"
        )
    if not device_manifest_path.exists():
        raise FileNotFoundError(
            f"Device manifest not found at {device_manifest_path}. "
            f"Run `system-benchmark capture-device` first."
        )

    manifest = json.loads(_read_text(device_manifest_path))
    started_at = now()
    distributions = run_stream(binary, iterations=iterations, runner=runner) if runner else run_stream(binary, iterations=iterations)
    ended_at = now()

    payload: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "run_id": str(uuid.uuid4()),
        "benchmark": {
            "family": "memory",
            "name": "stream",
            "version": binary_version,
        },
        "device_ref": str(device_manifest_path),
        "device_summary": {
            "vendor": manifest.get("vendor"),
            "slug": manifest.get("slug"),
            "chip": manifest.get("chip"),
            "memory_bytes": manifest.get("memory_bytes"),
        },
        "started_at": started_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ended_at": ended_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "params": {
            "iterations": iterations,
            "threads": threads,
            "array_size_doubles": array_size,
            "binary": str(binary),
        },
        "metrics": {
            kernel: _kernel_dist_to_dict(dist) for kernel, dist in distributions.items()
        },
        "environment": {
            "ac_power": _detect_ac_power(),
            "low_power_mode": _detect_low_power_mode(),
            "loadavg_1_5_15": _read_loadavg(),
            "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
        },
    }

    vendor = manifest.get("vendor", "unknown")
    slug = manifest.get("slug", "unknown")
    out_dir = results_dir / vendor / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp_slug = started_at.strftime("%Y-%m-%dT%H-%M-%SZ")
    out_path = out_dir / f"{timestamp_slug}-stream.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return out_path
