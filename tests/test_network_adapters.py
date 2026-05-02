from __future__ import annotations

import json
import unittest

from system_benchmarking.adapters.iperf3 import parse_iperf3_json, run_iperf3_client
from system_benchmarking.adapters.ping import parse_ping_summary, run_ping


_IPERF3_JSON = json.dumps(
    {
        "start": {
            "version": "iperf 3.16",
            "test_start": {"protocol": "TCP"},
        },
        "end": {
            "sum_sent": {"bits_per_second": 9.4e9, "bytes": int(35.2e9), "seconds": 30.0, "retransmits": 0},
            "sum_received": {"bits_per_second": 9.4e9, "bytes": int(35.2e9), "seconds": 30.0, "retransmits": 0},
            "cpu_utilization_percent": {"host_total": 12.3, "remote_total": 8.7},
        },
    }
)


_PING_OUTPUT_MAC = """\
PING 1.1.1.1 (1.1.1.1): 56 data bytes
64 bytes from 1.1.1.1: icmp_seq=0 ttl=58 time=8.123 ms

--- 1.1.1.1 ping statistics ---
100 packets transmitted, 100 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 7.123/8.456/12.000/0.987 ms
"""

_PING_OUTPUT_LINUX = """\
PING 1.1.1.1 (1.1.1.1) 56(84) bytes of data.
64 bytes from 1.1.1.1: icmp_seq=1 ttl=58 time=8.0 ms

--- 1.1.1.1 ping statistics ---
100 packets transmitted, 99 received, 1% packet loss, time 99000ms
rtt min/avg/max/mdev = 7.123/8.456/12.000/0.987 ms
"""


class Iperf3Tests(unittest.TestCase):
    def test_parse_extracts_throughput(self):
        parsed = parse_iperf3_json(_IPERF3_JSON)
        self.assertEqual(parsed["protocol"], "TCP")
        self.assertEqual(parsed["sender"]["bits_per_second"], 9.4e9)
        self.assertEqual(parsed["receiver"]["seconds"], 30.0)

    def test_run_builds_command_with_target(self):
        captured: list[list[str]] = []

        def fake(command):
            captured.append(list(command))
            return _IPERF3_JSON

        run_iperf3_client(target="127.0.0.1", duration=10, runner=fake)
        cmd = captured[0]
        self.assertIn("-c", cmd)
        self.assertIn("127.0.0.1", cmd)
        self.assertIn("-t", cmd)
        self.assertIn("10", cmd)


class PingTests(unittest.TestCase):
    def test_parse_macos_summary(self):
        result = parse_ping_summary(_PING_OUTPUT_MAC)
        self.assertAlmostEqual(result["avg_ms"], 8.456)
        self.assertEqual(result["transmitted"], 100)
        self.assertEqual(result["received"], 100)
        self.assertEqual(result["loss_pct"], 0.0)

    def test_parse_linux_summary(self):
        result = parse_ping_summary(_PING_OUTPUT_LINUX)
        self.assertAlmostEqual(result["max_ms"], 12.0)
        self.assertEqual(result["transmitted"], 100)
        self.assertEqual(result["received"], 99)
        self.assertAlmostEqual(result["loss_pct"], 1.0)

    def test_run_invokes_ping_with_count(self):
        captured: list[list[str]] = []
        def fake(command):
            captured.append(list(command))
            return _PING_OUTPUT_MAC
        run_ping(target="1.1.1.1", count=50, runner=fake)
        cmd = captured[0]
        self.assertIn("-c", cmd)
        self.assertIn("50", cmd)
        self.assertIn("1.1.1.1", cmd)
