"""route_risk.py — DERA-ZN Evaluate: route & perishability risk for a candidate lot.

Implements docs/business_rules.md §2. Risk is normalized to [0,1] (higher = worse):

    transit_risk = clamp(avg_transit_hours / MAX_ACCEPTABLE_HOURS)
    perish_risk  = clamp((avg_transit_hours/24) / perishability_days)
    heat_risk    = clamp((temp_c - TEMP_SAFE_C) / (TEMP_MAX_C - TEMP_SAFE_C))
    road_risk    = ROAD_RISK[road_quality]
    flood_risk   = FLOOD_RISK_N[flood_risk]
    route_risk   = clamp( Σ w_i * risk_i  - (REFRIG_RELIEF if refrigerated else 0) )
    spoilage_margin_days = perishability_days - avg_transit_hours/24     (>0 desirable)

A consolidated lot has several legs (one per farmer zone -> delivery zone). The lot's
route_risk is the kg-weighted average of its legs; its spoilage margin is the *minimum*
(tightest) across legs — the binding constraint. Weather is read at the delivery zone on
the delivery date.

Pure + stdlib-only; unit-tested. route-risk sub-weights are provisional (M6 approval).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble_lots
import config
import dataio


def _weather_at(weather, province, commune, date):
    """Return (temp_c, flood_risk) at a zone/date, or sensible defaults if missing."""
    for w in weather:
        if w.get("province") == province and w.get("commune") == commune and w.get("date") == date:
            try:
                return dataio.to_float(w["temp_c"]), w.get("flood_risk", "low")
            except (ValueError, KeyError):
                break
    return 30.0, "low"  # default: warm, no flood info


def leg_risk(transit_hours, perishability_days, temp_c, flood_risk, road_quality, refrigerated, p=config):
    """Pure per-leg route risk. Returns a dict of components + route_risk + spoilage margin."""
    transit = p.clamp(transit_hours / p.MAX_ACCEPTABLE_HOURS)
    perish = p.clamp((transit_hours / 24.0) / perishability_days) if perishability_days else 1.0
    heat = p.clamp((temp_c - p.TEMP_SAFE_C) / (p.TEMP_MAX_C - p.TEMP_SAFE_C))
    road = p.ROAD_RISK.get(road_quality, 0.4)
    flood = p.FLOOD_RISK_N.get(flood_risk, 0.0)
    w = p.ROUTE_RISK_WEIGHTS
    raw = (w["transit"] * transit + w["perish"] * perish + w["heat"] * heat
           + w["road"] * road + w["flood"] * flood)
    relief = p.REFRIG_RELIEF if refrigerated else 0.0
    risk = p.clamp(raw - relief)
    return {
        "route_risk": round(risk, 4),
        "spoilage_margin_days": round(perishability_days - transit_hours / 24.0, 3),
        "components": {"transit": round(transit, 3), "perish": round(perish, 3), "heat": round(heat, 3),
                       "road": road, "flood": flood, "refrig_relief": relief},
    }


def route_risk_for_lot(lot, order, transport, weather):
    """Aggregate leg risks into a lot-level route factor."""
    routes = assemble_lots._transport_lookup(transport)
    # transport rows also carry road_quality/refrigerated/hours; build a richer lookup:
    meta = {}
    for t in transport:
        try:
            meta[(t["from_zone"], t["to_zone"])] = {
                "hours": dataio.to_float(t["avg_transit_hours"]),
                "road": t.get("road_quality", "fair"),
                "refrig": dataio.to_bool(t.get("refrigerated", "false")),
            }
        except (ValueError, KeyError):
            continue

    perishability = dataio.to_int(order["perishability_days"])
    temp_c, flood = _weather_at(weather, order["delivery_province"], order["delivery_commune"],
                                order["delivery_date"])
    dz = lot["delivery_zone"]

    legs = []
    total_kg = lot["total_kg"] or 1
    weighted_risk = 0.0
    min_margin = None
    for a in lot["allocations"]:
        m = meta.get((a["zone"], dz))
        hours = m["hours"] if m else config.MAX_ACCEPTABLE_HOURS  # unknown route -> pessimistic
        road = m["road"] if m else "poor"
        refrig = m["refrig"] if m else False
        lr = leg_risk(hours, perishability, temp_c, flood, road, refrig)
        lr.update({"farmer_id": a["farmer_id"], "zone": a["zone"], "allocated_kg": a["allocated_kg"],
                   "transit_hours": hours, "road_quality": road, "refrigerated": refrig})
        legs.append(lr)
        weighted_risk += lr["route_risk"] * a["allocated_kg"]
        margin = lr["spoilage_margin_days"]
        min_margin = margin if min_margin is None else min(min_margin, margin)

    return {
        "route_risk": round(weighted_risk / total_kg, 4),          # kg-weighted average
        "spoilage_margin_days": min_margin if min_margin is not None else 0.0,  # tightest leg
        "weather": {"temp_c": temp_c, "flood_risk": flood, "at": dz, "date": order["delivery_date"]},
        "worst_leg_risk": round(max((l["route_risk"] for l in legs), default=0.0), 4),
        "legs": legs,
    }


if __name__ == "__main__":
    import argparse
    import json
    p = argparse.ArgumentParser(description="DERA-ZN Evaluate: route/perishability risk for candidate lots.")
    p.add_argument("--order", required=True)
    args = p.parse_args()
    farmers = dataio.load_farmers()
    orders = dataio.load_orders()
    transport = dataio.load_transport()
    weather = dataio.load_weather()
    order = dataio.get_order(args.order, orders)
    print(f"[Route] {order['order_id']}: perishability {order['perishability_days']}d, "
          f"delivery {order['delivery_province']}:{order['delivery_commune']} {order['delivery_date']}")
    for lot in assemble_lots.build_candidates(order, farmers, transport):
        r = route_risk_for_lot(lot, order, transport, weather)
        print(f"  {lot['variant']:>17}: route_risk={r['route_risk']:.3f}  "
              f"spoilage_margin={r['spoilage_margin_days']:.2f}d  worst_leg={r['worst_leg_risk']:.3f}  "
              f"weather={r['weather']['temp_c']}C/{r['weather']['flood_risk']}")
    raise SystemExit(0)
