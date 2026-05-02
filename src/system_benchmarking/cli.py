"""Command-line entry point for system benchmarking."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from system_benchmarking.collectors.apple import collect_apple_device_manifest
from system_benchmarking.runner.registry import available_benchmarks, select_benchmarks
from system_benchmarking.runner.stream_run import (
    DEFAULT_BINARY as STREAM_DEFAULT_BINARY,
    DEFAULT_RESULTS_DIR as STREAM_DEFAULT_RESULTS_DIR,
    run_stream_benchmark,
)

DEFAULT_DEVICES_DIR = Path("devices")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="system-benchmark")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("list", help="List available benchmarks")

    run_parser = subcommands.add_parser("run", help="Run selected benchmarks")
    run_parser.add_argument("--family", choices=["cpu", "gpu", "memory", "system"])
    run_parser.add_argument(
        "--benchmark",
        choices=["stream"],
        help="Run a specific benchmark by name (currently: stream)",
    )
    run_parser.add_argument("--iterations", type=int, default=10, help="Outer iteration count (default: 10)")
    run_parser.add_argument("--binary", type=Path, default=STREAM_DEFAULT_BINARY, help="Path to benchmark binary")
    run_parser.add_argument(
        "--device-manifest",
        type=Path,
        help="Path to device manifest JSON (default: pick the only file under devices/<vendor>/)",
    )
    run_parser.add_argument(
        "--results-dir",
        type=Path,
        default=STREAM_DEFAULT_RESULTS_DIR,
        help="Where to write raw JSON results (default: results/raw)",
    )
    run_parser.add_argument("--dry-run", action="store_true", help="Print selected benchmarks without running them")

    capture_parser = subcommands.add_parser(
        "capture-device",
        help="Capture device manifest (vendor metadata, CPU/GPU/memory, OS) into devices/<vendor>/<slug>.json",
    )
    capture_parser.add_argument(
        "--platform",
        choices=["apple"],
        default="apple",
        help="Platform collector to use (only 'apple' implemented today)",
    )
    capture_parser.add_argument(
        "--devices-dir",
        type=Path,
        default=DEFAULT_DEVICES_DIR,
        help="Root directory for device manifests (default: ./devices)",
    )
    capture_parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print manifest JSON to stdout instead of writing to disk",
    )
    capture_parser.add_argument(
        "--raw",
        action="store_true",
        help="Embed raw system_profiler + sysctl payloads alongside parsed fields",
    )
    capture_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override output path (default: <devices-dir>/<vendor>/<slug>.json)",
    )

    return parser


def _resolve_device_manifest(devices_dir: Path = DEFAULT_DEVICES_DIR) -> Path | None:
    candidates = sorted(devices_dir.rglob("*.json"))
    if len(candidates) == 1:
        return candidates[0]
    return None


def _run_stream(args: argparse.Namespace) -> int:
    manifest_path = args.device_manifest or _resolve_device_manifest()
    if manifest_path is None:
        print(
            "could not infer a device manifest. Pass --device-manifest or run "
            "`system-benchmark capture-device` first.",
            file=sys.stderr,
        )
        return 2

    try:
        out_path = run_stream_benchmark(
            binary=args.binary,
            iterations=args.iterations,
            device_manifest_path=manifest_path,
            results_dir=args.results_dir,
        )
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
        if args.benchmark == "stream":
            return _run_stream(args)
        print(
            "Specify a benchmark to run, e.g. `--benchmark stream`. "
            "Use `--dry-run` to list selected benchmarks.",
            file=sys.stderr,
        )
        return 1

    if args.command == "capture-device":
        return _capture_device(args)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
