from __future__ import annotations

import json
import unittest

from system_benchmarking.adapters.fio import parse_fio_json, run_fio


_FIO_JSON = json.dumps(
    {
        "fio version": "fio-3.36",
        "global options": {"runtime": "30", "ioengine": "posixaio"},
        "jobs": [
            {
                "jobname": "rand-read-4k",
                "read": {
                    "iops": 250000.5,
                    "bw": 1024000,
                    "clat_ns": {
                        "min": 1000,
                        "max": 1_000_000,
                        "mean": 12500.0,
                        "stddev": 3000.0,
                        "percentile": {
                            "50.000000": 11000.0,
                            "95.000000": 18000.0,
                            "99.000000": 22000.0,
                            "99.900000": 50000.0,
                            "99.990000": 200000.0,
                        },
                    },
                },
                "write": {"iops": 0, "bw": 0, "clat_ns": {}},
            }
        ],
    }
)


class FioAdapterTests(unittest.TestCase):
    def test_parse_extracts_read_summary(self):
        parsed = parse_fio_json(_FIO_JSON)
        self.assertEqual(parsed["fio_version"], "fio-3.36")
        self.assertEqual(len(parsed["jobs"]), 1)
        read = parsed["jobs"][0]["read"]
        self.assertAlmostEqual(read["iops"], 250000.5)
        self.assertAlmostEqual(read["bw_kib_s"], 1024000)
        self.assertEqual(read["p50_ns"], 11000.0)
        self.assertEqual(read["p99_ns"], 22000.0)

    def test_run_passes_profile_args(self):
        captured: list[list[str]] = []

        def fake_runner(command):
            captured.append(list(command))
            return _FIO_JSON

        run_fio(profile_args=["profiles/disk/x.fio", "--directory=/tmp"], runner=fake_runner)
        self.assertEqual(len(captured), 1)
        self.assertIn("--output-format=json+", captured[0])
        self.assertIn("profiles/disk/x.fio", captured[0])
        self.assertIn("--directory=/tmp", captured[0])
