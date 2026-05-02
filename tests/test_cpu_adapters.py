from __future__ import annotations

import unittest
from pathlib import Path

from system_benchmarking.adapters.scalar_native import parse_scalar_output, run_scalar
from system_benchmarking.adapters.stress_ng import parse_stress_ng_cpu, run_stress_ng_cpu
from system_benchmarking.adapters.sysbench import parse_sysbench_cpu, run_sysbench_cpu


_SYSBENCH_OUTPUT = """\
sysbench 1.0.20 (using bundled LuaJIT 2.1.0-beta2)

Running the test with following options:
Number of threads: 18
Initializing random number generator from current time

Prime numbers limit: 20000

Initializing worker threads...

Threads started!

CPU speed:
    events per second: 12345.67

General statistics:
    total time:                          30.0012s
    total number of events:              370370

Latency (ms):
         min:                                    1.40
         avg:                                    1.46
         max:                                   40.00
         95th percentile:                        1.55
         sum:                               541620.20

Threads fairness:
    events (avg/stddev):           20576.1111/45.50
    execution time (avg/stddev):   30.0901/0.01
"""


_STRESS_NG_STDERR = """\
stress-ng: info:  [12345] dispatching hogs: 18 cpu
stress-ng: info:  [12345] successful run completed in 30.04s
stress-ng: metrc: [12345] stressor       bogo ops real time  usr time  sys time   bogo ops/s     bogo ops/s
stress-ng: metrc: [12345]                           (secs)    (secs)    (secs)   (real time) (usr+sys time)
stress-ng: metrc: [12345] cpu             5400000     30.04   540.50      0.10    179786.95       9990.74
stress-ng: info:  [12345] for a 30.04s run time:
"""


_SCALAR_STDOUT = """\
{"kernel":"int64_add", "ops":4000000000, "seconds":0.420000, "ops_per_second":9.524e+09}
{"kernel":"fp64_fma", "ops":3000000000, "seconds":0.500000, "ops_per_second":6.000e+09}
{"kernel":"neon_fp32x4_fma", "ops":6000000000, "seconds":0.250000, "ops_per_second":2.400e+10}
"""


class SysbenchTests(unittest.TestCase):
    def test_parse_extracts_fields(self):
        sample = parse_sysbench_cpu(_SYSBENCH_OUTPUT)
        self.assertAlmostEqual(sample.events_per_second, 12345.67)
        self.assertEqual(sample.total_events, 370370)
        self.assertAlmostEqual(sample.total_time_s, 30.0012)
        self.assertEqual(sample.threads, 18)
        self.assertEqual(sample.cpu_max_prime, 20000)

    def test_parse_raises_on_missing_field(self):
        with self.assertRaises(ValueError):
            parse_sysbench_cpu("nope")

    def test_run_aggregates_iterations(self):
        outputs = iter([_SYSBENCH_OUTPUT, _SYSBENCH_OUTPUT.replace("12345.67", "12500.00")])
        result = run_sysbench_cpu(
            threads=18,
            iterations=2,
            runner=lambda _: next(outputs),
        )
        eps = result["events_per_second"]
        self.assertEqual(eps["n"], 2)
        self.assertAlmostEqual(eps["min"], 12345.67)
        self.assertAlmostEqual(eps["max"], 12500.00)


class StressNgTests(unittest.TestCase):
    def test_parse_extracts_cpu_row(self):
        sample = parse_stress_ng_cpu(_STRESS_NG_STDERR)
        self.assertEqual(sample.bogo_ops, 5400000)
        self.assertAlmostEqual(sample.real_time_s, 30.04)
        self.assertAlmostEqual(sample.bogo_ops_per_second_real, 179786.95)

    def test_run_aggregates(self):
        outs = iter([_STRESS_NG_STDERR, _STRESS_NG_STDERR.replace("179786.95", "180000.00")])
        result = run_stress_ng_cpu(
            workers=18,
            iterations=2,
            runner=lambda _: ("", next(outs)),
        )
        bps = result["bogo_ops_per_second"]
        self.assertEqual(bps["n"], 2)
        self.assertAlmostEqual(bps["max"], 180000.00)


class ScalarNativeTests(unittest.TestCase):
    def test_parse_three_kernels(self):
        kernels = parse_scalar_output(_SCALAR_STDOUT)
        self.assertEqual(set(kernels.keys()), {"int64_add", "fp64_fma", "neon_fp32x4_fma"})
        self.assertAlmostEqual(kernels["int64_add"]["ops_per_second"], 9.524e9, delta=1e6)

    def test_run_aggregates(self):
        outs = iter([_SCALAR_STDOUT, _SCALAR_STDOUT.replace("9.524e+09", "9.700e+09")])
        result = run_scalar(
            binary=Path("/fake"),
            iterations=2,
            runner=lambda _: next(outs),
        )
        self.assertIn("int64_add", result)
        self.assertEqual(result["int64_add"]["n"], 2)

    def test_parse_raises_on_empty(self):
        with self.assertRaises(ValueError):
            parse_scalar_output("no json here")
