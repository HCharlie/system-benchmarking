"""Markdown report generation from raw JSON benchmark results."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from system_benchmarking.results import RawResult


def render_result_summary(result: RawResult) -> str:
    """Render a single legacy RawResult as Markdown."""
    data = result.to_dict()
    return (
        f"# {data['benchmark']['name']}\n\n"
        f"- Device: {data['device']['model']} ({data['device']['chip']})\n"
        f"- Score: {data['metrics']['score']} {data['metrics']['unit']}\n"
    )


@dataclass(frozen=True)
class _Row:
    benchmark: str
    metric: str
    median: float
    stddev: float
    unit: str
    samples: int
    started_at: str


def _load_raw_results(results_dir: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in sorted(results_dir.rglob("*.json")):
        try:
            out.append(json.loads(path.read_text()))
        except json.JSONDecodeError:
            continue
    return out


def _row_for_distribution(name: str, kernel: str, distribution: dict[str, Any], started_at: str) -> _Row:
    return _Row(
        benchmark=f"{name}.{kernel}",
        metric="bandwidth",
        median=float(distribution.get("median_gbps", 0.0)),
        stddev=float(distribution.get("stddev_gbps", 0.0)),
        unit="GB/s",
        samples=int(distribution.get("n", 0)),
        started_at=started_at,
    )


def _extract_rows(payload: dict[str, Any]) -> Iterable[_Row]:
    benchmark = payload.get("benchmark", {})
    name = benchmark.get("name", "unknown")
    started_at = payload.get("started_at", "")
    metrics = payload.get("metrics", {})

    if name == "stream":
        for kernel, dist in metrics.items():
            yield _row_for_distribution(name, kernel, dist, started_at)
        return

    if isinstance(metrics, dict) and "median" in metrics:
        yield _Row(
            benchmark=name,
            metric=metrics.get("metric", "score"),
            median=float(metrics.get("median", 0.0)),
            stddev=float(metrics.get("stddev", 0.0)),
            unit=metrics.get("unit", ""),
            samples=int(metrics.get("n", 0)),
            started_at=started_at,
        )
        return

    if isinstance(metrics, dict) and "score" in metrics:
        yield _Row(
            benchmark=name,
            metric="score",
            median=float(metrics["score"]),
            stddev=0.0,
            unit=metrics.get("unit", ""),
            samples=len(metrics.get("samples", []) or []),
            started_at=started_at,
        )
        return

    if isinstance(metrics, dict):
        for sub_name, sub in metrics.items():
            if isinstance(sub, dict) and "median" in sub:
                yield _Row(
                    benchmark=f"{name}.{sub_name}",
                    metric="score",
                    median=float(sub["median"]),
                    stddev=float(sub.get("stddev", 0.0)),
                    unit=sub.get("unit", ""),
                    samples=int(sub.get("n", 0)),
                    started_at=started_at,
                )


def render_results_report(results_dir: Path) -> str:
    """Render all results found under `results_dir` into a single Markdown document.

    Output is grouped by device slug then benchmark family/name. Each row shows
    median, stddev, unit, sample count, and run timestamp so the same machine
    measured on different days remains comparable.
    """
    payloads = _load_raw_results(results_dir)

    by_device: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for payload in payloads:
        slug = (payload.get("device_summary") or {}).get("slug") or payload.get("device_ref", "unknown")
        by_device[slug].append(payload)

    lines: list[str] = ["# System Benchmark Results", ""]
    if not payloads:
        lines.append("_No results found. Run a benchmark and re-render._")
        return "\n".join(lines) + "\n"

    for slug in sorted(by_device.keys()):
        first = by_device[slug][0]
        summary = first.get("device_summary") or {}
        chip = summary.get("chip", "unknown chip")
        memory = summary.get("memory_bytes")
        memory_str = f"{round(memory / (1024**3))} GB" if memory else "?"
        lines.append(f"## {slug}")
        lines.append("")
        lines.append(f"- chip: **{chip}**")
        lines.append(f"- memory: {memory_str}")
        lines.append("")
        lines.append("| Benchmark | Metric | Median | Stddev | Unit | n | Started |")
        lines.append("|---|---|---:|---:|---|---:|---|")

        rows: list[_Row] = []
        for payload in by_device[slug]:
            rows.extend(_extract_rows(payload))
        rows.sort(key=lambda r: (r.benchmark, r.started_at))

        for row in rows:
            lines.append(
                f"| {row.benchmark} | {row.metric} | {row.median:.2f} | {row.stddev:.2f} | "
                f"{row.unit} | {row.samples} | {row.started_at} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def write_results_report(results_dir: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_results_report(results_dir))
    return output_path
