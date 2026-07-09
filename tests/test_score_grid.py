"""Unit tests for tools/score_grid.py (Recommend — Zone-Normalized decision grid).

Run:  py -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import score_grid as sg  # noqa: E402


def candidate(variant, coverage, headroom, route_risk, margin, feasible=True, allocs=None):
    return {
        "variant": variant, "coverage": coverage, "feasible": feasible, "n_farmers": len(allocs or [1]),
        "allocations": allocs or [{"reliability_score": 0.8}],
        "factors": {"coverage": coverage, "headroom_per_kg_khr": headroom,
                    "route_risk": route_risk, "spoilage_margin_days": margin},
        "pricing": {"blended_price_per_kg_khr": 3500, "headroom_per_kg_khr": headroom},
        "route": {"route_risk": route_risk, "spoilage_margin_days": margin},
    }


class TestNormalization(unittest.TestCase):
    def test_normalized_in_unit_interval(self):
        cands = [candidate("a", 1.0, 200, 0.19, 2.9),
                 candidate("b", 1.0, 180, 0.16, 2.9),
                 candidate("c", 1.0, 80, 0.17, 2.7)]
        grid = sg.build_grid(cands)
        for row in grid["ranked"]:
            for f, v in row["normalized"].items():
                self.assertGreaterEqual(v, 0.0, f)
                self.assertLessEqual(v, 1.0, f)

    def test_equal_factor_all_ones(self):
        # coverage identical across all -> normalized coverage = 1.0 for every candidate (no /0)
        cands = [candidate("a", 1.0, 200, 0.19, 2.9), candidate("b", 1.0, 180, 0.16, 2.8)]
        grid = sg.build_grid(cands)
        for row in grid["ranked"]:
            self.assertEqual(row["normalized"]["coverage"], 1.0)

    def test_weights_sum_to_one_and_score_bounded(self):
        self.assertAlmostEqual(sum(sg.config.GRID_WEIGHTS.values()), 1.0, places=9)
        cands = [candidate("a", 1.0, 200, 0.19, 2.9), candidate("b", 1.0, 80, 0.30, 2.0)]
        for row in sg.build_grid(cands)["ranked"]:
            self.assertGreaterEqual(row["score"], 0.0)
            self.assertLessEqual(row["score"], 1.0)


class TestRankingAndFeasibility(unittest.TestCase):
    def test_deterministic_and_best_wins(self):
        # 'best' dominates on price+route+freshness -> should rank first
        cands = [candidate("best", 1.0, 300, 0.10, 3.0),
                 candidate("mid", 1.0, 150, 0.20, 2.5),
                 candidate("worst", 1.0, 50, 0.40, 1.5)]
        grid = sg.build_grid(cands)
        self.assertEqual(grid["winner"]["variant"], "best")
        self.assertEqual([r["variant"] for r in grid["ranked"]], ["best", "mid", "worst"])
        # stable/deterministic across runs
        self.assertEqual(grid["ranked"], sg.build_grid(cands)["ranked"])

    def test_only_feasible_ranked(self):
        cands = [candidate("ok", 1.0, 200, 0.19, 2.9, feasible=True),
                 candidate("overcap", 1.0, -500, 0.19, 2.9, feasible=False)]
        grid = sg.build_grid(cands)
        self.assertEqual(grid["n_feasible"], 1)
        self.assertEqual([r["variant"] for r in grid["ranked"]], ["ok"])

    def test_no_feasible_recommends_renegotiate(self):
        cands = [candidate("x", 1.0, -100, 0.5, 1.0, feasible=False)]
        grid = sg.build_grid(cands)
        self.assertIsNone(grid["winner"])
        self.assertIn("renegotiate", grid["note"])

    def test_tie_breaks_by_coverage_then_reliability(self):
        # identical factors -> all normalized equal -> scores tie; break by mean reliability
        a = candidate("a", 1.0, 100, 0.2, 2.0, allocs=[{"reliability_score": 0.60}])
        b = candidate("b", 1.0, 100, 0.2, 2.0, allocs=[{"reliability_score": 0.95}])
        grid = sg.build_grid([a, b])
        self.assertEqual(grid["winner"]["variant"], "b")  # higher reliability wins the tie


if __name__ == "__main__":
    unittest.main()
