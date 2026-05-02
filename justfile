# Convenience targets for system-benchmarking.
# Run `just` to see this list. Requires https://github.com/casey/just

default:
    @just --list

# --- Build native binaries ---

build-stream:
    scripts/build-stream.sh

build-scalar:
    scripts/build-scalar.sh

build-pointer-chase:
    scripts/build-pointer-chase.sh

build-all: build-stream build-scalar build-pointer-chase

# --- Capture device manifest ---

capture-device:
    uv run system-benchmark capture-device

# --- Individual benchmarks ---

run-stream iterations="10":
    uv run system-benchmark run --benchmark stream --iterations {{iterations}}

run-sysbench iterations="3":
    uv run system-benchmark run --benchmark sysbench --iterations {{iterations}}

run-stress-ng iterations="3":
    uv run system-benchmark run --benchmark stress-ng --iterations {{iterations}}

run-scalar iterations="5":
    uv run system-benchmark run --benchmark scalar --iterations {{iterations}}

run-pointer-chase:
    uv run system-benchmark run --benchmark pointer-chase --iterations 1

run-fio profile="profiles/disk/seq-read-1m.fio":
    uv run system-benchmark run --benchmark fio --profile {{profile}}

run-iperf3-loopback duration="10":
    uv run system-benchmark run --benchmark iperf3 --target 127.0.0.1 --duration {{duration}}

run-ping target="1.1.1.1" count="100":
    uv run system-benchmark run --benchmark ping --target {{target}} --count {{count}}

run-metal-probe:
    uv run system-benchmark run --benchmark metal-probe

run-powermetrics samples="60":
    uv run system-benchmark run --benchmark powermetrics --samples {{samples}}

# --- Bundles ---

# Quick smoke: capture device, STREAM, sysbench, scalar, ping, report.
bench-quick: capture-device build-stream build-scalar
    just run-stream 5
    just run-sysbench 1
    just run-scalar 3
    just run-metal-probe
    just report

# Long sweep: everything except powermetrics (which needs sudo) and iperf3 to a remote target.
bench-full: capture-device build-all
    just run-stream 10
    just run-sysbench 3
    just run-stress-ng 3
    just run-scalar 5
    just run-pointer-chase
    just run-fio profiles/disk/seq-read-1m.fio
    just run-fio profiles/disk/rand-read-4k-qd32.fio
    just run-fio profiles/disk/rand-write-4k-qd1.fio
    just run-metal-probe
    just report

# --- Report + tests ---

report:
    uv run system-benchmark report --out results/reports/all.md

test:
    uv run python -m unittest discover -s tests -v

clean:
    rm -rf .build
