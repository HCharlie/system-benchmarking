"""macOS powermetrics output parser.

powermetrics emits one human-readable block per sample. We extract a small set
of fields per sample so callers get a tractable time series even when the tool
prints dozens of unrelated lines. powermetrics requires sudo — handle that at
the caller, not here.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable, Sequence
from typing import Any

ProcessRunner = Callable[[Sequence[str]], str]

_SAMPLE_DELIMITER = re.compile(r"^\*+ Sampled system activity .*$", re.MULTILINE)

_FIELD_PATTERNS = {
    "package_power_mw": re.compile(r"Combined Power.*?:\s*([\d.]+)\s*mW"),
    "cpu_power_mw": re.compile(r"CPU Power:\s*([\d.]+)\s*mW"),
    "gpu_power_mw": re.compile(r"GPU Power:\s*([\d.]+)\s*mW"),
    "ane_power_mw": re.compile(r"ANE Power:\s*([\d.]+)\s*mW"),
    "cpu_die_temperature_c": re.compile(r"CPU die temperature:\s*([\d.]+)\s*C"),
    "gpu_die_temperature_c": re.compile(r"GPU die temperature:\s*([\d.]+)\s*C"),
    "fan_rpm": re.compile(r"Fan:\s*([\d.]+)\s*rpm"),
}


def _maybe_float(text: str, pattern: re.Pattern[str]) -> float | None:
    match = pattern.search(text)
    return float(match.group(1)) if match else None


def parse_powermetrics(stdout: str) -> list[dict[str, float | None]]:
    """Split a powermetrics dump into per-sample dicts of selected fields."""
    blocks = _SAMPLE_DELIMITER.split(stdout)
    samples: list[dict[str, float | None]] = []
    for block in blocks[1:]:  # first block is preamble
        sample = {name: _maybe_float(block, pattern) for name, pattern in _FIELD_PATTERNS.items()}
        if any(value is not None for value in sample.values()):
            samples.append(sample)
    return samples


def _default_runner(command: Sequence[str]) -> str:
    return subprocess.check_output(list(command), text=True)


def run_powermetrics(
    *,
    samples: int = 60,
    interval_ms: int = 1000,
    samplers: Sequence[str] = ("cpu_power", "gpu_power", "thermal"),
    sudo: bool = True,
    runner: ProcessRunner = _default_runner,
) -> list[dict[str, float | None]]:
    """Sample powermetrics for `samples * interval_ms` total milliseconds.

    Requires sudo on real systems. ``sudo=False`` is mostly useful for tests
    where the runner is a fake.
    """
    command: list[str] = []
    if sudo:
        command.append("sudo")
    command += [
        "powermetrics",
        "--samplers",
        ",".join(samplers),
        "-i",
        str(interval_ms),
        "-n",
        str(samples),
    ]
    return parse_powermetrics(runner(command))
