"""fio JSON output parser.

fio's `--output-format=json+` is the canonical machine-readable form. We
extract the headline metrics per job: bandwidth (KiB/s), IOPS, and a few
latency percentiles. Latency keys live under `clat_ns.percentile`. The
parser is conservative: missing fields default to None rather than raising,
so future fio versions don't break entire result writes.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from typing import Any

ProcessRunner = Callable[[Sequence[str]], str]

_PERCENTILES_OF_INTEREST = ("50.000000", "95.000000", "99.000000", "99.900000", "99.990000")


def _summarize_direction(stats: dict[str, Any]) -> dict[str, Any] | None:
    """Pick out the bits we care about from a {read|write} sub-object."""
    iops = stats.get("iops")
    bw_kibps = stats.get("bw")
    if iops is None and bw_kibps is None:
        return None
    clat = stats.get("clat_ns") or {}
    percentile = clat.get("percentile") or {}
    pct_label = {
        "50.000000": "p50_ns",
        "95.000000": "p95_ns",
        "99.000000": "p99_ns",
        "99.900000": "p99_9_ns",
        "99.990000": "p99_99_ns",
    }
    selected_percentiles = {
        pct_label[key]: value for key, value in percentile.items() if key in pct_label
    }
    return {
        "iops": iops,
        "bw_kib_s": bw_kibps,
        "bw_mb_s": (bw_kibps * 1024 / 1_000_000) if bw_kibps else None,
        "clat_min_ns": clat.get("min"),
        "clat_max_ns": clat.get("max"),
        "clat_mean_ns": clat.get("mean"),
        "clat_stddev_ns": clat.get("stddev"),
        **selected_percentiles,
    }


def parse_fio_json(stdout: str) -> dict[str, Any]:
    payload = json.loads(stdout)
    jobs_raw = payload.get("jobs") or []
    jobs: list[dict[str, Any]] = []
    for job in jobs_raw:
        jobs.append(
            {
                "name": job.get("jobname") or job.get("name"),
                "read": _summarize_direction(job.get("read", {})),
                "write": _summarize_direction(job.get("write", {})),
                "trim": _summarize_direction(job.get("trim", {})),
            }
        )
    return {
        "fio_version": payload.get("fio version"),
        "global_options": payload.get("global options", {}),
        "jobs": jobs,
    }


def _default_runner(command: Sequence[str]) -> str:
    return subprocess.check_output(list(command), text=True)


def run_fio(
    *,
    profile_args: Sequence[str],
    runner: ProcessRunner = _default_runner,
) -> dict[str, Any]:
    """Invoke fio with caller-supplied profile args plus json+ output, then parse.

    Profile args are passed through to fio (e.g. ``--rw=randread --bs=4k``). The
    runner injects ``--output-format=json+`` so callers don't need to remember.
    """
    command = ["fio", "--output-format=json+", *profile_args]
    return parse_fio_json(runner(command))
