"""Unit tests for tools/calibrate_weights.py and tools/record_outcome.py (M12).

Run:  py -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import calibrate_weights as cw  # noqa: E402
import record_outcome as ro  # noqa: E402


def outcome(fc, fp, frt, ffr, shipped="true", on_time="true", spoil=3, sat=5, paid="true"):
    return {"f_coverage": fc, "f_price": fp, "f_route": frt, "f_freshness": ffr,
            "shipped": shipped, "delivered_on_time": on_time, "actual_spoilage_pct": spoil,
            "buyer_satisfaction": sat, "farmer_paid_full": paid}


class TestProposeWeights(unittest.TestCase):
    def test_insufficient_data(self):
        p = cw.propose_weights([outcome(1, 1, 1, 1)])
        self.assertTrue(p["insufficient"])
        self.assertEqual(p["proposed"], p["current"])  # unchanged

    def test_weights_sum_to_one(self):
        outs = [outcome(1, 0.7, 1.0, 1.0, sat=5, spoil=3),
                outcome(1, 1.0, 0.0, 0.5, on_time="false", sat=3, spoil=12),
                outcome(1, 0.5, 0.8, 0.9, sat=4, spoil=5)]
        p = cw.propose_weights(outs)
        self.assertAlmostEqual(sum(p["proposed"].values()), 1.0, places=3)

    def test_nudges_bounded(self):
        outs = [outcome(1, 0.7, 1.0, 1.0), outcome(1, 1.0, 0.0, 0.5, on_time="false", sat=2, spoil=20),
                outcome(1, 0.5, 0.8, 0.9)]
        p = cw.propose_weights(outs, step=0.05)
        for r in p["per_factor"]:
            self.assertLessEqual(abs(r["nudge"]), 0.05 + 1e-9)

    def test_route_up_price_down_when_route_predicts_success(self):
        # route high -> success high; price high -> success low
        outs = [outcome(1, 0.2, 1.0, 1.0, sat=5, spoil=2, on_time="true"),
                outcome(1, 1.0, 0.0, 0.2, sat=2, spoil=25, on_time="false"),
                outcome(1, 0.4, 0.7, 0.8, sat=4, spoil=6, on_time="true")]
        p = cw.propose_weights(outs)
        byf = {r["factor"]: r for r in p["per_factor"]}
        self.assertGreater(byf["route"]["corr_with_success"], 0)   # route predicts success
        self.assertLess(byf["price"]["corr_with_success"], 0)      # price anti-predicts
        # constant coverage -> zero correlation -> no nudge
        self.assertEqual(byf["coverage"]["nudge"], 0.0)

    def test_deterministic(self):
        outs = [outcome(1, 0.7, 1.0, 1.0), outcome(1, 1.0, 0.0, 0.5, sat=3), outcome(1, 0.5, 0.8, 0.9)]
        self.assertEqual(cw.propose_weights(outs), cw.propose_weights(outs))


class TestRecordOutcomeValidation(unittest.TestCase):
    def test_valid_row(self):
        self.assertEqual(ro.validate_row(outcome(1.0, 0.5, 0.8, 0.9)), [])

    def test_factor_out_of_range(self):
        errs = ro.validate_row(outcome(1.0, 1.5, 0.8, 0.9))
        self.assertTrue(any("f_price" in e for e in errs))

    def test_bad_satisfaction(self):
        errs = ro.validate_row(outcome(1.0, 0.5, 0.8, 0.9, sat=9))
        self.assertTrue(any("buyer_satisfaction" in e for e in errs))

    def test_bad_boolean(self):
        errs = ro.validate_row(outcome(1.0, 0.5, 0.8, 0.9, shipped="maybe"))
        self.assertTrue(any("shipped" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
