"""iperf3 -J output parser.

iperf3 in JSON mode (`-J`) returns a single payload at the end of the run with
sender + receiver summaries. We extract throughput in bits/s and bytes, the
duration, and (for retransmits-aware tests over TCP) retransmit counts.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from typing import Any

ProcessRunner = Callable[[Sequence[str]], str]


def _summarize_endpoint(endpoint: dict[str, Any] | None) -> dict[str, Any] | None:
    if endpoint is None:
        return None
    sum_ = endpoint.get("sum") or {}
    return {
        "bits_per_second": sum_.get("bits_per_second"),
        "bytes": sum_.get("bytes"),
        "seconds": sum_.get("seconds"),
        "retransmits": sum_.get("retransmits"),
    }


def parse_iperf3_json(stdout: str) -> dict[str, Any]:
    payload = json.loads(stdout)
    end = payload.get("end") or {}
    return {
        "iperf_version": payload.get("start", {}).get("version"),
        "protocol": (payload.get("start", {}).get("test_start") or {}).get("protocol"),
        "sender": _summarize_endpoint({"sum": end.get("sum_sent")}),
        "receiver": _summarize_endpoint({"sum": end.get("sum_received")}),
        "cpu_utilization": end.get("cpu_utilization_percent"),
    }


def _default_runner(command: Sequence[str]) -> str:
    return subprocess.check_output(list(command), text=True)


def run_iperf3_client(
    *,
    target: str,
    duration: int = 30,
    parallel: int = 1,
    udp: bool = False,
    extra_args: Sequence[str] = (),
    runner: ProcessRunner = _default_runner,
) -> dict[str, Any]:
    command: list[str] = ["iperf3", "-J", "-c", target, "-t", str(duration), "-P", str(parallel)]
    if udp:
        command.append("-u")
    command.extend(extra_args)
    return parse_iperf3_json(runner(command))
