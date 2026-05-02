from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from system_benchmarking.reports.markdown import render_results_report, write_results_report


def _stream_payload(slug: str, started_at: str, triad_median: float) -> dict:
    return {
        "schema_version": "1",
        "benchmark": {"family": "memory", "name": "stream", "version": "5.10"},
        "device_ref": f"devices/apple/{slug}.json",
        "device_summary": {
            "vendor": "apple",
            "slug": slug,
            "chip": "Apple M5 Max",
            "memory_bytes": 68719476736,
        },
        "started_at": started_at,
        "ended_at": started_at,
        "metrics": {
            "copy": {"median_gbps": 380.0, "stddev_gbps": 1.2, "n": 5},
            "scale": {"median_gbps": 370.0, "stddev_gbps": 1.5, "n": 5},
            "add": {"median_gbps": 410.0, "stddev_gbps": 1.0, "n": 5},
            "triad": {"median_gbps": triad_median, "stddev_gbps": 1.4, "n": 5},
        },
    }


class MarkdownReportTests(unittest.TestCase):
    def test_renders_empty_message_when_no_results(self):
        with TemporaryDirectory() as tmp:
            md = render_results_report(Path(tmp))
            self.assertIn("No results found", md)

    def test_renders_stream_results_grouped_by_device(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            d1 = tmp_path / "apple" / "macbook-pro-apple-m5-max"
            d2 = tmp_path / "apple" / "mac-mini-m2"
            d1.mkdir(parents=True)
            d2.mkdir(parents=True)
            (d1 / "2026-05-03T10-00-00Z-stream.json").write_text(
                json.dumps(_stream_payload("macbook-pro-apple-m5-max", "2026-05-03T10:00:00Z", 410.0))
            )
            (d2 / "2026-05-03T11-00-00Z-stream.json").write_text(
                json.dumps(_stream_payload("mac-mini-m2", "2026-05-03T11:00:00Z", 95.0))
            )

            md = render_results_report(tmp_path)
            self.assertIn("## macbook-pro-apple-m5-max", md)
            self.assertIn("## mac-mini-m2", md)
            self.assertIn("stream.triad", md)
            self.assertIn("410.00", md)
            self.assertIn("95.00", md)
            self.assertGreaterEqual(md.count("Apple M5 Max"), 1)

    def test_write_results_report_creates_parent_dirs(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            d = tmp_path / "apple" / "x"
            d.mkdir(parents=True)
            (d / "r.json").write_text(json.dumps(_stream_payload("x", "2026-05-03T10:00:00Z", 100.0)))
            out = tmp_path / "reports" / "deep" / "report.md"
            written = write_results_report(tmp_path, out)
            self.assertTrue(written.exists())
            self.assertIn("stream.triad", written.read_text())
