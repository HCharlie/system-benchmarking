"""Command-line entry point for system benchmarking."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from system_benchmarking.collectors.apple import collect_apple_device_manifest
from system_benchmarking.reports.markdown import write_results_report
from system_benchmarking.runner.cpu_run import (
    DEFAULT_SCALAR_BINARY,
    run_scalar_benchmark,
    run_stress_ng_benchmark,
    run_sysbench_benchmark,
)
from system_benchmarking.runner.disk_run import run_fio_benchmark
from system_benchmarking.runner.gpu_run import run_metal_probe_benchmark
from system_benchmarking.runner.network_run import run_iperf3_benchmark, run_ping_benchmark
from system_benchmarking.runner.power_run import run_powermetrics_benchmark
from system_benchmarking.runner.memory_run import (
    DEFAULT_POINTER_CHASE_BINARY,
    run_pointer_chase_benchmark,
    run_tinymembench_benchmark,
)
from system_benchmarking.runner.registry import available_benchmarks, select_benchmarks
from system_benchmarking.runner.stream_run import (
    DEFAULT_BINARY as STREAM_DEFAULT_BINARY,
    DEFAULT_RESULTS_DIR as DEFAULT_RESULTS_DIR,
    run_stream_benchmark,
)

DEFAULT_DEVICES_DIR = Path("devices")

BENCHMARK_CHOICES = (
    "stream",
    "sysbench",
    "stress-ng",
    "scalar",
    "tinymembench",
    "pointer-chase",
    "fio",
    "iperf3",
    "ping",
    "metal-probe",
    "powermetrics",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="system-benchmark")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("list", help="List available benchmarks")

    run_parser = subcommands.add_parser("run", help="Run selected benchmarks")
    run_parser.add_argument("--family", choices=["cpu", "gpu", "memory", "system"])
    run_parser.add_argument("--benchmark", choices=BENCHMARK_CHOICES)
    run_parser.add_argument("--iterations", type=int, default=10)
    run_parser.add_argument("--threads", type=int, default=None, help="Threads/workers (CPU benches)")
    run_parser.add_argument("--seconds", type=int, default=30, help="Per-iteration duration (CPU benches)")
    run_parser.add_argument("--cpu-max-prime", type=int, default=20000, help="sysbench --cpu-max-prime")
    run_parser.add_argument("--method", default="all", help="stress-ng --cpu-method")
    run_parser.add_argument("--inner-iters", type=int, default=1_000_000_000, help="Inner loop count for native scalar")
    run_parser.add_argument("--access-count", type=int, default=40_000_000, help="Pointer-chase accesses per size")
    run_parser.add_argument("--profile", type=Path, default=None, help="Path to fio/iperf profile file")
    run_parser.add_argument("--workdir", type=Path, default=None, help="Working directory for fio (defaults to cwd)")
    run_parser.add_argument("--target", default=None, help="iperf3/ping target host")
    run_parser.add_argument("--duration", type=int, default=30, help="iperf3 duration in seconds")
    run_parser.add_argument("--count", type=int, default=100, help="ping count")
    run_parser.add_argument("--samples", type=int, default=60, help="powermetrics samples")
    run_parser.add_argument("--interval-ms", type=int, default=1000, help="powermetrics sampling interval")
    run_parser.add_argument("--no-sudo", action="store_true", help="run powermetrics without sudo (testing only)")
    run_parser.add_argument("--binary", type=Path, default=None, help="Override benchmark binary path")
    run_parser.add_argument("--device-manifest", type=Path, default=None)
    run_parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    run_parser.add_argument("--dry-run", action="store_true")

    report_parser = subcommands.add_parser("report", help="Render Markdown report from raw JSON results")
    report_parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    report_parser.add_argument("--out", type=Path, default=Path("results/reports/all.md"))

    capture_parser = subcommands.add_parser(
        "capture-device",
        help="Capture device manifest into devices/<vendor>/<slug>.json",
    )
    capture_parser.add_argument("--platform", choices=["apple"], default="apple")
    capture_parser.add_argument("--devices-dir", type=Path, default=DEFAULT_DEVICES_DIR)
    capture_parser.add_argument("--stdout", action="store_true")
    capture_parser.add_argument("--raw", action="store_true")
    capture_parser.add_argument("--output", type=Path, default=None)

    return parser


def _resolve_device_manifest(devices_dir: Path = DEFAULT_DEVICES_DIR) -> Path | None:
    candidates = sorted(devices_dir.rglob("*.json"))
    if len(candidates) == 1:
        return candidates[0]
    return None


def _resolve_threads(args: argparse.Namespace) -> int:
    if args.threads is not None:
        return args.threads
    import os as _os

    return _os.cpu_count() or 1


def _run_benchmark(args: argparse.Namespace) -> int:
    manifest_path = args.device_manifest or _resolve_device_manifest()
    if manifest_path is None:
        print(
            "could not infer a device manifest. Pass --device-manifest or run "
            "`system-benchmark capture-device` first.",
            file=sys.stderr,
        )
        return 2

    common = {
        "device_manifest_path": manifest_path,
        "results_dir": args.results_dir,
    }

    try:
        if args.benchmark == "stream":
            out_path = run_stream_benchmark(
                binary=args.binary or STREAM_DEFAULT_BINARY,
                iterations=args.iterations,
                threads=args.threads,
                **common,
            )
        elif args.benchmark == "sysbench":
            out_path = run_sysbench_benchmark(
                threads=_resolve_threads(args),
                time_seconds=args.seconds,
                cpu_max_prime=args.cpu_max_prime,
                iterations=args.iterations,
                **common,
            )
        elif args.benchmark == "stress-ng":
            out_path = run_stress_ng_benchmark(
                workers=_resolve_threads(args),
                seconds=args.seconds,
                method=args.method,
                iterations=args.iterations,
                **common,
            )
        elif args.benchmark == "scalar":
            out_path = run_scalar_benchmark(
                binary=args.binary or DEFAULT_SCALAR_BINARY,
                iterations=args.iterations,
                inner_iters=args.inner_iters,
                **common,
            )
        elif args.benchmark == "tinymembench":
            if args.binary is None:
                print("--binary required for tinymembench (path to compiled binary)", file=sys.stderr)
                return 2
            out_path = run_tinymembench_benchmark(
                binary=args.binary,
                iterations=args.iterations,
                **common,
            )
        elif args.benchmark == "pointer-chase":
            out_path = run_pointer_chase_benchmark(
                binary=args.binary or DEFAULT_POINTER_CHASE_BINARY,
                iterations=args.iterations,
                access_count=args.access_count,
                **common,
            )
        elif args.benchmark == "fio":
            if args.profile is None:
                print("--profile required for fio (e.g. profiles/disk/seq-read-1m.fio)", file=sys.stderr)
                return 2
            out_path = run_fio_benchmark(
                profile=args.profile,
                workdir=args.workdir,
                **common,
            )
        elif args.benchmark == "iperf3":
            if args.target is None:
                print("--target required for iperf3 (e.g. 127.0.0.1)", file=sys.stderr)
                return 2
            out_path = run_iperf3_benchmark(
                target=args.target,
                duration=args.duration,
                **common,
            )
        elif args.benchmark == "ping":
            if args.target is None:
                print("--target required for ping (e.g. 1.1.1.1)", file=sys.stderr)
                return 2
            out_path = run_ping_benchmark(
                target=args.target,
                count=args.count,
                **common,
            )
        elif args.benchmark == "metal-probe":
            out_path = run_metal_probe_benchmark(**common)
        elif args.benchmark == "powermetrics":
            out_path = run_powermetrics_benchmark(
                samples=args.samples,
                interval_ms=args.interval_ms,
                sudo=not args.no_sudo,
                **common,
            )
        else:
            print(
                f"Specify --benchmark from {BENCHMARK_CHOICES}. Use `--dry-run` to list selected.",
                file=sys.stderr,
            )
            return 1
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"wrote {out_path}", file=sys.stderr)
    return 0


def _capture_device(args: argparse.Namespace) -> int:
    if args.platform != "apple":
        print(f"platform '{args.platform}' not yet implemented", file=sys.stderr)
        return 2

    manifest = collect_apple_device_manifest(include_raw=args.raw)
    payload = json.dumps(manifest.to_dict(), indent=2, sort_keys=True)

    if args.stdout:
        print(payload)
        return 0

    output_path = args.output or (args.devices_dir / manifest.vendor / f"{manifest.slug}.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(payload + "\n")
    print(f"wrote {output_path}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "list":
        for benchmark in available_benchmarks():
            print(f"{benchmark.name}\t{benchmark.description}")
        return 0

    if args.command == "run":
        selected = select_benchmarks(family=args.family)
        if args.dry_run:
            for benchmark in selected:
                print(f"would run {benchmark.name}")
            return 0
        return _run_benchmark(args)

    if args.command == "capture-device":
        return _capture_device(args)

    if args.command == "report":
        out = write_results_report(args.results_dir, args.out)
        print(f"wrote {out}", file=sys.stderr)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
