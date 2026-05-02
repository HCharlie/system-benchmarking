from __future__ import annotations

import unittest

from system_benchmarking.adapters.powermetrics import parse_powermetrics, run_powermetrics


_POWERMETRICS_OUTPUT = """\
Machine model: MacBookPro
OS version: 26F22

**** Sampled system activity (Sun May  3 10:00:00 2026 UTC) (1000.04 ms elapsed) ****

CPU Power: 5400.12 mW
GPU Power: 2300.55 mW
ANE Power: 0 mW
Combined Power (CPU + GPU + ANE): 7700.67 mW
CPU die temperature: 65.4 C
GPU die temperature: 68.1 C
Fan: 1800.0 rpm

**** Sampled system activity (Sun May  3 10:00:01 2026 UTC) (1000.02 ms elapsed) ****

CPU Power: 5800.10 mW
GPU Power: 2400.10 mW
ANE Power: 0 mW
Combined Power (CPU + GPU + ANE): 8200.20 mW
CPU die temperature: 67.8 C
GPU die temperature: 70.0 C
Fan: 2000.0 rpm
"""


class PowermetricsTests(unittest.TestCase):
    def test_parse_extracts_two_samples(self):
        samples = parse_powermetrics(_POWERMETRICS_OUTPUT)
        self.assertEqual(len(samples), 2)
        self.assertAlmostEqual(samples[0]["package_power_mw"], 7700.67)
        self.assertAlmostEqual(samples[1]["cpu_die_temperature_c"], 67.8)
        self.assertAlmostEqual(samples[0]["fan_rpm"], 1800.0)

    def test_parse_handles_missing_fields(self):
        snippet = "**** Sampled system activity ****\nCPU Power: 100 mW\n"
        samples = parse_powermetrics(snippet)
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]["cpu_power_mw"], 100.0)
        self.assertIsNone(samples[0]["gpu_power_mw"])

    def test_run_command_includes_sudo_when_requested(self):
        captured: list[list[str]] = []
        def fake(command):
            captured.append(list(command))
            return _POWERMETRICS_OUTPUT
        run_powermetrics(samples=2, interval_ms=500, sudo=True, runner=fake)
        cmd = captured[0]
        self.assertEqual(cmd[0], "sudo")
        self.assertIn("powermetrics", cmd)
        self.assertIn("--samplers", cmd)
        self.assertIn("-n", cmd)
        self.assertIn("2", cmd)
