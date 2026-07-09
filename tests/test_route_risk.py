"""Unit tests for tools/route_risk.py (Evaluate — route & perishability risk).

Run:  py -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import route_risk as rr  # noqa: E402


class TestLegRisk(unittest.TestCase):
    def test_bounds(self):
        # extreme-bad inputs still clamp to [0,1]
        r = rr.leg_risk(transit_hours=48, perishability_days=1, temp_c=45,
                        flood_risk="high", road_quality="poor", refrigerated=False)
        self.assertGreaterEqual(r["route_risk"], 0.0)
        self.assertLessEqual(r["route_risk"], 1.0)
        # extreme-good inputs
        r2 = rr.leg_risk(transit_hours=0.5, perishability_days=10, temp_c=20,
                         flood_risk="low", road_quality="good", refrigerated=True)
        self.assertGreaterEqual(r2["route_risk"], 0.0)
        self.assertLessEqual(r2["route_risk"], 1.0)

    def test_increases_with_distance_time(self):
        base = rr.leg_risk(2, 3, 30, "low", "good", False)["route_risk"]
        longer = rr.leg_risk(10, 3, 30, "low", "good", False)["route_risk"]
        self.assertGreater(longer, base)

    def test_increases_with_heat(self):
        cool = rr.leg_risk(4, 3, 26, "low", "fair", False)["route_risk"]
        hot = rr.leg_risk(4, 3, 39, "low", "fair", False)["route_risk"]
        self.assertGreater(hot, cool)

    def test_refrigeration_lowers_risk(self):
        no = rr.leg_risk(6, 2, 35, "medium", "fair", False)["route_risk"]
        yes = rr.leg_risk(6, 2, 35, "medium", "fair", True)["route_risk"]
        self.assertLess(yes, no)

    def test_spoilage_margin(self):
        r = rr.leg_risk(24, 3, 30, "low", "good", False)  # 24h = 1 day transit
        self.assertAlmostEqual(r["spoilage_margin_days"], 3 - 1.0, places=3)
        # tighter perishability -> higher perish component
        tight = rr.leg_risk(12, 1, 30, "low", "good", False)["route_risk"]
        loose = rr.leg_risk(12, 7, 30, "low", "good", False)["route_risk"]
        self.assertGreater(tight, loose)


class TestLotAggregation(unittest.TestCase):
    def _lot(self):
        return {
            "variant": "cheapest_first", "delivery_zone": "Kandal:Ta Khmau", "total_kg": 1000,
            "allocations": [
                {"farmer_id": "F1", "zone": "Kandal:Ta Khmau", "allocated_kg": 600},
                {"farmer_id": "F2", "zone": "Siem Reap:Puok", "allocated_kg": 400},  # far leg
            ],
        }

    def _order(self):
        return {"order_id": "order_x", "perishability_days": "3", "delivery_province": "Kandal",
                "delivery_commune": "Ta Khmau", "delivery_date": "2026-07-22"}

    def test_weighted_and_min_margin(self):
        transport = [
            {"from_zone": "Kandal:Ta Khmau", "to_zone": "Kandal:Ta Khmau", "avg_transit_hours": "0.5",
             "road_quality": "good", "refrigerated": "true"},
            {"from_zone": "Siem Reap:Puok", "to_zone": "Kandal:Ta Khmau", "avg_transit_hours": "8.0",
             "road_quality": "poor", "refrigerated": "false"},
        ]
        weather = [{"province": "Kandal", "commune": "Ta Khmau", "date": "2026-07-22",
                    "temp_c": "34", "flood_risk": "medium"}]
        r = rr.route_risk_for_lot(self._lot(), self._order(), transport, weather)
        self.assertEqual(len(r["legs"]), 2)
        # lot route risk is between the two legs' risks (kg-weighted average)
        risks = sorted(l["route_risk"] for l in r["legs"])
        self.assertGreaterEqual(r["route_risk"], risks[0])
        self.assertLessEqual(r["route_risk"], risks[1])
        # spoilage margin is the tightest (min) leg -> the far leg
        self.assertEqual(r["spoilage_margin_days"], min(l["spoilage_margin_days"] for l in r["legs"]))

    def test_missing_weather_uses_default(self):
        transport = [{"from_zone": "Kandal:Ta Khmau", "to_zone": "Kandal:Ta Khmau",
                      "avg_transit_hours": "1.0", "road_quality": "good", "refrigerated": "false"}]
        lot = {"variant": "v", "delivery_zone": "Kandal:Ta Khmau", "total_kg": 500,
               "allocations": [{"farmer_id": "F1", "zone": "Kandal:Ta Khmau", "allocated_kg": 500}]}
        r = rr.route_risk_for_lot(lot, self._order(), transport, [])  # no weather rows
        self.assertEqual(r["weather"]["temp_c"], 30.0)
        self.assertEqual(r["weather"]["flood_risk"], "low")


if __name__ == "__main__":
    unittest.main()
