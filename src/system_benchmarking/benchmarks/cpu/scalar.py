"""Scalar CPU benchmark metadata."""

from system_benchmarking.benchmarks import BenchmarkSpec

SPEC = BenchmarkSpec(
    family="cpu",
    name="cpu.scalar_integer",
    version="0.1",
    description="Scalar integer CPU loop",
    supported_platforms=("darwin", "linux", "win32"),
)
