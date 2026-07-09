"""Unit tests for tools/audit_recommendation.py (M11 auditor gate).

Exercises the pure check functions with in-memory artifacts/data.

Run:  py -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import audit_recommendation as au  # noqa: E402


FARMERS = [
    {"farmer_id": "F1", "declared_crop": "bok_choy", "declared_qty_kg": "600", "quality_grade": "A",
     "ask_price_per_kg_khr": "3000", "province": "Kandal", "commune": "Ta Khmau", "reliability_score": "0.9"},
    {"farmer_id": "F2", "declared_crop": "bok_choy", "declared_qty_kg": "500", "quality_grade": "B",
     "ask_price_per_kg_khr": "3200", "province": "Takeo", "commune": "Doun Kaev", "reliability_score": "0.8"},
]
ORDER = {"order_id": "order_x", "commodity": "bok_choy", "quantity_kg": "1000", "quality_required": "B",
         "max_price_per_kg_khr": "3800", "delivery_province": "Kandal", "delivery_commune": "Ta Khmau",
         "delivery_date": "2026-07-22", "perishability_days": "3"}


def artifact(payout, allocs, blended=3400, margin=2.0, variant="cheapest_first"):
    return {"status": "RECOMMENDATION - pending human approval",
            "recommendation": {"variant": variant, "farmers": allocs, "farmer_payout_khr": payout,
                               "blended_price_per_kg_khr": blended, "spoilage_margin_days": margin,
                               "total_kg": sum(a["allocated_kg"] for a in allocs)}}


def alloc(fid, kg, ask):
    return {"farmer_id": fid, "allocated_kg": kg, "ask_price_per_kg_khr": ask}


# evaluate.json with the same winner variant so grid_reproduces passes for a valid case
def evaluate_for(variant="cheapest_first"):
    return {"candidates": [{
        "variant": variant, "coverage": 1.0, "feasible": True, "n_farmers": 2,
        "allocations": [{"reliability_score": 0.9}],
        "factors": {"coverage": 1.0, "headroom_per_kg_khr": 400, "route_risk": 0.2, "spoilage_margin_days": 2.0},
        "pricing": {"blended_price_per_kg_khr": 3400, "headroom_per_kg_khr": 400},
        "route": {"route_risk": 0.2, "spoilage_margin_days": 2.0}}]}


class TestAuditRecommendation(unittest.TestCase):
    def _by_name(self, checks):
        return {c["check"]: c["passed"] for c in checks}

    def test_valid_passes(self):
        allocs = [alloc("F1", 600, 3000), alloc("F2", 400, 3200)]
        payout = 600 * 3000 + 400 * 3200  # 3,080,000
        checks = au.audit_recommendation(artifact(payout, allocs), FARMERS, ORDER, evaluate_for())
        self.assertTrue(all(c["passed"] for c in checks), self._by_name(checks))

    def test_tampered_payout_fails(self):
        allocs = [alloc("F1", 600, 3000), alloc("F2", 400, 3200)]
        checks = au.audit_recommendation(artifact(9_999_999, allocs), FARMERS, ORDER, evaluate_for())
        self.assertFalse(self._by_name(checks)["zero_cut"])

    def test_wrong_ask_fails_zero_cut(self):
        # artifact claims a cheaper ask than the CSV -> asks_match False
        allocs = [alloc("F1", 600, 2000), alloc("F2", 400, 3200)]
        payout = 600 * 2000 + 400 * 3200
        checks = au.audit_recommendation(artifact(payout, allocs), FARMERS, ORDER, evaluate_for())
        self.assertFalse(self._by_name(checks)["zero_cut"])

    def test_overallocation_fails(self):
        allocs = [alloc("F1", 900, 3000), alloc("F2", 100, 3200)]  # F1 declared only 600
        payout = 900 * 3000 + 100 * 3200
        checks = au.audit_recommendation(artifact(payout, allocs), FARMERS, ORDER, evaluate_for())
        self.assertFalse(self._by_name(checks)["no_overallocation"])

    def test_underfill_fails(self):
        allocs = [alloc("F1", 600, 3000), alloc("F2", 300, 3200)]  # 900 != 1000
        payout = 600 * 3000 + 300 * 3200
        checks = au.audit_recommendation(artifact(payout, allocs), FARMERS, ORDER, evaluate_for())
        self.assertFalse(self._by_name(checks)["volume_filled"])

    def test_over_cap_fails(self):
        allocs = [alloc("F1", 600, 3000), alloc("F2", 400, 3200)]
        payout = 600 * 3000 + 400 * 3200
        art = artifact(payout, allocs, blended=4200)  # > cap 3800
        checks = au.audit_recommendation(art, FARMERS, ORDER, evaluate_for())
        self.assertFalse(self._by_name(checks)["within_cap"])


class TestAuditBlock(unittest.TestCase):
    def test_blocked_justified(self):
        big_order = dict(ORDER, quantity_kg="3000")  # supply 1100 < 3000
        art = {"status": "BLOCKED - pending human review", "recommendation": None}
        checks = au.audit_block(art, FARMERS, big_order, {})
        self.assertTrue(checks[0]["passed"])

    def test_blocked_unjustified_flags(self):
        # order fillable (1000 <= 1100) but artifact claims blocked -> audit should FAIL the justification
        art = {"status": "BLOCKED - pending human review", "recommendation": None}
        checks = au.audit_block(art, FARMERS, ORDER, {})
        self.assertFalse(checks[0]["passed"])


if __name__ == "__main__":
    unittest.main()
