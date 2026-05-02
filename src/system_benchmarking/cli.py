"""Command-line entry point for system benchmarking."""

from __future__ import annotations

import argparse

from system_benchmarking.runner.registry import available_benchmarks, select_benchmarks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="system-benchmark")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("list", help="List available benchmarks")

    run_parser = subcommands.add_parser("run", help="Run selected benchmarks")
    run_parser.add_argument("--family", choices=["cpu", "gpu", "memory", "system"])
    run_parser.add_argument("--dry-run", action="store_true", help="Print selected benchmarks without running them")

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    if args.command == "list":
        for benchmark in available_benchmarks():
            print(f"{benchmark.name}\t{benchmark.description}")
        return

    if args.command == "run":
        selected = select_benchmarks(family=args.family)
        if args.dry_run:
            for benchmark in selected:
                print(f"would run {benchmark.name}")
            return
        raise SystemExit("benchmark execution is not implemented yet; use --dry-run")


if __name__ == "__main__":
    main()
