"""validate_data.py — DERA-ZN stage D (Detect).

Audits a buyer order + farmers' declared supply and emits outputs/<order>/detect.json:
    { clean, blockers, warnings, supply, facts, params }

The headline check is the **volume gap**: is there enough declared supply of the
ordered commodity, at the required quality grade, to fill the order? If not, that
is a hard blocker and the pipeline should stop with a renegotiate recommendation.

Deterministic + stdlib-only. build_detect() is pure (takes in-memory rows) so it is
easy to unit-test; the CLI wrapper handles loading, resume state, and file output.

Run:
    py tools/validate_data.py --order order_001
    py tools/validate_data.py --all          # schema smoke over every order
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import dataio
import dera_state as ds

# Required columns per CSV (schema check).
REQUIRED = {
    "farmers": ["farmer_id", "province", "commune", "declared_crop", "declared_qty_kg",
                "quality_grade", "reliability_score", "ask_price_per_kg_khr", "expected_harvest_date"],
    "orders": ["order_id", "commodity", "quantity_kg", "quality_required", "max_price_per_kg_khr",
               "delivery_province", "delivery_commune", "delivery_date", "perishability_days"],
    "transport": ["from_zone", "to_zone", "distance_km", "cost_per_kg_khr"],
    "weather": ["province", "commune", "date"],
}
STAGE = "detect"


def _issue(code, message, **extra):
    d = {"code": code, "message": message}
    d.update(extra)
    return d


def _check_schema(name, rows, blockers):
    if not rows:
        blockers.append(_issue("EMPTY_TABLE", f"{name}.csv has no rows"))
        return
    missing = [c for c in REQUIRED[name] if c not in rows[0]]
    if missing:
        blockers.append(_issue("SCHEMA", f"{name}.csv missing columns: {missing}", columns=missing))


def build_detect(order_id, farmers, orders, transport, weather):
    """Pure Detect logic. Returns the detect.json dict (no I/O)."""
    blockers, warnings = [], []

    # 1. Schema -----------------------------------------------------------------
    _check_schema("farmers", farmers, blockers)
    _check_schema("orders", orders, blockers)
    _check_schema("transport", transport, blockers)
    _check_schema("weather", weather, blockers)
    if blockers:  # cannot go further without a valid schema
        return _result(order_id, None, blockers, warnings, supply=None, facts={})

    # 2. Order exists -----------------------------------------------------------
    try:
        order = dataio.get_order(order_id, orders)
    except KeyError as e:
        blockers.append(_issue("ORDER_NOT_FOUND", str(e)))
        return _result(order_id, None, blockers, warnings, supply=None, facts={})

    commodity = order["commodity"]
    req_grade = order["quality_required"]
    try:
        req_qty = dataio.to_int(order["quantity_kg"])
    except ValueError:
        blockers.append(_issue("BAD_ORDER_QTY", f"quantity_kg not an integer: {order['quantity_kg']!r}"))
        return _result(order_id, order, blockers, warnings, supply=None, facts={})

    # 3. Row-level range checks (warnings unless clearly fatal) ------------------
    _validate_farmer_rows(farmers, warnings)

    # 4. Supply + volume-gap check ---------------------------------------------
    matching = [f for f in farmers if f.get("declared_crop") == commodity]
    qualifying = [f for f in matching if config.grade_meets(f.get("quality_grade"), req_grade)]

    def _sum_qty(rows):
        total = 0
        for f in rows:
            try:
                total += dataio.to_int(f["declared_qty_kg"])
            except (ValueError, KeyError):
                warnings.append(_issue("BAD_QTY", f"farmer {f.get('farmer_id')} has bad declared_qty_kg",
                                       farmer_id=f.get("farmer_id")))
        return total

    total_kg = _sum_qty(matching)
    qualifying_kg = _sum_qty(qualifying)

    supply = {
        "commodity": commodity,
        "required_qty_kg": req_qty,
        "quality_required": req_grade,
        "total_declared_kg": total_kg,
        "qualifying_kg": qualifying_kg,          # meets required grade
        "n_matching_farmers": len(matching),
        "n_qualifying_farmers": len(qualifying),
    }

    if qualifying_kg < req_qty:
        blockers.append(_issue(
            "VOLUME_GAP",
            f"Only {qualifying_kg} kg of {commodity} at grade >= {req_grade} declared, "
            f"but order needs {req_qty} kg. Recommend renegotiate quantity, grade, or timeline.",
            qualifying_kg=qualifying_kg, required_qty_kg=req_qty, shortfall_kg=req_qty - qualifying_kg))
    elif len(qualifying) == 1:
        warnings.append(_issue("SINGLE_FARMER",
                               "Order can be filled by a single farmer — no aggregation needed; "
                               "double-check this is expected."))

    # 5. Referential: delivery zone known to transport + weather ---------------
    dz = dataio.order_delivery_zone(order)
    if not any(t.get("to_zone") == dz for t in transport):
        warnings.append(_issue("NO_ROUTE_TO_DELIVERY",
                               f"no transport route ends at delivery zone {dz}", zone=dz))
    if not any(w.get("province") == order["delivery_province"] and w.get("commune") == order["delivery_commune"]
               for w in weather):
        warnings.append(_issue("NO_WEATHER_FOR_DELIVERY",
                               f"no weather rows for delivery zone {dz}", zone=dz))

    facts = {
        "delivery_zone": dz,
        "delivery_date": order.get("delivery_date"),
        "perishability_days": order.get("perishability_days"),
        "max_price_per_kg_khr": order.get("max_price_per_kg_khr"),
    }
    return _result(order_id, order, blockers, warnings, supply, facts)


def _validate_farmer_rows(farmers, warnings):
    for f in farmers:
        fid = f.get("farmer_id", "?")
        # reliability 0..1
        try:
            r = dataio.to_float(f["reliability_score"])
            if not (0.0 <= r <= 1.0):
                warnings.append(_issue("RANGE", f"farmer {fid} reliability_score {r} out of [0,1]", farmer_id=fid))
        except (ValueError, KeyError):
            warnings.append(_issue("BAD_FIELD", f"farmer {fid} reliability_score unparsable", farmer_id=fid))
        # grade valid
        if f.get("quality_grade") not in config.VALID_GRADES:
            warnings.append(_issue("BAD_GRADE", f"farmer {fid} grade {f.get('quality_grade')!r} invalid", farmer_id=fid))
        # ask price positive
        try:
            if dataio.to_int(f["ask_price_per_kg_khr"]) <= 0:
                warnings.append(_issue("RANGE", f"farmer {fid} ask_price must be > 0", farmer_id=fid))
        except (ValueError, KeyError):
            warnings.append(_issue("BAD_FIELD", f"farmer {fid} ask_price unparsable", farmer_id=fid))


def _result(order_id, order, blockers, warnings, supply, facts):
    return {
        "stage": STAGE,
        "order_id": order_id,
        "clean": len(blockers) == 0,
        "blockers": blockers,
        "warnings": warnings,
        "supply": supply,
        "facts": facts,
        "params": {"grades": list(config.VALID_GRADES)},
    }


# --------------------------------------------------------------------------- #
# CLI wrapper (loading, resume state, file output)
# --------------------------------------------------------------------------- #
def run_detect(order_id, root=None, force=False, now=None):
    farmers = dataio.load_farmers(root)
    orders = dataio.load_orders(root)
    transport = dataio.load_transport(root)
    weather = dataio.load_weather(root)

    order_row = next((o for o in orders if o["order_id"] == order_id), None)
    input_hash = ds.hash_inputs("detect", order_row, farmers, {"grades": config.VALID_GRADES})

    state = ds.load_state(order_id, root)
    out_path = os.path.join(ds.order_dir(order_id, root), "detect.json")

    if not force and not ds.should_run(state, STAGE, input_hash) and os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as fh:
            return json.load(fh), True  # (result, skipped)

    result = build_detect(order_id, farmers, orders, transport, weather)
    os.makedirs(ds.order_dir(order_id, root), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    ds.mark_done(state, STAGE, "detect.json", input_hash, now=now)
    ds.save_state(state, root, now=now)
    return result, False


def _print_summary(result, skipped):
    tag = " (resumed / cached)" if skipped else ""
    verdict = "CLEAN" if result["clean"] else "BLOCKED"
    print(f"[Detect] {result['order_id']}: {verdict}{tag}")
    if result.get("supply"):
        s = result["supply"]
        print(f"  supply: {s['qualifying_kg']} kg of {s['commodity']} at grade>= {s['quality_required']} "
              f"from {s['n_qualifying_farmers']} farmers (order needs {s['required_qty_kg']} kg)")
    for b in result["blockers"]:
        print(f"  BLOCKER [{b['code']}]: {b['message']}")
    for w in result["warnings"]:
        print(f"  warn    [{w['code']}]: {w['message']}")


def _cli(argv=None):
    p = argparse.ArgumentParser(description="DERA-ZN Detect: audit order + supply, volume-gap check.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--order", help="order id, e.g. order_001")
    g.add_argument("--all", action="store_true", help="schema smoke over every order")
    p.add_argument("--force", action="store_true", help="ignore resume cache")
    p.add_argument("--now", help="inject ISO timestamp (for deterministic runs)")
    args = p.parse_args(argv)

    if args.all:
        orders = dataio.load_orders()
        rc = 0
        for o in orders:
            result, skipped = run_detect(o["order_id"], force=args.force, now=args.now)
            _print_summary(result, skipped)
            if not result["clean"]:
                rc = 1
        return rc

    result, skipped = run_detect(args.order, force=args.force, now=args.now)
    _print_summary(result, skipped)
    return 0 if result["clean"] else 2


if __name__ == "__main__":
    raise SystemExit(_cli())
