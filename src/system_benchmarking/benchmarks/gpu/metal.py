"""Apple Metal capability benchmark metadata."""

from system_benchmarking.benchmarks import BenchmarkSpec

SPEC = BenchmarkSpec(
    family="gpu",
    name="gpu.metal_capabilities",
    version="0.1",
    description="Apple Metal capability metadata",
    supported_platforms=("darwin",),
)
