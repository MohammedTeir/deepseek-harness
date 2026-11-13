"""Runner-output regressions; these do not exercise Android or Node."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("device_runner", Path(__file__).parents[1] / "scripts/test_device.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class InstrumentationOutputTest(unittest.TestCase):
    def test_requires_complete_expected_execution(self):
        self.assertTrue(runner.instrumentation_passed("OK (2 tests)\nINSTRUMENTATION_CODE: -1\n", 2))
        self.assertTrue(runner.instrumentation_passed("OK (1 test)\nINSTRUMENTATION_CODE: -1\n", 1))
        for output in ["", "OK (0 tests)\nINSTRUMENTATION_CODE: -1\n",
                       "OK (2 tests)\n", "OK (2 tests)\nINSTRUMENTATION_CODE: 0\n",
                       "FAILURES!!!\nINSTRUMENTATION_CODE: -1\n",
                       "OK (2 tests)\nINSTRUMENTATION_STATUS_CODE: -2\nINSTRUMENTATION_CODE: -1\n",
                       "OK (2 tests)\nINSTRUMENTATION_RESULT: shortMsg=Process crashed.\nINSTRUMENTATION_CODE: -1\n"]:
            with self.subTest(output=output):
                self.assertFalse(runner.instrumentation_passed(output, 2))


if __name__ == "__main__":
    unittest.main()
