"""Command-line entry point for system benchmarking."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from system_benchmarking.collectors.apple import collect_apple_device_manifest
from system_benchmarking.runner.registry import available_benchmarks, select_benchmarks

DEFAULT_DEVICES_DIR = Path("devices")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="system-benchmark")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("list", help="List available benchmarks")

    run_parser = subcommands.add_parser("run", help="Run selected benchmarks")
    run_parser.add_argument("--family", choices=["cpu", "gpu", "memory", "system"])
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
        print("benchmark execution is not implemented yet; use --dry-run", file=sys.stderr)
        return 1

    if args.command == "capture-device":
        return _capture_device(args)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
