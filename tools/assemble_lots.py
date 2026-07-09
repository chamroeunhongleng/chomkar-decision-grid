"""assemble_lots.py — DERA-ZN Evaluate: deterministic candidate-lot assembly.

Deciding which farmers supply an order is a *money* decision (it determines who
earns), so it must be deterministic and auditable — not left to prose. This module
builds candidate consolidated lots that close the volume gap, using three transparent
ranking strategies (docs/business_rules.md §3):

    cheapest_first      — lowest ask price first  (maximizes headroom)
    nearest_first       — shortest transport distance to delivery  (lowest route risk)
    reliability_first   — highest reliability_score first  (safest fulfillment)

Allocation is greedy: sort qualifying farmers by the variant key, allocate kg until the
order quantity is met (the last farmer may be partially allocated); never allocate beyond
a farmer's declared_qty_kg. Only farmers matching the commodity AND the required grade are
eligible.

Pure + stdlib-only; unit-tested.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import dataio


def _transport_lookup(transport):
    """(from_zone, to_zone) -> {distance_km, cost_per_kg_khr} (numeric)."""
    out = {}
    for t in transport:
        try:
            out[(t["from_zone"], t["to_zone"])] = {
                "distance_km": dataio.to_float(t["distance_km"]),
                "cost_per_kg_khr": dataio.to_int(t["cost_per_kg_khr"]),
            }
        except (ValueError, KeyError):
            continue
    return out


def eligible_farmers(order, farmers):
    """Farmers matching the order commodity and meeting the required grade."""
    commodity = order["commodity"]
    req_grade = order["quality_required"]
    return [f for f in farmers
            if f.get("declared_crop") == commodity and config.grade_meets(f.get("quality_grade"), req_grade)]


def _rank_key(variant, delivery_zone, routes):
    """Return a sort key function for the given variant (all ascending)."""
    if variant == "cheapest_first":
        return lambda f: (dataio.to_int(f["ask_price_per_kg_khr"]), f["farmer_id"])
    if variant == "nearest_first":
        def dist(f):
            r = routes.get((dataio.farmer_zone(f), delivery_zone))
            return r["distance_km"] if r else float("inf")
        return lambda f: (dist(f), f["farmer_id"])
    if variant == "reliability_first":
        # higher reliability first -> negate for ascending sort
        return lambda f: (-dataio.to_float(f["reliability_score"]), f["farmer_id"])
    raise ValueError(f"unknown lot variant {variant!r}")


def build_lot(order, farmers, transport, variant):
    """Assemble one candidate lot for the given variant. Returns a lot dict."""
    req_qty = dataio.to_int(order["quantity_kg"])
    delivery_zone = dataio.order_delivery_zone(order)
    routes = _transport_lookup(transport)
    eligible = eligible_farmers(order, farmers)
    ranked = sorted(eligible, key=_rank_key(variant, delivery_zone, routes))

    allocations = []
    remaining = req_qty
    for f in ranked:
        if remaining <= 0:
            break
        avail = dataio.to_int(f["declared_qty_kg"])
        take = min(avail, remaining)
        if take <= 0:
            continue
        allocations.append({
            "farmer_id": f["farmer_id"],
            "zone": dataio.farmer_zone(f),
            "grade": f.get("quality_grade"),
            "ask_price_per_kg_khr": dataio.to_int(f["ask_price_per_kg_khr"]),
            "reliability_score": dataio.to_float(f["reliability_score"]),
            "allocated_kg": take,
        })
        remaining -= take

    total_kg = sum(a["allocated_kg"] for a in allocations)
    coverage = round(min(total_kg / req_qty, 1.0), 4) if req_qty else 0.0
    return {
        "variant": variant,
        "order_qty_kg": req_qty,
        "total_kg": total_kg,
        "coverage": coverage,
        "filled": total_kg >= req_qty,
        "n_farmers": len(allocations),
        "delivery_zone": delivery_zone,
        "allocations": allocations,
    }


def build_candidates(order, farmers, transport, variants=None):
    """Build all candidate lots (one per variant). Deduplicates identical lots."""
    variants = variants or config.LOT_VARIANTS
    lots = []
    seen = set()
    for v in variants:
        lot = build_lot(order, farmers, transport, v)
        # signature = ordered (farmer, kg) pairs; drop duplicate allocations under a new label
        sig = tuple((a["farmer_id"], a["allocated_kg"]) for a in lot["allocations"])
        if sig in seen:
            continue
        seen.add(sig)
        lots.append(lot)
    return lots
