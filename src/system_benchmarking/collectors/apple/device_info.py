"""Apple device metadata collection."""

from __future__ import annotations

import subprocess
from collections.abc import Callable

from system_benchmarking.results import DeviceInfo


def _run_command(command: tuple[str, ...]) -> str:
    return subprocess.check_output(command, text=True).strip()


def _bytes_to_gib(value: str) -> int:
    return round(int(value.strip()) / (1024**3))


def collect_apple_device_info(
    run_command: Callable[[tuple[str, ...]], str] = _run_command,
    model_name: str = "Unknown Mac",
) -> DeviceInfo:
    chip = run_command(("sysctl", "-n", "machdep.cpu.brand_string")).strip()
    memory = run_command(("sysctl", "-n", "hw.memsize")).strip()
    architecture = run_command(("uname", "-m")).strip()
    return DeviceInfo(
        vendor="apple",
        model=model_name,
        chip=chip,
        architecture=architecture,
        memory_gb=_bytes_to_gib(memory),
    )
