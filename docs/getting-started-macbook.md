# Getting Started: MacBook Pro (Apple Silicon)

Learning path. Follow phases in order. Each phase = small, runs end-to-end, teaches one concept.

Target machine for this guide: **MacBook Pro, M5 Max, 18 cores, 64 GB, macOS 26.x**.
Steps generalize to any Apple Silicon mac.

---

## Principles

- Wrap proven tools first. Write own kernels only after wrappers work.
- Vertical slice beats horizontal scaffold. One benchmark end-to-end, then add more.
- Raw JSON = source of truth. Reports generated, never hand-edited.
- Record full environment per run. Repro impossible otherwise.
- Multiple iterations. Report median + p99 + stddev, not mean.

## Mac caveats (know before measuring)

- No `perf`. Use `sudo powermetrics` for CPU/GPU power, `xcrun xctrace` for sampling.
- No `taskset`. Cannot pin cores. Document run as "scheduler-managed".
- No clean turbo disable. Mitigations: AC power, Low Power Mode OFF, lid open, ambient room temp, 60s idle before run, drop first 1-2 iters as warmup.
- Background work matters. Quit Slack/Chrome/Spotify. Check `top -l 1 -n 5 -o cpu` before run.
- Apple Silicon = heterogeneous (P-cores + E-cores). Pinning impossible → run multiple times, note variance.
- Thermal throttling kicks in fast under sustained load. Record `powermetrics --samplers thermal` alongside benchmark.

---

## Phase 0 — Tooling (15 min)

Install brew tools.

```bash
brew install stress-ng sysbench fio iperf3 hyperfine ioping coreutils
brew install --cask macfuse  # optional, for fs benchmarks
xcode-select --install         # for clang, Metal, xctrace
```

Verify uv + repo:

```bash
cd ~/src/github.com/HCharlie/system-benchmarking
uv sync
uv run python -m unittest discover -s tests -v
uv run system-benchmark list
```

Acceptance: `list` runs without error.

---

## Phase 1 — Device capture (concept: reproducibility) (1–2 h)

Goal: snapshot machine state into JSON. Every benchmark run links to one snapshot.

Steps:

1. Read existing `src/system_benchmarking/collectors/apple/device_info.py`.
2. Extend it to call:
   - `system_profiler SPHardwareDataType SPSoftwareDataType SPDisplaysDataType -json`
   - `sysctl -a` → filter `hw.*`, `machdep.cpu.*`, `kern.osversion`
   - `ioreg -l -d 1 -w 0` (optional, deeper)
3. Output schema (versioned):

```json
{
  "schema_version": 1,
  "captured_at": "2026-05-03T10:00:00Z",
  "device": {
    "vendor": "apple",
    "model_id": "Mac17,7",
    "marketing_name": "MacBook Pro",
    "chip": "Apple M5 Max",
    "cpu": {"p_cores": 12, "e_cores": 6, "total": 18},
    "memory_bytes": 68719476736,
    "gpu": {"name": "Apple M5 Max GPU", "cores": 40}
  },
  "os": {"name": "macOS", "version": "26.4.1", "build": "25E253"},
  "kernel": "Darwin 25.4.0",
  "raw": { "system_profiler": {...}, "sysctl": {...} }
}
```

4. CLI: `uv run system-benchmark capture-device > devices/apple/macbook-pro-m5-max.json`.
5. Test: parse fixture in `tests/test_apple_device_info.py`, assert fields.

Acceptance: command emits valid JSON with all fields above. Stored under `devices/apple/`.

**Why this first:** every later result needs to point to this snapshot. Build the anchor first.

---

## Phase 2 — First real benchmark: STREAM (concept: memory bandwidth) (2–3 h)

STREAM = de-facto memory bandwidth benchmark. Single number (Triad GB/s) cited everywhere.

Steps:

1. Vendor STREAM source under `benchmarks/memory/bandwidth/stream/`.
   - `git clone https://github.com/jeffhammond/STREAM.git` into that dir, or vendor `stream.c` directly (~400 lines).
2. Build script: `scripts/build-stream.sh`. Compile with `-O3 -fopenmp -mcpu=apple-m1` (works for M-series). Tune `STREAM_ARRAY_SIZE` so working set ≥ 4× last-level cache (≥ 100 MB safe for M-series).
3. Adapter: `src/system_benchmarking/adapters/stream.py`. Run binary, parse stdout (regex `Triad:\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)`), emit JSON.
4. Wire into runner: `benchmarks/memory/bandwidth.py` Benchmark subclass calls adapter.
5. CLI: `uv run system-benchmark run --family memory --benchmark stream --iterations 10`.
6. Output:

```text
results/raw/apple/macbook-pro-m5-max/2026-05-03T10-15-00Z-stream.json
```

Schema (per result):

```json
{
  "schema_version": 1,
  "run_id": "uuid",
  "benchmark": {"family": "memory", "name": "stream", "version": "5.10"},
  "device_ref": "devices/apple/macbook-pro-m5-max.json",
  "started_at": "...", "ended_at": "...",
  "params": {"array_size": 100000000, "threads": 18, "compiler": "clang 17", "flags": "-O3 -fopenmp"},
  "metrics": {
    "copy_gbps":  {"samples": [...], "median": 380.1, "p99": 384.2, "stddev": 1.4, "unit": "GB/s"},
    "scale_gbps": {...},
    "add_gbps":   {...},
    "triad_gbps": {...}
  },
  "environment": {"ac_power": true, "low_power_mode": false, "background_load_pct": 3.2}
}
```

7. Test: feed canned STREAM stdout to adapter, assert parsed correctly.

Acceptance:
- `triad_gbps.median` reported. Sane = 200–500 GB/s on M-series (M5 Max ≈ 400+).
- 10 iterations, stddev < 5% of median. If higher → background noise, fix env not the code.
- Raw JSON validates against schema.

**Why this benchmark:** one number, well-defined, cross-platform, teaches the full pipeline (build → run → parse → store → report).

---

## Phase 3 — Report generator (concept: separating raw from view) (1 h)

Read `results/raw/**/*.json`, render Markdown table.

Steps:

1. Extend `src/system_benchmarking/reports/markdown.py`.
2. CLI: `uv run system-benchmark report --out results/reports/macbook-pro-m5-max.md`.
3. Group by device, family, benchmark. Show median + stddev + date.
4. Test: feed fixture results, assert markdown output.

Acceptance: Markdown file generated. Re-running with new results refreshes report without losing history.

---

## Phase 4 — CPU benchmarks (concept: integer vs FP vs SIMD) (3–4 h)

Wrap **sysbench** first, then small own kernel.

Steps:

1. `sysbench cpu --threads=18 --time=30 --cpu-max-prime=20000 run` → events/sec.
2. Adapter parses sysbench output, emits JSON like Phase 2.
3. `stress-ng --cpu 18 --cpu-method matrixprod --metrics-brief --timeout 30s` → bogo ops/sec. Adapter parses stderr.
4. Own scalar benchmark — write tiny C program: tight integer loop, FP loop, NEON SIMD loop. Compile with `-O3 -march=armv8.4-a+simd`. Time with `clock_gettime(CLOCK_MONOTONIC)`. Vendor under `benchmarks/cpu/scalar/native/`.
5. Run with 1 thread, then N threads. Compare scaling. Plot threads vs ops/sec.

Concept to learn:
- Why sysbench prime-finding ≠ STREAM ≠ matrix-mul. Different bottlenecks (FP units, branch predictor, memory).
- P-core vs E-core scheduling. Run with 1, 6, 12, 18 threads → see knee.

Acceptance: 3 CPU benchmarks running, results in JSON, report shows scaling curve.

---

## Phase 5 — Memory latency + cache (concept: hierarchy) (2–3 h)

STREAM measures bandwidth, not latency. Add latency tests.

Steps:

1. Vendor `tinymembench` (https://github.com/ssvb/tinymembench). Compile, wrap, parse.
2. Optional: own pointer-chase benchmark. Allocate buffer of size N, fill with permutation, follow pointers for M iterations, measure ns/access. Sweep N from 4 KB to 1 GB → see L1/L2/SLC/DRAM steps.
3. Plot N (log scale) vs latency → cache hierarchy visible.

Concept to learn: latency ≠ bandwidth. Memory bound code may be limited by either. Cache size matters.

Acceptance: latency curve generated. L1 (~1 ns), L2 (~3-5 ns), SLC (~15-25 ns), DRAM (~100+ ns) visible.

---

## Phase 6 — Disk (concept: IOPS vs throughput vs latency) (2 h)

`fio` = the standard. One tool.

Steps:

1. Adapter: `src/system_benchmarking/adapters/fio.py`. Run with `--output-format=json+`, parse JSON.
2. Define profiles under `profiles/disk/`:
   - `seq-read-1m.yaml`: sequential read, 1 MB blocks, 30 s.
   - `rand-read-4k-qd32.yaml`: random read, 4 KB blocks, queue depth 32.
   - `rand-write-4k-qd1.yaml`: random write, 4 KB, qd=1 (worst case latency).
3. Run on `/tmp` (APFS, internal SSD). Caveat: APFS compression + caching skews results — note in output. Use `--direct=1` if filesystem allows; on macOS may not.
4. Report MB/s, IOPS, p50/p99/p99.9 latency.

Concept to learn: same SSD gives wildly different numbers depending on block size, queue depth, R/W mix. One number meaningless.

Acceptance: 3 fio profiles run, results stored, report shows seq vs rand difference.

---

## Phase 7 — Network (concept: throughput vs latency vs jitter) (1–2 h)

Need second machine OR loopback (limited value).

Steps:

1. Loopback first: `iperf3 -s` in one terminal, `iperf3 -c 127.0.0.1 -J -t 30` in another. Adapter parses JSON.
2. Real test: another mac on same Wi-Fi/wired. Compare Wi-Fi 6E vs ethernet vs Thunderbolt.
3. Latency: `ping -c 100 target` → parse min/avg/max/stddev. Or `sockperf ping-pong` for sub-ms.

Concept to learn: throughput tells you bulk speed, latency tells you interactive feel, jitter tells you stability. Different workloads care about different ones.

Acceptance: at least loopback iperf3 result stored.

---

## Phase 8 — GPU via Metal (concept: compute kernels) (4–6 h, advanced)

Hardest phase. Skip until Phases 0–3 solid.

Steps:

1. Capability probe first: list Metal device, max threadgroup size, family. Already partially in `benchmarks/gpu/metal.py`.
2. Wrap **clpeak** first (works via OpenCL→Metal shim on mac, or skip).
3. Write Metal compute kernel: SAXPY, then GEMM. Use Swift or PyObjC. Time with `MTLCommandBuffer.GPUStartTime/GPUEndTime`.
4. Compare GPU GEMM TFLOPS to CPU GEMM (Accelerate framework `vDSP`/`BLAS`).

Concept to learn: launch overhead dominates small kernels, bandwidth dominates large ones. Unified memory on Apple = no copy cost, very different from discrete GPU.

Acceptance: at least Metal capability JSON + one compute kernel TFLOPS number.

---

## Phase 9 — Power + thermal (concept: sustained vs peak) (2 h)

Run a bench under `powermetrics` so power and thermal recorded alongside throughput.

Steps:

1. Wrapper: `sudo powermetrics --samplers cpu_power,gpu_power,thermal -i 1000 -n 60` → 60 samples 1s apart.
2. Parse output, store as time series in result JSON.
3. Run a 5-minute STREAM or stress-ng session, plot:
   - Throughput vs time (does it drop?)
   - Package power vs time (does it cap?)
   - CPU die temperature vs time

Concept to learn: peak ≠ sustained. M-series throttles after ~30-60s under heavy load. Real workload behavior depends on duration.

Acceptance: time-series plot showing thermal throttling (or lack of it) on M5 Max.

---

## Phase 10 — Cleanup + automation (1 h)

After phases 1–6 working:

1. Add `justfile` or `Makefile`:
   ```make
   bench-quick: capture-device run-stream run-sysbench report
   bench-full:  capture-device run-stream run-sysbench run-fio run-iperf run-gpu run-power report
   ```
2. Add `profiles/quick.yaml`, `profiles/full.yaml` controlling which benchmarks + iterations.
3. Add CI (GitHub Actions): NOT for absolute numbers (cloud runner = useless), just to catch parser/schema regressions on fixture data.
4. Tag a v0.1.0. From here, adding Linux = new collector + same wrappers (most tools cross-platform).

---

## Reference card

| Concept | Phase | Key tool |
|---|---|---|
| Reproducibility | 1 | `system_profiler`, `sysctl` |
| Memory bandwidth | 2 | STREAM |
| Reporting pipeline | 3 | own Markdown gen |
| CPU integer/FP | 4 | sysbench, stress-ng, own C |
| Memory latency / cache | 5 | tinymembench, own pointer-chase |
| Disk | 6 | fio |
| Network | 7 | iperf3, ping |
| GPU compute | 8 | Metal, clpeak |
| Power / thermal | 9 | powermetrics |
| Automation | 10 | justfile, profiles |

## Progress checklist

- [x] Phase 0 — Tooling installed, `uv run system-benchmark list` works
- [x] Phase 1 — Device JSON captured for this mac (`devices/apple/macbook-pro-apple-m5-max.json`)
- [x] Phase 2 — STREAM wrapper wired (build script, adapter, runner, tests). Run on real machine to populate `results/raw/`.
- [ ] Phase 3 — Markdown report generated from raw JSON
- [ ] Phase 4 — sysbench + stress-ng + own scalar bench
- [ ] Phase 5 — Latency curve plotted
- [ ] Phase 6 — fio with 3 profiles
- [ ] Phase 7 — iperf3 loopback (+ real second machine)
- [ ] Phase 8 — Metal capability + 1 compute kernel
- [ ] Phase 9 — Power/thermal time series under sustained load
- [ ] Phase 10 — `just bench-quick` works end-to-end

---

## What you learn at end

- How to design a reproducible benchmark.
- Difference between bandwidth, latency, IOPS, throughput, jitter.
- Why a single "score" lies.
- How to read `perf`-style counters (mac equivalent: `xctrace`).
- How thermal limits real-world performance on laptops.
- Schema design for multi-machine, multi-year result archives.
- When to wrap an existing tool vs write your own.
