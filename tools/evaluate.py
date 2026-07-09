"""evaluate.py — DERA-ZN stage E (Evaluate) assembler.

Orchestrates the deterministic Evaluate sub-tools for an order:
    assemble_lots.build_candidates  -> candidate consolidated lots (coverage)
    calculate_price.price_lot       -> 0%-cut cost build-up (price headroom)
    route_risk.route_risk_for_lot   -> route risk + spoilage margin (freshness)

and writes outputs/<order>/evaluate.json with each candidate's raw factor values:
    coverage, headroom_per_kg_khr, route_risk, spoilage_margin_days

The M6 grid (score_grid.py) orients + zone-normalizes these into the decision grid.
Handles resume state (skips when inputs unchanged). Refuses to evaluate an order whose
Detect result is blocked.

Run:  py tools/evaluate.py --order order_001
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble_lots
import calculate_price as cp
import config
import dataio
import dera_state as ds
import route_risk as rr

STAGE = "evaluate"


def build_evaluate(order, farmers, transport, weather, handling_fee=None):
    """Pure Evaluate: build + score all candidate lots. Returns the evaluate.json dict."""
    candidates = []
    for lot in assemble_lots.build_candidates(order, farmers, transport):
        pricing = cp.price_lot(lot, order, transport, handling_fee=handling_fee)
        route = rr.route_risk_for_lot(lot, order, transport, weather)
        feasible = bool(pricing["feasible"] and lot["filled"])
        candidates.append({
            "variant": lot["variant"],
            "coverage": lot["coverage"],
            "filled": lot["filled"],
            "n_farmers": lot["n_farmers"],
            "feasible": feasible,
            "allocations": lot["allocations"],
            "pricing": pricing,
            "route": route,
            "factors": {  # raw factor values consumed by the grid (M6)
                "coverage": lot["coverage"],
                "headroom_per_kg_khr": pricing["headroom_per_kg_khr"],
                "route_risk": route["route_risk"],
                "spoilage_margin_days": route["spoilage_margin_days"],
            },
        })
    return {
        "stage": STAGE,
        "order_id": order["order_id"],
        "commodity": order["commodity"],
        "n_candidates": len(candidates),
        "n_feasible": sum(1 for c in candidates if c["feasible"]),
        "params": {
            "handling_fee_per_kg_khr": config.HANDLING_FEE_PER_KG if handling_fee is None else handling_fee,
            "spoilage_buffer_pct": config.SPOILAGE_BUFFER_PCT,
            "route_risk_weights": config.ROUTE_RISK_WEIGHTS,
        },
        "candidates": candidates,
    }


def run_evaluate(order_id, root=None, handling_fee=None, force=False, now=None):
    farmers = dataio.load_farmers(root)
    orders = dataio.load_orders(root)
    transport = dataio.load_transport(root)
    weather = dataio.load_weather(root)
    order = dataio.get_order(order_id, orders)

    # Guard: don't evaluate a blocked order.
    detect_path = os.path.join(ds.order_dir(order_id, root), "detect.json")
    if os.path.exists(detect_path):
        with open(detect_path, encoding="utf-8") as fh:
            detect = json.load(fh)
        if not detect.get("clean", True):
            return {"stage": STAGE, "order_id": order_id, "blocked": True,
                    "reason": "Detect found blockers; not evaluating.",
                    "blockers": detect.get("blockers", [])}, False

    input_hash = ds.hash_inputs("evaluate", order, farmers, transport, weather,
                                {"handling_fee": handling_fee, "spoilage": config.SPOILAGE_BUFFER_PCT,
                                 "route_weights": config.ROUTE_RISK_WEIGHTS})
    state = ds.load_state(order_id, root)
    out_path = os.path.join(ds.order_dir(order_id, root), "evaluate.json")
    if not force and not ds.should_run(state, STAGE, input_hash) and os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as fh:
            return json.load(fh), True

    result = build_evaluate(order, farmers, transport, weather, handling_fee=handling_fee)
    os.makedirs(ds.order_dir(order_id, root), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    ds.mark_done(state, STAGE, "evaluate.json", input_hash, now=now)
    ds.save_state(state, root, now=now)
    return result, False


def _cli(argv=None):
    p = argparse.ArgumentParser(description="DERA-ZN Evaluate: score candidate lots for an order.")
    p.add_argument("--order", required=True)
    p.add_argument("--handling-fee", type=int, default=None)
    p.add_argument("--force", action="store_true")
    p.add_argument("--now")
    args = p.parse_args(argv)
    result, skipped = run_evaluate(args.order, handling_fee=args.handling_fee, force=args.force, now=args.now)
    tag = " (resumed / cached)" if skipped else ""
    if result.get("blocked"):
        print(f"[Evaluate] {result['order_id']}: BLOCKED — {result['reason']}")
        return 2
    print(f"[Evaluate] {result['order_id']}: {result['n_feasible']}/{result['n_candidates']} feasible candidates{tag}")
    for c in result["candidates"]:
        f = c["factors"]
        print(f"  {c['variant']:>17}: coverage={f['coverage']}  headroom={f['headroom_per_kg_khr']:,} KHR/kg  "
              f"route_risk={f['route_risk']:.3f}  spoilage_margin={f['spoilage_margin_days']}d  "
              f"[{'feasible' if c['feasible'] else 'infeasible'}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
