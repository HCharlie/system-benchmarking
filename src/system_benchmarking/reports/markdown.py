"""Markdown report generation."""

from __future__ import annotations

from system_benchmarking.results import RawResult


def render_result_summary(result: RawResult) -> str:
    data = result.to_dict()
    return (
        f"# {data['benchmark']['name']}\n\n"
        f"- Device: {data['device']['model']} ({data['device']['chip']})\n"
        f"- Score: {data['metrics']['score']} {data['metrics']['unit']}\n"
    )
