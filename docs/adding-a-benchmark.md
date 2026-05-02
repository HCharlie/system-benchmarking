# Adding a Benchmark

Place new benchmarks under the benchmark family they measure:

- `benchmarks/cpu/`
- `benchmarks/gpu/`
- `benchmarks/memory/`
- `benchmarks/system/`

A benchmark should define:

- What it measures
- Which platforms it supports
- Required dependencies
- Input parameters
- Output metrics and units
- Known limitations

Keep benchmark output machine-readable. Human-readable reports should be
generated from raw result files instead of replacing them.

