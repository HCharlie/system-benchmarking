"""Metal GPU capability probe.

Pulls the same SPDisplaysDataType data we use during device capture, but
formatted as a benchmark result so it lives alongside actual GPU compute
results once those are added. Pure metadata — does not run a kernel.

A real Metal compute benchmark needs Swift or Objective-C. The recommended
path is to vendor a small Swift program under ``benchmarks/gpu/compute/metal/``,
build it with ``swiftc``, and add an adapter that parses its JSON output.
This probe is the placeholder until that exists.
"""

from __future__ import annotations

import json
import platform
import subprocess
from collections.abc import Callable, Sequence
from typing import Any

ProcessRunner = Callable[[Sequence[str]], str]


def parse_displays_json(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    displays = payload.get("SPDisplaysDataType", [])
    if not displays:
        return {"available": False}
    primary = displays[0]
    return {
        "available": True,
        "name": primary.get("sppci_model") or primary.get("_name"),
        "vendor": primary.get("spdisplays_vendor"),
        "cores": int(primary["sppci_cores"]) if primary.get("sppci_cores") else None,
        "metal_family": primary.get("spdisplays_mtlgpufamilysupport"),
        "bus": primary.get("sppci_bus"),
    }


def _default_runner(command: Sequence[str]) -> str:
    return subprocess.check_output(list(command), text=True)


def probe_metal(runner: ProcessRunner = _default_runner) -> dict[str, Any]:
    if platform.system() != "Darwin":
        return {"available": False, "reason": "metal probe only supported on macOS"}
    try:
        raw = runner(["system_profiler", "SPDisplaysDataType", "-json"])
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        return {"available": False, "reason": f"system_profiler failed: {exc!r}"}
    return parse_displays_json(raw)
