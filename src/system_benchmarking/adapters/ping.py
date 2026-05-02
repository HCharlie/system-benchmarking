"""macOS / Linux ping output parser.

We aim at the summary block ping prints at the end:
  round-trip min/avg/max/stddev = 1.234/2.345/3.456/0.123 ms (macOS)
  rtt min/avg/max/mdev = 1.234/2.345/3.456/0.123 ms          (Linux)
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable, Sequence
from typing import Any

ProcessRunner = Callable[[Sequence[str]], str]

_SUMMARY = re.compile(
    r"(?:round-trip|rtt)\s+(?:min/avg/max/stddev|min/avg/max/mdev)"
    r"\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)\s*ms",
)
_PACKETS = re.compile(r"(\d+)\s+packets transmitted,\s+(\d+)\s+(?:packets )?received")


def parse_ping_summary(stdout: str) -> dict[str, Any]:
    summary = _SUMMARY.search(stdout)
    if not summary:
        raise ValueError("ping output missing summary line")
    sent_recv = _PACKETS.search(stdout)
    transmitted = int(sent_recv.group(1)) if sent_recv else None
    received = int(sent_recv.group(2)) if sent_recv else None
    return {
        "min_ms": float(summary.group(1)),
        "avg_ms": float(summary.group(2)),
        "max_ms": float(summary.group(3)),
        "stddev_ms": float(summary.group(4)),
        "transmitted": transmitted,
        "received": received,
        "loss_pct": (
            100.0 * (transmitted - received) / transmitted
            if transmitted and received is not None
            else None
        ),
    }


def _default_runner(command: Sequence[str]) -> str:
    return subprocess.check_output(list(command), text=True)


def run_ping(
    *,
    target: str,
    count: int = 100,
    runner: ProcessRunner = _default_runner,
) -> dict[str, Any]:
    return parse_ping_summary(runner(["ping", "-c", str(count), target]))
