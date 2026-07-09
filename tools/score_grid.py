"""score_grid.py — DERA-ZN stage R (Recommend): the Zone-Normalized decision grid.

Ranks the candidate lots from evaluate.json. For each of the 4 factors, orient to
higher-is-better, then **min-max normalize across the candidate lots** (the "ZN" step),
then combine with the approved weights (docs/business_rules.md §3):

    coverage   = coverage                       (higher better)
    price      = headroom_per_kg_khr            (higher better)
    route      = 1 - route_risk                 (higher better)
    freshness  = max(0, spoilage_margin_days)   (higher better)

    norm_f(lot) = (raw_f - min_f) / (max_f - min_f)   [all 1.0 if max==min]
    score(lot)  = Σ W_f * norm_f(lot)

Only feasible candidates are ranked; if none are feasible the recommendation is
"cannot fulfill". Ties break by higher coverage, then higher mean farmer reliability.

Pure build_grid() is unit-tested. Writes outputs/<order>/recommend.json with resume.

Run:  py tools/score_grid.py --order order_001
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import dera_state as ds

STAGE = "recommend"
FACTORS = ("coverage", "price", "route", "freshness")


def _orient(candidate):
    """Raw higher-is-better factor values for one candidate."""
    f = candidate["factors"]
    return {
        "coverage": float(f["coverage"]),
        "price": float(f["headroom_per_kg_khr"]),
        "route": 1.0 - float(f["route_risk"]),
        "freshness": max(0.0, float(f["spoilage_margin_days"])),
    }


def _mean_reliability(candidate):
    allocs = candidate.get("allocations", [])
    if not allocs:
        return 0.0
    return sum(a.get("reliability_score", 0.0) for a in allocs) / len(allocs)


def build_grid(candidates, weights=None):
    """Zone-normalize + weight + rank the feasible candidates. Pure. Returns a dict."""
    weights = weights or config.GRID_WEIGHTS
    total_w = sum(weights.values())
    if abs(total_w - 1.0) > 1e-9:  # renormalize defensively; flag it
        weights = {k: v / total_w for k, v in weights.items()}
        weights_note = f"weights did not sum to 1.0 (was {total_w}); renormalized"
    else:
        weights_note = None

    feasible = [c for c in candidates if c.get("feasible")]
    if not feasible:
        return {"weights": weights, "weights_note": weights_note, "ranked": [],
                "winner": None, "n_feasible": 0,
                "note": "No feasible candidate lot within the buyer cap — recommend renegotiate."}

    raws = {c["variant"]: _orient(c) for c in feasible}
    mins = {f: min(raws[v][f] for v in raws) for f in FACTORS}
    maxs = {f: max(raws[v][f] for v in raws) for f in FACTORS}

    def norm(f, val):
        span = maxs[f] - mins[f]
        return 1.0 if span == 0 else (val - mins[f]) / span

    rows = []
    for c in feasible:
        raw = raws[c["variant"]]
        normalized = {f: round(norm(f, raw[f]), 4) for f in FACTORS}
        weighted = {f: round(weights[f] * normalized[f], 4) for f in FACTORS}
        score = round(sum(weighted.values()), 4)
        rows.append({
            "variant": c["variant"],
            "score": score,
            "raw": {f: round(raw[f], 4) for f in FACTORS},
            "normalized": normalized,
            "weighted": weighted,
            "coverage": c["coverage"],
            "mean_reliability": round(_mean_reliability(c), 4),
            "n_farmers": c["n_farmers"],
            "blended_price_per_kg_khr": c["pricing"]["blended_price_per_kg_khr"],
            "headroom_per_kg_khr": c["pricing"]["headroom_per_kg_khr"],
            "route_risk": c["route"]["route_risk"],
            "spoilage_margin_days": c["route"]["spoilage_margin_days"],
        })

    # rank by score desc; tie-break: coverage desc, mean_reliability desc, variant asc (stable)
    rows.sort(key=lambda r: (-r["score"], -r["coverage"], -r["mean_reliability"], r["variant"]))
    return {"weights": weights, "weights_note": weights_note, "ranked": rows,
            "winner": rows[0], "n_feasible": len(feasible), "note": None}


def run_recommend(order_id, root=None, force=False, now=None):
    eval_path = os.path.join(ds.order_dir(order_id, root), "evaluate.json")
    if not os.path.exists(eval_path):
        raise FileNotFoundError(f"{eval_path} missing — run Evaluate first (tools/evaluate.py --order {order_id})")
    with open(eval_path, encoding="utf-8") as fh:
        evaluate = json.load(fh)

    input_hash = ds.hash_inputs("recommend", evaluate.get("candidates"), config.GRID_WEIGHTS)
    state = ds.load_state(order_id, root)
    out_path = os.path.join(ds.order_dir(order_id, root), "recommend.json")
    if not force and not ds.should_run(state, STAGE, input_hash) and os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as fh:
            return json.load(fh), True

    grid = build_grid(evaluate.get("candidates", []))
    result = {"stage": STAGE, "order_id": order_id, "commodity": evaluate.get("commodity"), **grid}
    os.makedirs(ds.order_dir(order_id, root), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    ds.mark_done(state, STAGE, "recommend.json", input_hash, now=now)
    ds.save_state(state, root, now=now)
    return result, False


def _cli(argv=None):
    p = argparse.ArgumentParser(description="DERA-ZN Recommend: zone-normalized decision grid.")
    p.add_argument("--order", required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--now")
    args = p.parse_args(argv)
    result, skipped = run_recommend(args.order, force=args.force, now=args.now)
    tag = " (resumed / cached)" if skipped else ""
    if not result["winner"]:
        print(f"[Recommend] {result['order_id']}: NO FEASIBLE LOT — {result['note']}")
        return 2
    w = result["winner"]
    print(f"[Recommend] {result['order_id']}: winner = {w['variant']} (score {w['score']}){tag}")
    print(f"  {'variant':>17} | {'score':>6} | cov  price route fresh (normalized)")
    for r in result["ranked"]:
        n = r["normalized"]
        print(f"  {r['variant']:>17} | {r['score']:>6} | {n['coverage']:.2f} {n['price']:.2f} "
              f"{n['route']:.2f} {n['freshness']:.2f}")
    print(f"  winner blended={w['blended_price_per_kg_khr']:,} KHR/kg  headroom={w['headroom_per_kg_khr']:,}  "
          f"route_risk={w['route_risk']}  spoilage_margin={w['spoilage_margin_days']}d")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
