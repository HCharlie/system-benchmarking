# System Benchmarking Repository Design

## Purpose

The repository is named `system-benchmarking`. It serves two related purposes:

- A benchmark runner/tool that users can clone and run on their own machines.
- A reproducible results archive for comparing processors, GPUs, memory systems,
  and whole-system behavior across vendors and platforms.

The initial scope is Apple Silicon systems, including CPU, GPU, memory, and
system metadata collection. The structure must remain extensible for future
Intel, AMD, NVIDIA, ARM, Linux, and Windows support.

## Naming

- Repository: `system-benchmarking`
- Python package: `system_benchmarking`
- CLI command: `system-benchmark`

This naming is intentionally broad. It avoids tying the project to Apple,
processors only, or one benchmark family.

## Architecture

The repository separates benchmark implementation, benchmark descriptions,
device metadata, results, and documentation.

- `src/system_benchmarking/` contains executable Python code.
- `benchmarks/` contains benchmark descriptions, documentation, and external
  benchmark assets when needed.
- `devices/` contains known device metadata organized by vendor.
- `results/` contains raw benchmark output, processed summaries, and generated
  reports.
- `docs/` contains methodology, result schemas, contribution guidance, and
  design notes.
- `scripts/` contains convenience scripts that are not part of the Python API.
- `tests/` contains automated tests for collectors, result validation, reports,
  and runner behavior.

## Proposed Layout

```text
system-benchmarking/
├── benchmarks/
│   ├── cpu/
│   ├── gpu/
│   ├── memory/
│   └── system/
├── devices/
│   ├── apple/
│   ├── amd/
│   ├── intel/
│   └── nvidia/
├── docs/
│   ├── adding-a-benchmark.md
│   ├── devices.md
│   ├── methodology.md
│   └── result-format.md
├── results/
│   ├── raw/
│   ├── processed/
│   └── reports/
├── scripts/
├── src/
│   └── system_benchmarking/
│       ├── cli.py
│       ├── benchmarks/
│       │   ├── cpu/
│       │   ├── gpu/
│       │   ├── memory/
│       │   └── system/
│       ├── collectors/
│       │   ├── apple/
│       │   ├── linux/
│       │   └── windows/
│       ├── reports/
│       ├── results/
│       └── runner/
└── tests/
```

## Apple-First Milestone

The first implementation target is Apple Silicon. The initial code should focus
on:

- System metadata from `system_profiler`.
- CPU and memory metadata from `sysctl`.
- GPU and Metal capability detection.
- CPU scalar and floating-point benchmarks.
- Memory bandwidth and latency benchmarks.
- A Metal GPU benchmark interface that initially reports capability and dry-run
  metadata, then grows into executable Metal compute kernels after the runner
  and result format are stable.
- Raw JSON result output.
- A simple Markdown report generated from raw or processed results.

## Result Layout

Raw results are organized by vendor, normalized device slug, and run date:

```text
results/raw/apple/macbook-pro-m3-max/2026-05-02.json
results/raw/apple/mac-mini-m2/2026-05-02.json
```

Processed results and reports remain separate from raw data:

```text
results/processed/apple/macbook-pro-m3-max/summary.json
results/reports/apple-m-series-comparison.md
```

Raw JSON is the source of truth. Reports should be generated from raw or
processed result files, not manually maintained as the only record.

## Extensibility Rules

- Add new benchmark families as separate folders under both top-level
  `benchmarks/` and `src/system_benchmarking/benchmarks/` when executable code
  is required.
- Add platform-specific system collectors under
  `src/system_benchmarking/collectors/<platform>/`.
- Add known device metadata under `devices/<vendor>/`.
- Keep raw results immutable where practical. If normalization changes, create
  new processed output instead of rewriting historical raw files.
- Every benchmark must document what it measures, supported platforms,
  dependencies, parameters, metrics, units, and limitations.

## Testing

The first test layer should cover:

- Result schema validation.
- Device slug normalization.
- Apple collector parsing with fixture data.
- Runner behavior for selecting and executing benchmark families.
- Report generation from fixture result files.

Benchmarks that depend on specific hardware should expose dry-run or fixture
paths so the project can still be tested on machines without that hardware.
