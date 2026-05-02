"""Apple device metadata collection.

Captures a reproducible manifest of an Apple Silicon (or Intel) Mac by calling
`system_profiler`, `sysctl`, and `uname`. Output is a DeviceManifest suitable
for serialization to JSON under devices/apple/<slug>.json.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from system_benchmarking.results import (
    CacheSizes,
    CpuTopology,
    DeviceInfo,
    DeviceManifest,
    GpuInfo,
    OsInfo,
)

MANIFEST_SCHEMA_VERSION = "1"

CommandRunner = Callable[[tuple[str, ...]], str]


def _run_command(command: tuple[str, ...]) -> str:
    return subprocess.check_output(command, text=True)


def _bytes_to_gib(value: int) -> int:
    return round(value / (1024**3))


def _parse_sysctl_block(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if ": " not in line:
            continue
        key, _, value = line.partition(": ")
        out[key.strip()] = value.strip()
    return out


def _maybe_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


_SLUG_PUNCT = re.compile(r"[^a-z0-9]+")


def slugify(*parts: str) -> str:
    """Build a stable filesystem-safe slug from name parts."""
    joined = " ".join(p for p in parts if p)
    lowered = joined.lower()
    cleaned = _SLUG_PUNCT.sub("-", lowered).strip("-")
    return cleaned or "unknown"


_SYSCTL_KEYS: tuple[str, ...] = (
    "hw.ncpu",
    "hw.physicalcpu",
    "hw.logicalcpu",
    "hw.perflevel0.physicalcpu",
    "hw.perflevel0.logicalcpu",
    "hw.perflevel1.physicalcpu",
    "hw.perflevel1.logicalcpu",
    "hw.memsize",
    "hw.pagesize",
    "hw.cachelinesize",
    "hw.l1icachesize",
    "hw.l1dcachesize",
    "hw.l2cachesize",
    "machdep.cpu.brand_string",
    "kern.osversion",
    "kern.version",
)


def _read_sysctl(run_command: CommandRunner) -> dict[str, str]:
    output = run_command(("sysctl",) + _SYSCTL_KEYS)
    return _parse_sysctl_block(output)


def _read_system_profiler(run_command: CommandRunner) -> dict[str, Any]:
    output = run_command(
        (
            "system_profiler",
            "SPHardwareDataType",
            "SPSoftwareDataType",
            "SPDisplaysDataType",
            "-json",
        )
    )
    return json.loads(output)


def _first(items: list[dict[str, Any]] | None) -> dict[str, Any]:
    return (items or [{}])[0]


def _extract_cpu(sysctl: dict[str, str]) -> CpuTopology:
    # On Apple Silicon: perflevel0 = performance cluster, perflevel1 = efficiency cluster.
    p_physical = _maybe_int(sysctl.get("hw.perflevel0.physicalcpu"))
    e_physical = _maybe_int(sysctl.get("hw.perflevel1.physicalcpu"))
    return CpuTopology(
        total_cores=_maybe_int(sysctl.get("hw.physicalcpu")) or _maybe_int(sysctl.get("hw.ncpu")) or 0,
        performance_cores=p_physical,
        efficiency_cores=e_physical,
        logical_cores=_maybe_int(sysctl.get("hw.logicalcpu")) or _maybe_int(sysctl.get("hw.ncpu")),
    )


def _extract_cache(sysctl: dict[str, str]) -> CacheSizes:
    return CacheSizes(
        l1d_bytes=_maybe_int(sysctl.get("hw.l1dcachesize")),
        l1i_bytes=_maybe_int(sysctl.get("hw.l1icachesize")),
        l2_bytes=_maybe_int(sysctl.get("hw.l2cachesize")),
        line_bytes=_maybe_int(sysctl.get("hw.cachelinesize")),
        page_bytes=_maybe_int(sysctl.get("hw.pagesize")),
    )


def _extract_gpu(displays: list[dict[str, Any]]) -> GpuInfo | None:
    if not displays:
        return None
    primary = displays[0]
    name = primary.get("sppci_model") or primary.get("_name") or "Unknown GPU"
    cores = _maybe_int(primary.get("sppci_cores"))
    metal_family = primary.get("spdisplays_mtlgpufamilysupport")
    return GpuInfo(name=name, cores=cores, metal_family=metal_family)


def _extract_os(software: dict[str, Any], sysctl: dict[str, str]) -> OsInfo:
    raw_version = software.get("os_version", "")
    name, version, build = "macOS", "", None
    # Example: "macOS 26.4.1 (25E253)"
    match = re.match(r"(\S+)\s+([0-9.]+)(?:\s+\(([^)]+)\))?", raw_version)
    if match:
        name, version, build = match.group(1), match.group(2), match.group(3)
    if build is None:
        build = sysctl.get("kern.osversion")
    return OsInfo(
        name=name or "macOS",
        version=version or sysctl.get("kern.osversion", "unknown"),
        build=build,
        kernel=software.get("kernel_version"),
    )


def _parse_memory_bytes(hardware: dict[str, Any], sysctl: dict[str, str]) -> int:
    sysctl_value = _maybe_int(sysctl.get("hw.memsize"))
    if sysctl_value:
        return sysctl_value
    text = hardware.get("physical_memory", "")
    match = re.match(r"([\d.]+)\s*(GB|MB|TB)", text)
    if not match:
        return 0
    value = float(match.group(1))
    unit = match.group(2)
    multiplier = {"MB": 1024**2, "GB": 1024**3, "TB": 1024**4}[unit]
    return int(value * multiplier)


def collect_apple_device_manifest(
    run_command: CommandRunner = _run_command,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    include_raw: bool = False,
) -> DeviceManifest:
    """Capture a full Apple Mac device manifest.

    Pure with respect to `run_command` and `now` so tests can substitute fakes.
    Set ``include_raw=True`` to embed the raw system_profiler + sysctl payloads
    alongside the parsed fields, useful for forensics.
    """

    sp = _read_system_profiler(run_command)
    sysctl = _read_sysctl(run_command)
    architecture = run_command(("uname", "-m")).strip()

    hardware = _first(sp.get("SPHardwareDataType"))
    software = _first(sp.get("SPSoftwareDataType"))
    displays = sp.get("SPDisplaysDataType", [])

    chip = hardware.get("chip_type") or sysctl.get("machdep.cpu.brand_string", "Unknown")
    model_id = hardware.get("machine_model", "Unknown")
    marketing_name = hardware.get("machine_name", "Mac")
    memory_bytes = _parse_memory_bytes(hardware, sysctl)

    raw_payload: dict[str, Any] = {}
    if include_raw:
        raw_payload = {"system_profiler": sp, "sysctl": sysctl}

    return DeviceManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        captured_at=now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        slug=slugify(marketing_name, chip),
        vendor="apple",
        model_id=model_id,
        marketing_name=marketing_name,
        chip=chip,
        architecture=architecture,
        memory_bytes=memory_bytes,
        cpu=_extract_cpu(sysctl),
        cache=_extract_cache(sysctl),
        gpu=_extract_gpu(displays),
        os=_extract_os(software, sysctl),
        raw=raw_payload,
    )


def collect_apple_device_info(
    run_command: CommandRunner = _run_command,
    model_name: str | None = None,
) -> DeviceInfo:
    """Backwards-compatible lightweight collector used by older callers."""
    chip = run_command(("sysctl", "-n", "machdep.cpu.brand_string")).strip()
    memory = run_command(("sysctl", "-n", "hw.memsize")).strip()
    architecture = run_command(("uname", "-m")).strip()
    return DeviceInfo(
        vendor="apple",
        model=model_name or "Unknown Mac",
        chip=chip,
        architecture=architecture,
        memory_gb=_bytes_to_gib(int(memory)),
    )
