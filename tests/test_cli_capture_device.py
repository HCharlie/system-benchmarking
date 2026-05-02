from __future__ import annotations

import io
import json
import subprocess
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from system_benchmarking.cli import main


_FAKE_OUTPUTS = {
    ("uname", "-m"): "arm64\n",
    (
        "system_profiler",
        "SPHardwareDataType",
        "SPSoftwareDataType",
        "SPDisplaysDataType",
        "-json",
    ): json.dumps(
        {
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
                    "sppci_model": "Apple M5 Max",
                    "sppci_cores": "40",
                    "spdisplays_mtlgpufamilysupport": "spdisplays_metal4",
                }
            ],
        }
    ),
}

_FAKE_SYSCTL_BLOCK = """\
hw.ncpu: 18
hw.physicalcpu: 18
hw.logicalcpu: 18
hw.perflevel0.physicalcpu: 12
hw.perflevel1.physicalcpu: 6
hw.memsize: 68719476736
hw.pagesize: 16384
hw.cachelinesize: 128
hw.l1icachesize: 131072
hw.l1dcachesize: 65536
hw.l2cachesize: 8388608
machdep.cpu.brand_string: Apple M5 Max
kern.osversion: 25E253
"""


def _fake_check_output(command, text=False, **_):
    if command[0] == "sysctl" and len(command) > 2:
        return _FAKE_SYSCTL_BLOCK
    return _FAKE_OUTPUTS[tuple(command)]


class CaptureDeviceCliTests(unittest.TestCase):
    def test_capture_device_writes_file_to_devices_dir(self):
        with TemporaryDirectory() as tmp, patch.object(subprocess, "check_output", side_effect=_fake_check_output):
            devices_dir = Path(tmp) / "devices"
            exit_code = main(["capture-device", "--devices-dir", str(devices_dir)])
            self.assertEqual(exit_code, 0)

            written = list(devices_dir.rglob("*.json"))
            self.assertEqual(len(written), 1)
            self.assertEqual(written[0].parent.name, "apple")

            payload = json.loads(written[0].read_text())
            self.assertEqual(payload["chip"], "Apple M5 Max")
            self.assertEqual(payload["cpu"]["performance_cores"], 12)
            self.assertEqual(payload["cpu"]["efficiency_cores"], 6)
            self.assertEqual(payload["raw"], {})

    def test_capture_device_stdout_does_not_write(self):
        with TemporaryDirectory() as tmp, patch.object(subprocess, "check_output", side_effect=_fake_check_output):
            devices_dir = Path(tmp) / "devices"
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = main(["capture-device", "--devices-dir", str(devices_dir), "--stdout"])

            self.assertEqual(exit_code, 0)
            self.assertFalse(devices_dir.exists())
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["vendor"], "apple")

    def test_capture_device_raw_includes_payloads(self):
        with TemporaryDirectory() as tmp, patch.object(subprocess, "check_output", side_effect=_fake_check_output):
            output_path = Path(tmp) / "manifest.json"
            exit_code = main([
                "capture-device",
                "--output", str(output_path),
                "--raw",
            ])
            self.assertEqual(exit_code, 0)
            payload = json.loads(output_path.read_text())
            self.assertIn("system_profiler", payload["raw"])
            self.assertIn("sysctl", payload["raw"])
