# System Benchmarking Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create an extensible repository scaffold for a benchmark runner and results archive, with Apple Silicon as the first supported platform.

**Architecture:** Keep executable code under `src/system_benchmarking/` and public benchmark/result documentation under top-level repository folders. Add small Python modules with stable boundaries for benchmarks, collectors, runner behavior, result schemas, and report generation. Start with lightweight, testable contracts rather than hardware-specific heavy implementations.

**Tech Stack:** Python 3.11, standard library `dataclasses`, `json`, `platform`, `subprocess`, `statistics`, and `pytest` for tests.

---

## File Structure

- Create `src/system_benchmarking/benchmarks/__init__.py`: shared benchmark protocol exports.
- Create `src/system_benchmarking/benchmarks/base.py`: benchmark data structures and benchmark result contract.
- Create `src/system_benchmarking/benchmarks/cpu/__init__.py`: CPU benchmark package marker and exports.
- Create `src/system_benchmarking/benchmarks/cpu/scalar.py`: simple CPU scalar benchmark.
- Create `src/system_benchmarking/benchmarks/gpu/__init__.py`: GPU benchmark package marker and exports.
- Create `src/system_benchmarking/benchmarks/gpu/metal.py`: Apple Metal capability benchmark contract.
- Create `src/system_benchmarking/benchmarks/memory/__init__.py`: memory benchmark package marker and exports.
- Create `src/system_benchmarking/benchmarks/memory/bandwidth.py`: simple memory bandwidth benchmark.
- Create `src/system_benchmarking/benchmarks/system/__init__.py`: system benchmark package marker.
- Create `src/system_benchmarking/collectors/__init__.py`: collector package marker.
- Create `src/system_benchmarking/collectors/apple/__init__.py`: Apple collector exports.
- Create `src/system_benchmarking/collectors/apple/device_info.py`: Apple device metadata collector with command injection for tests.
- Create `src/system_benchmarking/results/__init__.py`: result helpers exports.
- Create `src/system_benchmarking/results/schema.py`: normalized raw result schema and JSON serialization.
- Create `src/system_benchmarking/reports/__init__.py`: report package marker.
- Create `src/system_benchmarking/reports/markdown.py`: Markdown report generation from result objects.
- Create `src/system_benchmarking/runner/__init__.py`: runner package marker.
- Create `src/system_benchmarking/runner/registry.py`: benchmark registry for selecting families.
- Modify `src/system_benchmarking/cli.py`: expose `list` and `run --dry-run` commands.
- Create `tests/test_results_schema.py`: schema serialization tests.
- Create `tests/test_registry.py`: registry selection tests.
- Create `tests/test_apple_device_info.py`: Apple collector parsing tests using fixture command output.
- Create `docs/devices.md`: device metadata guidance.
- Create `devices/amd/README.md`, `devices/intel/README.md`, `devices/nvidia/README.md`: vendor directories for future devices.

## Task 1: Result Schema

**Files:**
- Create: `src/system_benchmarking/results/__init__.py`
- Create: `src/system_benchmarking/results/schema.py`
- Test: `tests/test_results_schema.py`

- [ ] **Step 1: Write the failing test**

```python
from system_benchmarking.results.schema import BenchmarkIdentity, DeviceInfo, MetricSet, RawResult


def test_raw_result_serializes_to_expected_json_dict():
    result = RawResult(
        schema_version="0.1",
        timestamp="2026-05-02T20:50:00Z",
        device=DeviceInfo(
            vendor="apple",
            model="MacBook Pro",
            chip="Apple M3 Max",
            architecture="arm64",
            memory_gb=36,
        ),
        environment={"os": "macOS", "os_version": "15.0"},
        benchmark=BenchmarkIdentity(family="cpu", name="scalar_integer", version="0.1"),
        metrics=MetricSet(score=123.4, unit="ops/s", samples=[120.0, 123.4, 126.8]),
    )

    assert result.to_dict() == {
        "schema_version": "0.1",
        "timestamp": "2026-05-02T20:50:00Z",
        "device": {
            "vendor": "apple",
            "model": "MacBook Pro",
            "chip": "Apple M3 Max",
            "architecture": "arm64",
            "memory_gb": 36,
        },
        "environment": {"os": "macOS", "os_version": "15.0"},
        "benchmark": {"family": "cpu", "name": "scalar_integer", "version": "0.1"},
        "metrics": {"score": 123.4, "unit": "ops/s", "samples": [120.0, 123.4, 126.8]},
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_results_schema.py -v`

Expected: FAIL because `system_benchmarking.results.schema` does not exist.

- [ ] **Step 3: Implement result schema**

```python
"""Raw benchmark result schema."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DeviceInfo:
    vendor: str
    model: str
    chip: str
    architecture: str
    memory_gb: int | None = None


@dataclass(frozen=True)
class BenchmarkIdentity:
    family: str
    name: str
    version: str


@dataclass(frozen=True)
class MetricSet:
    score: float
    unit: str
    samples: list[float]


@dataclass(frozen=True)
class RawResult:
    schema_version: str
    timestamp: str
    device: DeviceInfo
    environment: dict[str, Any]
    benchmark: BenchmarkIdentity
    metrics: MetricSet

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
```

Create `src/system_benchmarking/results/__init__.py`:

```python
"""Result schema and serialization helpers."""

from system_benchmarking.results.schema import BenchmarkIdentity, DeviceInfo, MetricSet, RawResult

__all__ = ["BenchmarkIdentity", "DeviceInfo", "MetricSet", "RawResult"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_results_schema.py -v`

Expected: PASS.

## Task 2: Benchmark Registry

**Files:**
- Create: `src/system_benchmarking/benchmarks/__init__.py`
- Create: `src/system_benchmarking/benchmarks/base.py`
- Create: `src/system_benchmarking/runner/__init__.py`
- Create: `src/system_benchmarking/runner/registry.py`
- Test: `tests/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
from system_benchmarking.runner.registry import available_benchmarks, select_benchmarks


def test_available_benchmarks_include_initial_families():
    names = [benchmark.name for benchmark in available_benchmarks()]

    assert "cpu.scalar_integer" in names
    assert "memory.bandwidth" in names
    assert "gpu.metal_capabilities" in names


def test_select_benchmarks_filters_by_family():
    selected = select_benchmarks(family="cpu")

    assert [benchmark.family for benchmark in selected] == ["cpu"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_registry.py -v`

Expected: FAIL because the runner registry does not exist.

- [ ] **Step 3: Implement benchmark contract and registry**

Create `src/system_benchmarking/benchmarks/base.py`:

```python
"""Benchmark contracts shared by benchmark families."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from system_benchmarking.results import MetricSet


@dataclass(frozen=True)
class BenchmarkSpec:
    family: str
    name: str
    version: str
    description: str
    supported_platforms: tuple[str, ...]


class Benchmark(Protocol):
    spec: BenchmarkSpec

    def run(self) -> MetricSet:
        ...
```

Create `src/system_benchmarking/benchmarks/__init__.py`:

```python
"""Benchmark interfaces and implementations."""

from system_benchmarking.benchmarks.base import Benchmark, BenchmarkSpec

__all__ = ["Benchmark", "BenchmarkSpec"]
```

Create `src/system_benchmarking/runner/registry.py`:

```python
"""Benchmark registry."""

from __future__ import annotations

from system_benchmarking.benchmarks.base import BenchmarkSpec


_BENCHMARKS = (
    BenchmarkSpec("cpu", "cpu.scalar_integer", "0.1", "Scalar integer CPU loop", ("darwin", "linux", "win32")),
    BenchmarkSpec("memory", "memory.bandwidth", "0.1", "Sequential memory bandwidth", ("darwin", "linux", "win32")),
    BenchmarkSpec("gpu", "gpu.metal_capabilities", "0.1", "Apple Metal capability metadata", ("darwin",)),
)


def available_benchmarks() -> list[BenchmarkSpec]:
    return list(_BENCHMARKS)


def select_benchmarks(family: str | None = None) -> list[BenchmarkSpec]:
    if family is None:
        return available_benchmarks()
    return [benchmark for benchmark in _BENCHMARKS if benchmark.family == family]
```

Create `src/system_benchmarking/runner/__init__.py`:

```python
"""Benchmark runner utilities."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_registry.py -v`

Expected: PASS.

## Task 3: Apple Device Collector

**Files:**
- Create: `src/system_benchmarking/collectors/__init__.py`
- Create: `src/system_benchmarking/collectors/apple/__init__.py`
- Create: `src/system_benchmarking/collectors/apple/device_info.py`
- Test: `tests/test_apple_device_info.py`

- [ ] **Step 1: Write the failing test**

```python
from system_benchmarking.collectors.apple.device_info import collect_apple_device_info


def test_collect_apple_device_info_parses_command_output():
    outputs = {
        ("sysctl", "-n", "machdep.cpu.brand_string"): "Apple M3 Max\n",
        ("sysctl", "-n", "hw.memsize"): "38654705664\n",
        ("uname", "-m"): "arm64\n",
    }

    def fake_run(command: tuple[str, ...]) -> str:
        return outputs[command]

    device = collect_apple_device_info(run_command=fake_run, model_name="MacBook Pro")

    assert device.vendor == "apple"
    assert device.model == "MacBook Pro"
    assert device.chip == "Apple M3 Max"
    assert device.architecture == "arm64"
    assert device.memory_gb == 36
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_apple_device_info.py -v`

Expected: FAIL because the Apple collector does not exist.

- [ ] **Step 3: Implement Apple collector**

```python
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
```

Create `src/system_benchmarking/collectors/__init__.py`:

```python
"""System metadata collectors."""
```

Create `src/system_benchmarking/collectors/apple/__init__.py`:

```python
"""Apple platform collectors."""

from system_benchmarking.collectors.apple.device_info import collect_apple_device_info

__all__ = ["collect_apple_device_info"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_apple_device_info.py -v`

Expected: PASS.

## Task 4: CLI Listing and Dry Run

**Files:**
- Modify: `src/system_benchmarking/cli.py`
- Test manually with CLI commands.

- [ ] **Step 1: Update CLI implementation**

```python
"""Command-line entry point for system benchmarking."""

from __future__ import annotations

import argparse

from system_benchmarking.runner.registry import available_benchmarks, select_benchmarks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="system-benchmark")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("list", help="List available benchmarks")

    run_parser = subcommands.add_parser("run", help="Run selected benchmarks")
    run_parser.add_argument("--family", choices=["cpu", "gpu", "memory", "system"])
    run_parser.add_argument("--dry-run", action="store_true", help="Print selected benchmarks without running them")

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    if args.command == "list":
        for benchmark in available_benchmarks():
            print(f"{benchmark.name}\t{benchmark.description}")
        return

    if args.command == "run":
        selected = select_benchmarks(family=args.family)
        if args.dry_run:
            for benchmark in selected:
                print(f"would run {benchmark.name}")
            return
        raise SystemExit("benchmark execution is not implemented yet; use --dry-run")
```

- [ ] **Step 2: Run CLI checks**

Run: `python -m system_benchmarking.cli list`

Expected output includes `cpu.scalar_integer`, `memory.bandwidth`, and `gpu.metal_capabilities`.

Run: `python -m system_benchmarking.cli run --family cpu --dry-run`

Expected output: `would run cpu.scalar_integer`.

## Task 5: Repository Directories and Documentation

**Files:**
- Create: `devices/amd/README.md`
- Create: `devices/intel/README.md`
- Create: `devices/nvidia/README.md`
- Create: `docs/devices.md`
- Create package directories listed in File Structure with `__init__.py` files.

- [ ] **Step 1: Add vendor README files**

`devices/amd/README.md`:

```markdown
# AMD Devices

Add one Markdown or JSON file per tested AMD CPU or GPU system. Include the
processor model, GPU model when present, memory configuration, operating system,
power limits, cooling details, and benchmark run notes.
```

`devices/intel/README.md`:

```markdown
# Intel Devices

Add one Markdown or JSON file per tested Intel CPU or GPU system. Include the
processor model, integrated or discrete GPU details, memory configuration,
operating system, power limits, cooling details, and benchmark run notes.
```

`devices/nvidia/README.md`:

```markdown
# NVIDIA Devices

Add one Markdown or JSON file per tested NVIDIA GPU system. Include the GPU
model, driver version, CUDA or compute runtime version when relevant, host CPU,
memory configuration, operating system, power limits, and benchmark run notes.
```

- [ ] **Step 2: Add device documentation**

`docs/devices.md`:

```markdown
# Devices

Device files describe the machines used for benchmark runs. Store known devices
under `devices/<vendor>/` and use lowercase hyphenated filenames such as
`macbook-pro-m3-max.md` or `ryzen-9-7950x-rtx-4090.md`.

Each device entry should include:

- Vendor
- Model
- CPU or SoC
- GPU
- Memory size and configuration
- Operating system
- Driver or runtime versions when relevant
- Power mode or power limits
- Cooling and thermal notes
- Links to raw result files produced by this device
```

- [ ] **Step 3: Verify structure**

Run: `find src/system_benchmarking -maxdepth 3 -type d | sort`

Expected output includes `benchmarks`, `collectors`, `reports`, `results`, and `runner`.

Run: `find devices -maxdepth 2 -type f | sort`

Expected output includes README files for `apple`, `amd`, `intel`, and `nvidia`.

## Task 6: Final Verification

**Files:**
- No new files.

- [ ] **Step 1: Run all tests**

Run: `python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 2: Run CLI smoke checks**

Run: `python -m system_benchmarking.cli list`

Expected: command exits successfully and prints the initial benchmark registry.

Run: `python -m system_benchmarking.cli run --family cpu --dry-run`

Expected: command exits successfully and prints `would run cpu.scalar_integer`.

- [ ] **Step 3: Check Git status if repository metadata exists**

Run: `git status --short`

Expected in this workspace: if `.git` does not exist, Git reports `fatal: not a git repository`. If the project is initialized as a Git repository later, this command should show only intentional scaffold changes.
