"""Unit tests for tools/validate_data.py (Detect).

Uses in-memory rows to exercise build_detect() (pure), so no CSVs are touched.

Run:  py -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import validate_data as vd  # noqa: E402


def farmer(fid, crop, qty, grade="B", prov="Kandal", comm="Ta Khmau", ask=3000, rel=0.8):
    return {"farmer_id": fid, "province": prov, "commune": comm, "declared_crop": crop,
            "declared_qty_kg": str(qty), "quality_grade": grade, "reliability_score": str(rel),
            "ask_price_per_kg_khr": str(ask), "expected_harvest_date": "2026-07-18"}


def order(oid, crop, qty, grade="B", prov="Kandal", comm="Ta Khmau", cap=3800):
    return {"order_id": oid, "commodity": crop, "quantity_kg": str(qty), "quality_required": grade,
            "max_price_per_kg_khr": str(cap), "delivery_province": prov, "delivery_commune": comm,
            "delivery_date": "2026-07-22", "perishability_days": "3", "penalty_per_day_khr": "200"}


TRANSPORT = [{"from_zone": "Takeo:Doun Kaev", "to_zone": "Kandal:Ta Khmau",
              "distance_km": "60", "cost_per_kg_khr": "230"}]
WEATHER = [{"province": "Kandal", "commune": "Ta Khmau", "date": "2026-07-22"}]


class TestVolumeGap(unittest.TestCase):
    def test_fillable_is_clean(self):
        farmers = [farmer("F1", "bok_choy", 500), farmer("F2", "bok_choy", 450),
                   farmer("F3", "bok_choy", 400), farmer("F4", "bok_choy", 300)]
        res = vd.build_detect("order_x", farmers, [order("order_x", "bok_choy", 1500)], TRANSPORT, WEATHER)
        self.assertTrue(res["clean"])
        self.assertEqual(res["supply"]["qualifying_kg"], 1650)
        self.assertFalse(any(b["code"] == "VOLUME_GAP" for b in res["blockers"]))

    def test_supply_below_demand_blocks(self):
        farmers = [farmer("F1", "long_bean", 500), farmer("F2", "long_bean", 450)]
        res = vd.build_detect("order_x", farmers, [order("order_x", "long_bean", 3000)], TRANSPORT, WEATHER)
        self.assertFalse(res["clean"])
        gap = [b for b in res["blockers"] if b["code"] == "VOLUME_GAP"]
        self.assertEqual(len(gap), 1)
        self.assertEqual(gap[0]["shortfall_kg"], 2050)

    def test_quality_aware_supply(self):
        # Enough total kg, but not enough at required grade A -> volume gap on qualifying_kg.
        farmers = [farmer("F1", "cabbage", 1000, grade="B"), farmer("F2", "cabbage", 1000, grade="A")]
        res = vd.build_detect("order_x", farmers, [order("order_x", "cabbage", 1500, grade="A")], TRANSPORT, WEATHER)
        self.assertEqual(res["supply"]["total_declared_kg"], 2000)
        self.assertEqual(res["supply"]["qualifying_kg"], 1000)   # only the grade-A farmer counts
        self.assertFalse(res["clean"])


class TestSchemaAndRefs(unittest.TestCase):
    def test_order_not_found(self):
        res = vd.build_detect("missing", [farmer("F1", "bok_choy", 500)],
                              [order("order_x", "bok_choy", 400)], TRANSPORT, WEATHER)
        self.assertFalse(res["clean"])
        self.assertTrue(any(b["code"] == "ORDER_NOT_FOUND" for b in res["blockers"]))

    def test_missing_column_is_schema_blocker(self):
        bad = [{"farmer_id": "F1"}]  # missing most columns
        res = vd.build_detect("order_x", bad, [order("order_x", "bok_choy", 400)], TRANSPORT, WEATHER)
        self.assertFalse(res["clean"])
        self.assertTrue(any(b["code"] == "SCHEMA" for b in res["blockers"]))

    def test_unknown_delivery_zone_warns(self):
        # Non-empty transport/weather, but none referencing the delivery zone -> warnings, not blockers.
        farmers = [farmer("F1", "bok_choy", 500), farmer("F2", "bok_choy", 500),
                   farmer("F3", "bok_choy", 500), farmer("F4", "bok_choy", 500)]
        other_transport = [{"from_zone": "Takeo:Doun Kaev", "to_zone": "Siem Reap:Puok",
                            "distance_km": "200", "cost_per_kg_khr": "580"}]
        other_weather = [{"province": "Siem Reap", "commune": "Puok", "date": "2026-07-22"}]
        res = vd.build_detect("order_x", farmers, [order("order_x", "bok_choy", 1500)],
                              other_transport, other_weather)
        self.assertTrue(res["clean"])  # warnings don't block
        codes = {w["code"] for w in res["warnings"]}
        self.assertIn("NO_ROUTE_TO_DELIVERY", codes)
        self.assertIn("NO_WEATHER_FOR_DELIVERY", codes)


if __name__ == "__main__":
    unittest.main()
