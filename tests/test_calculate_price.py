"""Unit tests for tools/calculate_price.py and tools/assemble_lots.py (Evaluate).

Critical invariant: 0% platform cut — farmer payout == Σ(ask × allocated_kg), always.

Run:  py -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import assemble_lots  # noqa: E402
import calculate_price as cp  # noqa: E402


def F(fid, qty, ask, grade="B", zone=("Kandal", "Ta Khmau"), rel=0.8):
    return {"farmer_id": fid, "province": zone[0], "commune": zone[1], "declared_crop": "bok_choy",
            "declared_qty_kg": str(qty), "quality_grade": grade, "reliability_score": str(rel),
            "ask_price_per_kg_khr": str(ask), "expected_harvest_date": "2026-07-18"}


ORDER = {"order_id": "order_x", "commodity": "bok_choy", "quantity_kg": "1000", "quality_required": "B",
         "max_price_per_kg_khr": "3800", "delivery_province": "Kandal", "delivery_commune": "Ta Khmau",
         "delivery_date": "2026-07-22", "perishability_days": "3", "penalty_per_day_khr": "200"}

# All farmers in the delivery zone -> transport cost 50/kg via the self route.
TRANSPORT = [{"from_zone": "Kandal:Ta Khmau", "to_zone": "Kandal:Ta Khmau",
              "distance_km": "0", "cost_per_kg_khr": "50"},
             {"from_zone": "Takeo:Doun Kaev", "to_zone": "Kandal:Ta Khmau",
              "distance_km": "60", "cost_per_kg_khr": "230"}]


class TestZeroCutInvariant(unittest.TestCase):
    def test_payout_equals_sum_of_asks(self):
        farmers = [F("F1", 600, 3000), F("F2", 500, 3200)]  # 600+400 allocated to fill 1000
        lot = assemble_lots.build_lot(ORDER, farmers, TRANSPORT, "cheapest_first")
        pr = cp.price_lot(lot, ORDER, TRANSPORT)
        expected = sum(a["ask_price_per_kg_khr"] * a["allocated_kg"] for a in lot["allocations"])
        self.assertEqual(pr["farmer_payout_khr"], expected)
        # F1 fully (600*3000) + F2 partial (400*3200)
        self.assertEqual(pr["farmer_payout_khr"], 600 * 3000 + 400 * 3200)

    def test_handling_and_spoilage_are_on_top_not_from_payout(self):
        farmers = [F("F1", 1000, 3000)]
        lot = assemble_lots.build_lot(ORDER, farmers, TRANSPORT, "cheapest_first")
        base = cp.price_lot(lot, ORDER, TRANSPORT, handling_fee=0, spoilage_pct=0)
        withfees = cp.price_lot(lot, ORDER, TRANSPORT, handling_fee=150, spoilage_pct=0.05)
        # payout identical regardless of fees; fees only raise total_cost
        self.assertEqual(base["farmer_payout_khr"], withfees["farmer_payout_khr"])
        self.assertEqual(withfees["handling_cost_khr"], 150 * 1000)
        self.assertEqual(withfees["spoilage_buffer_khr"], round(0.05 * withfees["farmer_payout_khr"]))
        self.assertGreater(withfees["total_cost_khr"], base["total_cost_khr"])


class TestCostMath(unittest.TestCase):
    def test_blended_and_headroom(self):
        farmers = [F("F1", 1000, 3000)]  # payout 3,000,000
        lot = assemble_lots.build_lot(ORDER, farmers, TRANSPORT, "cheapest_first")
        pr = cp.price_lot(lot, ORDER, TRANSPORT, handling_fee=150, spoilage_pct=0.05)
        # transport 50*1000=50,000 ; handling 150,000 ; spoilage 150,000 ; total 3,350,000
        self.assertEqual(pr["transport_cost_khr"], 50_000)
        self.assertEqual(pr["total_cost_khr"], 3_000_000 + 50_000 + 150_000 + 150_000)
        self.assertEqual(pr["blended_price_per_kg_khr"], 3350.0)
        self.assertEqual(pr["headroom_per_kg_khr"], 3800 - 3350.0)
        self.assertTrue(pr["feasible"])

    def test_over_cap_is_infeasible(self):
        low_cap = dict(ORDER, max_price_per_kg_khr="2000")
        farmers = [F("F1", 1000, 2600)]  # payout alone 2,600,000 -> blended > 2000
        lot = assemble_lots.build_lot(low_cap, farmers, TRANSPORT, "cheapest_first")
        pr = cp.price_lot(lot, low_cap, TRANSPORT)
        self.assertLess(pr["headroom_per_kg_khr"], 0)
        self.assertFalse(pr["feasible"])

    def test_usd_equivalent(self):
        farmers = [F("F1", 1000, 3000)]
        lot = assemble_lots.build_lot(ORDER, farmers, TRANSPORT, "cheapest_first")
        pr = cp.price_lot(lot, ORDER, TRANSPORT, handling_fee=0, spoilage_pct=0)
        self.assertEqual(pr["usd"]["farmer_payout"], round(3_000_000 / 4000, 2))


class TestAssembly(unittest.TestCase):
    def test_allocation_never_exceeds_declared(self):
        farmers = [F("F1", 300, 2900), F("F2", 300, 3000), F("F3", 300, 3100), F("F4", 300, 3200)]
        lot = assemble_lots.build_lot(ORDER, farmers, TRANSPORT, "cheapest_first")
        for a in lot["allocations"]:
            declared = next(int(f["declared_qty_kg"]) for f in farmers if f["farmer_id"] == a["farmer_id"])
            self.assertLessEqual(a["allocated_kg"], declared)
        self.assertEqual(lot["total_kg"], 1000)
        self.assertTrue(lot["filled"])

    def test_cheapest_first_picks_lowest_asks(self):
        farmers = [F("F_hi", 1000, 3500), F("F_lo", 1000, 2800)]
        lot = assemble_lots.build_lot(ORDER, farmers, TRANSPORT, "cheapest_first")
        self.assertEqual(lot["allocations"][0]["farmer_id"], "F_lo")

    def test_reliability_first_picks_most_reliable(self):
        farmers = [F("F_low", 1000, 3000, rel=0.60), F("F_high", 1000, 3000, rel=0.95)]
        lot = assemble_lots.build_lot(ORDER, farmers, TRANSPORT, "reliability_first")
        self.assertEqual(lot["allocations"][0]["farmer_id"], "F_high")

    def test_variants_produced(self):
        farmers = [F("F1", 400, 2900, rel=0.7, zone=("Takeo", "Doun Kaev")),
                   F("F2", 400, 3000, rel=0.9), F("F3", 400, 3100, rel=0.8)]
        lots = assemble_lots.build_candidates(ORDER, farmers, TRANSPORT)
        self.assertGreaterEqual(len(lots), 1)
        self.assertLessEqual(len(lots), 3)


if __name__ == "__main__":
    unittest.main()
