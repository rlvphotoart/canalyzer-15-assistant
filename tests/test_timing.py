import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_timing", ROOT / "skills/canalyzer-15-assistant/scripts/check_timing.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def analyze(rows, window="0.5"):
    return checker.analyze([(Decimal(t), a, b) for t, a, b in rows], Decimal(window))


class TimingTests(unittest.TestCase):
    def test_published_fixture(self):
        report = checker.analyze(checker.read_samples(ROOT / "examples/timing-check.csv"), Decimal("0.5"))
        self.assertEqual(report["counts"], {"Pass": 2, "Fail": 1, "Inconclusive": 1})
        self.assertEqual([Decimal(c["delay_ms"]) if c["delay_ms"] else None for c in report["checks"]],
                         [320, 500, 600, None])
        self.assertEqual(report["trigger_count"], 4)
        self.assertEqual(report["conclusive_count"], 3)

    def test_exact_decimal_deadline(self):
        report = analyze([("0", 0, 0), ("0.1", 1, 0), ("0.6", 1, 1)])
        self.assertEqual(report["overall"], "Pass")
        self.assertEqual(Decimal(report["checks"][0]["delay_ms"]), 500)

    def test_one_nanosecond_late(self):
        report = analyze([("0", 0, 0), ("0.1", 1, 0), ("0.600000001", 1, 1)])
        self.assertEqual(report["overall"], "Fail")

    def test_missing_response_at_and_before_deadline(self):
        for end, expected in [("1.5", "Fail"), ("1.499999999", "Inconclusive")]:
            with self.subTest(end=end):
                self.assertEqual(analyze([("0", 0, 0), ("1", 1, 0), (end, 1, 0)])["overall"], expected)

    def test_initial_high_is_not_an_edge(self):
        report = analyze([("0", 1, 0), ("1", 1, 1)])
        self.assertEqual(report["trigger_count"], 0)
        self.assertEqual(report["overall"], "Inconclusive")
        self.assertTrue(report["initial_trigger_high"])

    def test_response_already_high_requires_new_rise(self):
        report = analyze([("0", 0, 1), ("1", 1, 1), ("1.5", 1, 1)])
        self.assertEqual(report["overall"], "Fail")
        report = analyze([("0", 0, 1), ("1", 1, 1), ("1.1", 1, 0), ("1.2", 1, 1)])
        self.assertEqual(report["overall"], "Pass")

    def test_simultaneous_rises(self):
        report = analyze([("0", 0, 0), ("1", 1, 1)])
        self.assertEqual(report["overall"], "Pass")
        self.assertEqual(Decimal(report["checks"][0]["delay_ms"]), 0)

    def test_overlapping_windows_rejected_even_at_deadline(self):
        for retrigger in ("1.4", "1.5"):
            with self.subTest(retrigger=retrigger), self.assertRaises(ValueError):
                analyze([("0", 0, 0), ("1", 1, 0), ("1.1", 0, 0), (retrigger, 1, 0)])

    def test_response_at_next_trigger_belongs_to_next_window(self):
        report = analyze([("0", 0, 0), ("1", 1, 0), ("1.8", 0, 0), ("2", 1, 1)])
        self.assertEqual([c["result"] for c in report["checks"]], ["Fail", "Pass"])
        self.assertIsNone(report["checks"][0]["response_s"])

    def test_first_response_and_repeated_high_samples(self):
        report = analyze([("0", 0, 0), ("1", 1, 0), ("1.1", 1, 1),
                          ("1.2", 1, 0), ("1.3", 1, 1), ("1.4", 1, 1)])
        self.assertEqual(report["trigger_count"], 1)
        self.assertEqual(Decimal(report["checks"][0]["delay_ms"]), 100)

    def run_csv(self, content, window="500"):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.csv"
            path.write_text(content, encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                status = checker.main([str(path), "--window-ms", window, "--complete-event-export"])
            return status, out.getvalue(), err.getvalue()

    def test_invalid_inputs_never_emit_verdict(self):
        for content in [
            "time_s,trigger,response\n", "time_s,trigger,response\n0,0,0\n",
            "time_s,trigger,response\n0,0,0\n0,1,1\n",
            "time_s,trigger,response\n1,0,0\n0,1,1\n",
            "time_s,trigger,response\n-1,0,0\n0,1,1\n",
            "time_s,trigger,response\n0,0,0\nNaN,1,1\n",
            "time_s,trigger,response\n0,0,0\nInfinity,1,1\n",
            "time_s,trigger,response\n0,0,0\n1,2,1\n",
            "time_s,trigger,response\n0,0,0\n1,1,\n",
            "time_s,trigger,response\n0,0,0\n1,1\n",
            "time_s,trigger,response\n0,0,0\n1,1,1,extra\n",
            "time_ms,trigger,response\n0,0,0\n1000,1,1\n",
            "time_s,trigger,response\n0,0,0\n0.0000000001,1,1\n",
            'time_s,trigger,response\n0,0,0\n1,1,"1\n',
        ]:
            with self.subTest(content=content):
                status, out, err = self.run_csv(content)
                self.assertEqual(status, 3)
                self.assertEqual(out, "")
                self.assertIn("Input error:", err)

    def test_invalid_window(self):
        for window in ("0", "-1", "NaN", "Infinity", "nonsense", "0e999999", "1e-10"):
            with self.subTest(window=window):
                self.assertEqual(self.run_csv("time_s,trigger,response\n0,0,0\n1,1,1\n", window)[0], 3)

    def test_cli_status_and_bom(self):
        for final, status, overall in [("1,1,1", 0, "Pass"), ("1.5,1,0", 1, "Fail"),
                                       ("1.2,1,0", 2, "Inconclusive")]:
            content = "\ufefftime_s,trigger,response\n0,0,0\n"
            if status:
                content += "1,1,0\n"
            actual, out, err = self.run_csv(content + final + "\n")
            self.assertEqual(actual, status)
            self.assertEqual(json.loads(out)["overall"], overall)
            self.assertEqual(err, "")

    def test_completeness_assertion_required(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            checker.main(["unused.csv", "--window-ms", "500"])
        self.assertEqual(raised.exception.code, 2)

    def test_missing_file_and_invalid_encoding(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.csv"
            for exists in (False, True):
                if exists:
                    path.write_bytes(b"\xff\xfe\x00")
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    status = checker.main([str(path), "--window-ms", "500", "--complete-event-export"])
                self.assertEqual(status, 3)
                self.assertEqual(out.getvalue(), "")
                self.assertIn("Input error:", err.getvalue())


if __name__ == "__main__":
    unittest.main()
