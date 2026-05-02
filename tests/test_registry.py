from system_benchmarking.runner.registry import available_benchmarks, select_benchmarks


import unittest


class BenchmarkRegistryTests(unittest.TestCase):
    def test_available_benchmarks_include_initial_families(self):
        names = [benchmark.name for benchmark in available_benchmarks()]

        self.assertIn("cpu.scalar_integer", names)
        self.assertIn("memory.bandwidth", names)
        self.assertIn("gpu.metal_capabilities", names)

    def test_select_benchmarks_filters_by_family(self):
        selected = select_benchmarks(family="cpu")

        self.assertEqual([benchmark.family for benchmark in selected], ["cpu"])
