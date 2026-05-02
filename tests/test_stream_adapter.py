from __future__ import annotations

import unittest

from system_benchmarking.adapters.stream import (
    KERNELS,
    KernelDistribution,
    parse_stream_output,
    run_stream,
)


_FIXTURE_STDOUT = """\
-------------------------------------------------------------
STREAM version $Revision: 5.10 $
-------------------------------------------------------------
This system uses 8 bytes per array element.
-------------------------------------------------------------
Array size = 100000000 (elements), Offset = 0 (elements)
Memory per array = 762.9 MiB (= 0.7 GiB).
Total memory required = 2288.8 MiB (= 2.2 GiB).
-------------------------------------------------------------
Function    Best Rate MB/s  Avg time     Min time     Max time
Copy:           80123.4     0.020100     0.019970     0.020250
Scale:          78456.7     0.020450     0.020395     0.020510
Add:            85234.1     0.028100     0.028145     0.028200
Triad:          84987.2     0.028250     0.028227     0.028310
-------------------------------------------------------------
Solution Validates: avg error less than 1.000000e-13 on all three arrays
-------------------------------------------------------------
"""


class ParseStreamOutputTests(unittest.TestCase):
    def test_parses_all_four_kernels(self):
        parsed = parse_stream_output(_FIXTURE_STDOUT)
        self.assertEqual(set(parsed.keys()), set(KERNELS))

    def test_extracts_rates_and_times(self):
        parsed = parse_stream_output(_FIXTURE_STDOUT)
        triad = parsed["triad"]
        self.assertAlmostEqual(triad.rate_mb_s, 84987.2)
        self.assertAlmostEqual(triad.rate_gb_s, 84.9872)
        self.assertAlmostEqual(triad.min_time_s, 0.028227)
        self.assertAlmostEqual(triad.max_time_s, 0.028310)

    def test_raises_on_missing_kernel(self):
        truncated = "\n".join(_FIXTURE_STDOUT.splitlines()[:-5])
        with self.assertRaises(ValueError) as ctx:
            parse_stream_output(truncated)
        self.assertIn("missing kernels", str(ctx.exception))


class RunStreamTests(unittest.TestCase):
    def test_aggregates_samples_across_iterations(self):
        outputs = iter([
            _FIXTURE_STDOUT,
            _FIXTURE_STDOUT.replace("84987.2", "85100.5").replace("80123.4", "79800.1"),
            _FIXTURE_STDOUT.replace("84987.2", "84500.0").replace("80123.4", "80500.0"),
        ])

        def fake_runner(_command):
            return next(outputs)

        result = run_stream(binary=__import__("pathlib").Path("/fake"), iterations=3, runner=fake_runner)

        self.assertEqual(set(result.keys()), set(KERNELS))
        triad = result["triad"]
        self.assertEqual(len(triad.samples_gb_s), 3)
        self.assertAlmostEqual(triad.median, 84.9872, places=4)
        self.assertGreater(triad.maximum, triad.minimum)

    def test_rejects_non_positive_iterations(self):
        with self.assertRaises(ValueError):
            run_stream(__import__("pathlib").Path("/fake"), iterations=0, runner=lambda _: "")


class KernelDistributionTests(unittest.TestCase):
    def test_summary_statistics(self):
        dist = KernelDistribution(kernel="triad", samples_gb_s=[100.0, 110.0, 105.0, 95.0, 102.0])
        self.assertAlmostEqual(dist.median, 102.0)
        self.assertAlmostEqual(dist.minimum, 95.0)
        self.assertAlmostEqual(dist.maximum, 110.0)
        self.assertGreater(dist.stddev, 0.0)
        self.assertIn("median_gbps", dist.to_dict())

    def test_zero_stddev_for_single_sample(self):
        dist = KernelDistribution(kernel="copy", samples_gb_s=[300.0])
        self.assertEqual(dist.stddev, 0.0)
