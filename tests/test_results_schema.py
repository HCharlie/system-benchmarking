from system_benchmarking.results.schema import BenchmarkIdentity, DeviceInfo, MetricSet, RawResult


import unittest


class RawResultSchemaTests(unittest.TestCase):
    def test_raw_result_serializes_to_expected_json_dict(self):
        result = RawResult(
            schema_version="0.1",
            timestamp="2026-05-02T20:50:00Z",
            device=DeviceInfo(
                vendor="apple",
                model="MacBook Pro",
                chip="Apple M3 Max",
                architecture="arm64",
                memory_gb=36,
            ),
            environment={"os": "macOS", "os_version": "15.0"},
            benchmark=BenchmarkIdentity(family="cpu", name="scalar_integer", version="0.1"),
            metrics=MetricSet(score=123.4, unit="ops/s", samples=[120.0, 123.4, 126.8]),
        )

        self.assertEqual(
            result.to_dict(),
            {
                "schema_version": "0.1",
                "timestamp": "2026-05-02T20:50:00Z",
                "device": {
                    "vendor": "apple",
                    "model": "MacBook Pro",
                    "chip": "Apple M3 Max",
                    "architecture": "arm64",
                    "memory_gb": 36,
                    "manifest_ref": None,
                },
                "environment": {"os": "macOS", "os_version": "15.0"},
                "benchmark": {"family": "cpu", "name": "scalar_integer", "version": "0.1"},
                "metrics": {"score": 123.4, "unit": "ops/s", "samples": [120.0, 123.4, 126.8]},
            },
        )
