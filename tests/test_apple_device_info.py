from system_benchmarking.collectors.apple.device_info import collect_apple_device_info


import unittest


class AppleDeviceInfoTests(unittest.TestCase):
    def test_collect_apple_device_info_parses_command_output(self):
        outputs = {
            ("sysctl", "-n", "machdep.cpu.brand_string"): "Apple M3 Max\n",
            ("sysctl", "-n", "hw.memsize"): "38654705664\n",
            ("uname", "-m"): "arm64\n",
        }

        def fake_run(command: tuple[str, ...]) -> str:
            return outputs[command]

        device = collect_apple_device_info(run_command=fake_run, model_name="MacBook Pro")

        self.assertEqual(device.vendor, "apple")
        self.assertEqual(device.model, "MacBook Pro")
        self.assertEqual(device.chip, "Apple M3 Max")
        self.assertEqual(device.architecture, "arm64")
        self.assertEqual(device.memory_gb, 36)
