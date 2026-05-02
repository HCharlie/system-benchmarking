from __future__ import annotations

import json
import unittest

from system_benchmarking.adapters.metal_probe import parse_displays_json, probe_metal


_DISPLAYS_JSON = json.dumps(
    {
        "SPDisplaysDataType": [
            {
                "_name": "Apple M5 Max",
                "sppci_model": "Apple M5 Max",
                "sppci_cores": "40",
                "spdisplays_mtlgpufamilysupport": "spdisplays_metal4",
                "sppci_bus": "spdisplays_builtin",
                "spdisplays_vendor": "sppci_vendor_Apple",
            }
        ]
    }
)


class MetalProbeTests(unittest.TestCase):
    def test_parse_extracts_capability_fields(self):
        result = parse_displays_json(_DISPLAYS_JSON)
        self.assertTrue(result["available"])
        self.assertEqual(result["name"], "Apple M5 Max")
        self.assertEqual(result["cores"], 40)
        self.assertEqual(result["metal_family"], "spdisplays_metal4")

    def test_parse_marks_unavailable_when_empty(self):
        result = parse_displays_json(json.dumps({"SPDisplaysDataType": []}))
        self.assertFalse(result["available"])

    def test_probe_uses_runner(self):
        captured: list[list[str]] = []
        def fake(command):
            captured.append(list(command))
            return _DISPLAYS_JSON
        result = probe_metal(runner=fake)
        self.assertTrue(result["available"])
        self.assertIn("system_profiler", captured[0])
