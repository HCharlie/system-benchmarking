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
