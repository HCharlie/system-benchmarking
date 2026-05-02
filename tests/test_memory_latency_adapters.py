from __future__ import annotations

import unittest
from pathlib import Path

from system_benchmarking.adapters.pointer_chase import parse_pointer_chase, run_pointer_chase
from system_benchmarking.adapters.tinymembench import parse_tinymembench, run_tinymembench


_TINYMEMBENCH_OUTPUT = """\
==========================================================================
== Memory bandwidth tests
==========================================================================

 C copy backwards                                     :   12345.6 MB/s
 C copy backwards (32 byte blocks)                    :   12000.0 MB/s
 C copy                                               :   13000.0 MB/s
 C 2-pass copy                                        :   11000.0 MB/s

==========================================================================
== Memory latency test
==========================================================================

block size : single random read / dual random read
      1kB :    1.2 ns          /     1.4 ns
      4kB :    1.5 ns          /     1.6 ns
     16kB :    3.2 ns          /     3.4 ns
    64kB :    4.0 ns          /     4.1 ns
   256kB :    8.0 ns          /     8.5 ns
     1MB :   18.0 ns          /    19.0 ns
    16MB :  120.0 ns          /   123.0 ns
"""


_POINTER_CHASE_OUTPUT = """\
{"bytes":4096, "ns_per_access":1.05, "iterations":40000000}
{"bytes":262144, "ns_per_access":4.20, "iterations":40000000}
{"bytes":67108864, "ns_per_access":18.0, "iterations":40000000}
{"bytes":1073741824, "ns_per_access":110.0, "iterations":40000000}
"""


class TinymembenchTests(unittest.TestCase):
    def test_parse_extracts_bandwidth_rows(self):
        result = parse_tinymembench(_TINYMEMBENCH_OUTPUT)
        names = [b.name for b in result["bandwidth"]]
        self.assertIn("C copy", names)

    def test_parse_extracts_latency_rows(self):
        result = parse_tinymembench(_TINYMEMBENCH_OUTPUT)
        bytes_seen = [p.bytes for p in result["latency"]]
        self.assertIn(4 * 1024, bytes_seen)
        self.assertIn(16 * 1024 * 1024, bytes_seen)

    def test_run_aggregates_bandwidth(self):
        outputs = iter([_TINYMEMBENCH_OUTPUT, _TINYMEMBENCH_OUTPUT.replace("12345.6", "12500.0")])
        result = run_tinymembench(Path("/fake"), iterations=2, runner=lambda _: next(outputs))
        cb = result["bandwidth"]["C copy backwards"]
        self.assertEqual(cb["n"], 2)
        self.assertGreater(cb["median_mbps"], 12000.0)


class PointerChaseTests(unittest.TestCase):
    def test_parse_collects_all_points(self):
        points = parse_pointer_chase(_POINTER_CHASE_OUTPUT)
        self.assertEqual(len(points), 4)
        self.assertEqual(points[-1]["bytes"], 1073741824)
        self.assertAlmostEqual(points[-1]["ns_per_access"], 110.0)

    def test_run_returns_curve(self):
        result = run_pointer_chase(
            Path("/fake"),
            iterations=1,
            runner=lambda _: _POINTER_CHASE_OUTPUT,
        )
        self.assertEqual(len(result["latency_curve"]), 4)

    def test_parse_raises_on_garbage(self):
        with self.assertRaises(ValueError):
            parse_pointer_chase("nothing")
