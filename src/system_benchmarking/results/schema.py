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
