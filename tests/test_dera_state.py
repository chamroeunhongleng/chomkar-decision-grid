"""Unit tests for tools/dera_state.py (the resume engine).

Run:  py -m unittest discover tests
      py -m pytest tests/test_dera_state.py
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import dera_state as ds  # noqa: E402


class TestHashInputs(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(ds.hash_inputs({"a": 1}, [2, 3]), ds.hash_inputs({"a": 1}, [2, 3]))

    def test_order_and_delimiter_matter(self):
        self.assertNotEqual(ds.hash_inputs("a", "b"), ds.hash_inputs("ab"))
        self.assertNotEqual(ds.hash_inputs("a", "b"), ds.hash_inputs("b", "a"))

    def test_key_order_irrelevant(self):
        # sort_keys=True → dict key order does not change the hash
        self.assertEqual(ds.hash_inputs({"a": 1, "b": 2}), ds.hash_inputs({"b": 2, "a": 1}))


class TestResumeLogic(unittest.TestCase):
    def test_fresh_stage_runs(self):
        state = ds.new_state("order_test")
        self.assertTrue(ds.should_run(state, "detect", "h1"))

    def test_done_same_hash_skips(self):
        state = ds.new_state("order_test")
        ds.mark_done(state, "detect", "detect.json", "h1", now="2026-01-01T00:00:00+00:00")
        self.assertFalse(ds.should_run(state, "detect", "h1"))  # skip → resume

    def test_done_changed_hash_reruns(self):
        state = ds.new_state("order_test")
        ds.mark_done(state, "detect", "detect.json", "h1", now="2026-01-01T00:00:00+00:00")
        self.assertTrue(ds.should_run(state, "detect", "h2"))  # input changed → recompute

    def test_reset_forces_rerun(self):
        state = ds.new_state("order_test")
        ds.mark_done(state, "evaluate", "evaluate.json", "h1")
        ds.reset_stage(state, "evaluate")
        self.assertTrue(ds.should_run(state, "evaluate", "h1"))

    def test_unknown_stage_raises(self):
        state = ds.new_state("order_test")
        with self.assertRaises(ValueError):
            ds.should_run(state, "not_a_stage", "h1")


class TestPersistence(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as root:
            state = ds.new_state("order_001")
            ds.mark_done(state, "detect", "detect.json", "abc", now="2026-01-01T00:00:00+00:00")
            ds.save_state(state, root=root, now="2026-01-01T00:00:00+00:00")

            loaded = ds.load_state("order_001", root=root)
            self.assertEqual(loaded["order_id"], "order_001")
            self.assertEqual(loaded["stages"]["detect"]["status"], "done")
            self.assertEqual(loaded["stages"]["detect"]["input_hash"], "abc")
            self.assertEqual(loaded["stages"]["evaluate"]["status"], "todo")
            self.assertEqual(loaded["updated"], "2026-01-01T00:00:00+00:00")

    def test_load_missing_returns_fresh(self):
        with tempfile.TemporaryDirectory() as root:
            state = ds.load_state("never_saved", root=root)
            self.assertEqual(state["order_id"], "never_saved")
            self.assertTrue(all(st["status"] == "todo" for st in state["stages"].values()))


if __name__ == "__main__":
    unittest.main()
