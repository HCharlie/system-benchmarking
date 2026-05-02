"""Benchmark registry."""

from __future__ import annotations

from system_benchmarking.benchmarks.cpu.scalar import SPEC as CPU_SCALAR
from system_benchmarking.benchmarks.gpu.metal import SPEC as GPU_METAL
from system_benchmarking.benchmarks.memory.bandwidth import SPEC as MEMORY_BANDWIDTH
from system_benchmarking.benchmarks.base import BenchmarkSpec

_BENCHMARKS = (CPU_SCALAR, MEMORY_BANDWIDTH, GPU_METAL)


def available_benchmarks() -> list[BenchmarkSpec]:
    return list(_BENCHMARKS)


def select_benchmarks(family: str | None = None) -> list[BenchmarkSpec]:
    if family is None:
        return available_benchmarks()
    return [benchmark for benchmark in _BENCHMARKS if benchmark.family == family]
