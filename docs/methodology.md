# Methodology

Benchmark results are only useful when the test environment is documented and
the run can be repeated. Every benchmark should record:

- Device model and chip name
- CPU core layout when available
- GPU model or integrated GPU details when available
- Memory size and memory architecture
- Operating system version
- Power mode and thermal state when available
- Benchmark parameters
- Number of warmup and measured iterations
- Score, unit, and timestamp

Prefer reporting multiple measurements rather than a single number. At minimum,
store the raw samples, median, minimum, maximum, and standard deviation.

