# System Benchmarking

Reproducible benchmarks for comparing compute, memory, and system-level
performance across Apple Silicon, x86, ARM, and GPU-enabled machines.

The initial focus is Apple systems: CPU performance, GPU compute, memory
bandwidth and latency, and basic system metadata collection. The project layout
is intentionally extensible so new benchmark families, vendors, devices, and
report formats can be added without reshaping the repository.

## Scope

- CPU benchmarks: integer, floating point, SIMD/vector, compiler-sensitive tasks
- GPU benchmarks: compute kernels, matrix operations, memory throughput
- Memory benchmarks: bandwidth, latency, cache behavior
- System benchmarks: thermal behavior, power behavior, real workloads
- Device metadata: reproducible descriptions of machines under test
- Results: raw machine output, processed summaries, and reports

Out of scope for the first version: storage, networking, display, battery-life
testing, and full benchmark scoring. These can be added later as separate
benchmark families.

## Development

This repo uses `uv` for dependency management.

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run system-benchmark list
```

## Project Structure

```text
system-benchmarking/
├── benchmarks/
│   ├── cpu/
│   ├── gpu/
│   ├── memory/
│   └── system/
├── devices/
│   └── apple/
├── results/
│   ├── raw/
│   ├── processed/
│   └── reports/
├── scripts/
├── src/
│   └── system_benchmarking/
└── docs/
```

## Result Layout

Raw results should be grouped by vendor, device, and run date:

```text
results/raw/apple/macbook-pro-m3-max/2026-05-02.json
results/raw/apple/mac-mini-m2/2026-05-02.json
```

Each result should include the benchmark name, device metadata, environment,
score, units, timestamp, and enough configuration to reproduce the run.

## First Milestone

1. Collect Apple system information from `system_profiler`, `sysctl`, and Metal.
2. Add CPU microbenchmarks for scalar, floating point, and SIMD workloads.
3. Add memory bandwidth and latency tests.
4. Add GPU compute benchmarks through Metal.
5. Store raw JSON results and generate a simple Markdown report.
