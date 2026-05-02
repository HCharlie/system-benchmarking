from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from system_benchmarking.runner.stream_run import run_stream_benchmark


_FIXTURE_STDOUT = """\
Function    Best Rate MB/s  Avg time     Min time     Max time
Copy:           80123.4     0.020100     0.019970     0.020250
Scale:          78456.7     0.020450     0.020395     0.020510
Add:            85234.1     0.028100     0.028145     0.028200
Triad:          84987.2     0.028250     0.028227     0.028310
"""


def _make_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "vendor": "apple",
                "slug": "macbook-pro-test",
                "chip": "Apple M-test",
                "memory_bytes": 68719476736,
            }
        )
    )


class RunStreamBenchmarkTests(unittest.TestCase):
    def test_writes_raw_json_under_results_dir(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            binary = tmp_path / "stream"
            binary.write_bytes(b"")  # existence is what's checked
            manifest = tmp_path / "manifest.json"
            _make_manifest(manifest)
            results_dir = tmp_path / "results" / "raw"

            fixed = datetime(2026, 5, 3, 11, 0, 0, tzinfo=timezone.utc)

            out = run_stream_benchmark(
                binary=binary,
                iterations=2,
                device_manifest_path=manifest,
                results_dir=results_dir,
                threads=18,
                array_size=100000000,
                now=lambda: fixed,
                runner=lambda _: _FIXTURE_STDOUT,
            )

            self.assertTrue(out.exists())
            self.assertEqual(out.parent, results_dir / "apple" / "macbook-pro-test")

            payload = json.loads(out.read_text())
            self.assertEqual(payload["schema_version"], "1")
            self.assertEqual(payload["benchmark"]["name"], "stream")
            self.assertEqual(payload["params"]["iterations"], 2)
            self.assertEqual(payload["params"]["threads"], 18)
            self.assertEqual(payload["device_summary"]["chip"], "Apple M-test")
            self.assertIn("triad", payload["metrics"])
            triad = payload["metrics"]["triad"]
            self.assertEqual(triad["n"], 2)
            self.assertAlmostEqual(triad["median_gbps"], 84.9872, places=4)

    def test_raises_when_binary_missing(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manifest = tmp_path / "m.json"
            _make_manifest(manifest)
            with self.assertRaises(FileNotFoundError):
                run_stream_benchmark(
                    binary=tmp_path / "missing",
                    iterations=1,
                    device_manifest_path=manifest,
                    results_dir=tmp_path / "results",
                    runner=lambda _: _FIXTURE_STDOUT,
                )

    def test_raises_when_manifest_missing(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            binary = tmp_path / "stream"
            binary.write_bytes(b"")
            with self.assertRaises(FileNotFoundError):
                run_stream_benchmark(
                    binary=binary,
                    iterations=1,
                    device_manifest_path=tmp_path / "missing.json",
                    results_dir=tmp_path / "results",
                    runner=lambda _: _FIXTURE_STDOUT,
                )
