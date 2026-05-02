"""Result schema and device manifest types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class DeviceInfo:
    """Lightweight device descriptor embedded inside a benchmark result.

    The full reproducible snapshot lives in a DeviceManifest under devices/.
    """

    vendor: str
    model: str
    chip: str
    architecture: str
    memory_gb: int | None = None
    manifest_ref: str | None = None


@dataclass(frozen=True)
class CpuTopology:
    total_cores: int
    performance_cores: int | None = None
    efficiency_cores: int | None = None
    logical_cores: int | None = None


@dataclass(frozen=True)
class CacheSizes:
    l1d_bytes: int | None = None
    l1i_bytes: int | None = None
    l2_bytes: int | None = None
    line_bytes: int | None = None
    page_bytes: int | None = None


@dataclass(frozen=True)
class GpuInfo:
    name: str
    cores: int | None = None
    metal_family: str | None = None


@dataclass(frozen=True)
class OsInfo:
    name: str
    version: str
    build: str | None = None
    kernel: str | None = None


@dataclass(frozen=True)
class DeviceManifest:
    """Full reproducible snapshot of a machine.

    One file per machine under devices/<vendor>/<slug>.json. Benchmark results
    reference this manifest by path so raw outputs stay small.
    """

    schema_version: str
    captured_at: str
    slug: str
    vendor: str
    model_id: str
    marketing_name: str
    chip: str
    architecture: str
    memory_bytes: int
    cpu: CpuTopology
    cache: CacheSizes
    gpu: GpuInfo | None
    os: OsInfo
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
