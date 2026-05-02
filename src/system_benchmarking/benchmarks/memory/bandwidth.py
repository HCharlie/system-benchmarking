"""Memory bandwidth benchmark metadata."""

from system_benchmarking.benchmarks import BenchmarkSpec

SPEC = BenchmarkSpec(
    family="memory",
    name="memory.bandwidth",
    version="0.1",
    description="Sequential memory bandwidth",
    supported_platforms=("darwin", "linux", "win32"),
)
