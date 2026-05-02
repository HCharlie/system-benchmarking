"""Common helpers for writing raw JSON benchmark results.

Each benchmark runner builds its own metrics dict, calls into here for the
shared result-envelope (schema_version, run_id, device ref, env capture) plus
the file-naming convention under results/raw/<vendor>/<slug>/.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESULT_SCHEMA_VERSION = "1"


def detect_low_power_mode() -> bool | None:
    try:
        output = subprocess.check_output(["pmset", "-g"], text=True, timeout=2)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    for line in output.splitlines():
        if "lowpowermode" in line:
            return line.strip().endswith("1")
    return None


def detect_ac_power() -> bool | None:
    try:
        output = subprocess.check_output(["pmset", "-g", "batt"], text=True, timeout=2)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    return "AC Power" in output


def read_loadavg() -> tuple[float, float, float] | None:
    try:
        return os.getloadavg()
    except OSError:
        return None


def capture_environment() -> dict[str, Any]:
    return {
        "ac_power": detect_ac_power(),
        "low_power_mode": detect_low_power_mode(),
        "loadavg_1_5_15": read_loadavg(),
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
    }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def write_result(
    *,
    family: str,
    benchmark_name: str,
    benchmark_version: str,
    metrics: dict[str, Any],
    params: dict[str, Any],
    started_at: datetime,
    ended_at: datetime,
    device_manifest_path: Path,
    results_dir: Path,
    environment: dict[str, Any] | None = None,
) -> Path:
    """Build the canonical raw-result envelope and write to disk."""
    if not device_manifest_path.exists():
        raise FileNotFoundError(
            f"Device manifest not found at {device_manifest_path}. "
            f"Run `system-benchmark capture-device` first."
        )

    manifest = json.loads(device_manifest_path.read_text())

    payload: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "run_id": str(uuid.uuid4()),
        "benchmark": {
            "family": family,
            "name": benchmark_name,
            "version": benchmark_version,
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
        "params": params,
        "metrics": metrics,
        "environment": environment if environment is not None else capture_environment(),
    }

    vendor = manifest.get("vendor", "unknown")
    slug = manifest.get("slug", "unknown")
    out_dir = results_dir / vendor / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp_slug = started_at.strftime("%Y-%m-%dT%H-%M-%SZ")
    out_path = out_dir / f"{timestamp_slug}-{benchmark_name}.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return out_path
