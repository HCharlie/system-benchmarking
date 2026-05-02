from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from system_benchmarking.collectors.apple.device_info import (
    collect_apple_device_info,
    collect_apple_device_manifest,
    slugify,
)


_FAKE_SYSTEM_PROFILER = {
    "SPHardwareDataType": [
        {
            "chip_type": "Apple M5 Max",
            "machine_model": "Mac17,7",
            "machine_name": "MacBook Pro",
            "physical_memory": "64 GB",
        }
    ],
    "SPSoftwareDataType": [
        {
            "kernel_version": "Darwin 25.4.0",
            "os_version": "macOS 26.4.1 (25E253)",
        }
    ],
    "SPDisplaysDataType": [
        {
            "_name": "Apple M5 Max",
            "sppci_model": "Apple M5 Max",
            "sppci_cores": "40",
            "spdisplays_mtlgpufamilysupport": "spdisplays_metal4",
        }
    ],
}

_FAKE_SYSCTL = """\
hw.ncpu: 18
hw.physicalcpu: 18
hw.logicalcpu: 18
hw.perflevel0.physicalcpu: 12
hw.perflevel0.logicalcpu: 12
hw.perflevel1.physicalcpu: 6
hw.perflevel1.logicalcpu: 6
hw.memsize: 68719476736
hw.pagesize: 16384
hw.cachelinesize: 128
hw.l1icachesize: 131072
hw.l1dcachesize: 65536
hw.l2cachesize: 8388608
machdep.cpu.brand_string: Apple M5 Max
kern.osversion: 25E253
kern.version: Darwin Kernel Version 25.4.0
"""


def _fake_runner() -> callable:
    def run(command: tuple[str, ...]) -> str:
        if command[0] == "system_profiler":
            return json.dumps(_FAKE_SYSTEM_PROFILER)
        if command[0] == "sysctl":
            if command[1:] == ("-n", "machdep.cpu.brand_string"):
                return "Apple M5 Max\n"
            if command[1:] == ("-n", "hw.memsize"):
                return "68719476736\n"
            return _FAKE_SYSCTL
        if command[0] == "uname":
            return "arm64\n"
        raise AssertionError(f"unexpected command: {command}")

    return run


class AppleDeviceInfoTests(unittest.TestCase):
    def test_collect_apple_device_info_parses_command_output(self):
        device = collect_apple_device_info(run_command=_fake_runner(), model_name="MacBook Pro")
        self.assertEqual(device.vendor, "apple")
        self.assertEqual(device.model, "MacBook Pro")
        self.assertEqual(device.chip, "Apple M5 Max")
        self.assertEqual(device.architecture, "arm64")
        self.assertEqual(device.memory_gb, 64)


class AppleDeviceManifestTests(unittest.TestCase):
    def _build(self):
        fixed_now = datetime(2026, 5, 3, 10, 15, 0, tzinfo=timezone.utc)
        return collect_apple_device_manifest(
            run_command=_fake_runner(),
            now=lambda: fixed_now,
        )

    def test_manifest_top_level_fields(self):
        manifest = self._build()
        self.assertEqual(manifest.schema_version, "1")
        self.assertEqual(manifest.captured_at, "2026-05-03T10:15:00Z")
        self.assertEqual(manifest.vendor, "apple")
        self.assertEqual(manifest.model_id, "Mac17,7")
        self.assertEqual(manifest.marketing_name, "MacBook Pro")
        self.assertEqual(manifest.chip, "Apple M5 Max")
        self.assertEqual(manifest.architecture, "arm64")
        self.assertEqual(manifest.memory_bytes, 68719476736)
        self.assertEqual(manifest.slug, "macbook-pro-apple-m5-max")

    def test_manifest_cpu_topology(self):
        cpu = self._build().cpu
        self.assertEqual(cpu.total_cores, 18)
        self.assertEqual(cpu.performance_cores, 12)
        self.assertEqual(cpu.efficiency_cores, 6)
        self.assertEqual(cpu.logical_cores, 18)

    def test_manifest_cache_sizes(self):
        cache = self._build().cache
        self.assertEqual(cache.l1d_bytes, 65536)
        self.assertEqual(cache.l1i_bytes, 131072)
        self.assertEqual(cache.l2_bytes, 8388608)
        self.assertEqual(cache.line_bytes, 128)
        self.assertEqual(cache.page_bytes, 16384)

    def test_manifest_gpu(self):
        gpu = self._build().gpu
        self.assertIsNotNone(gpu)
        self.assertEqual(gpu.name, "Apple M5 Max")
        self.assertEqual(gpu.cores, 40)
        self.assertEqual(gpu.metal_family, "spdisplays_metal4")

    def test_manifest_os(self):
        os_info = self._build().os
        self.assertEqual(os_info.name, "macOS")
        self.assertEqual(os_info.version, "26.4.1")
        self.assertEqual(os_info.build, "25E253")
        self.assertEqual(os_info.kernel, "Darwin 25.4.0")

    def test_manifest_raw_excluded_by_default(self):
        manifest = self._build()
        self.assertEqual(manifest.raw, {})

    def test_manifest_raw_included_on_request(self):
        fixed_now = datetime(2026, 5, 3, tzinfo=timezone.utc)
        manifest = collect_apple_device_manifest(
            run_command=_fake_runner(),
            now=lambda: fixed_now,
            include_raw=True,
        )
        self.assertIn("system_profiler", manifest.raw)
        self.assertIn("sysctl", manifest.raw)

    def test_manifest_serializes_to_json(self):
        manifest = self._build()
        payload = json.dumps(manifest.to_dict())
        round_tripped = json.loads(payload)
        self.assertEqual(round_tripped["chip"], "Apple M5 Max")


class SlugifyTests(unittest.TestCase):
    def test_lowercases_and_replaces_punctuation(self):
        self.assertEqual(slugify("MacBook Pro", "Apple M5 Max"), "macbook-pro-apple-m5-max")

    def test_collapses_repeated_separators(self):
        self.assertEqual(slugify("Mac  Mini", "M2"), "mac-mini-m2")

    def test_falls_back_when_empty(self):
        self.assertEqual(slugify("", ""), "unknown")
