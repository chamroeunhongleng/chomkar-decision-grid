"""record_outcome.py — DERA-ZN M12: append one realized outcome to data/outcomes.csv.

The outcomes ledger is the evidence base for weight calibration. Each row snapshots the
winning lot's normalized decision factors (f_coverage/f_price/f_route/f_freshness) alongside
what actually happened (shipped, on-time, spoilage, satisfaction, paid-in-full). The factor
snapshot is pulled from outputs/<order>/recommend.json if present, else passed explicitly.

Deterministic append + validation. Pure validate_row() is unit-tested.

Run:
    py tools/record_outcome.py --order order_001 --shipped true --on-time true \\
        --spoilage 4 --satisfaction 5 --paid-full true --notes "delivered fine"
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dataio
import dera_state as ds

FIELDS = ["order_id", "decision_date", "recommended_lot", "f_coverage", "f_price", "f_route",
          "f_freshness", "shipped", "delivered_on_time", "actual_spoilage_pct", "buyer_satisfaction",
          "farmer_paid_full", "notes", "recorded_date"]


def outcomes_path(root=None):
    return os.path.join(dataio.data_dir(root), "outcomes.csv")


def validate_row(row):
    """Return a list of error strings (empty = valid)."""
    errs = []
    for c in ("f_coverage", "f_price", "f_route", "f_freshness"):
        try:
            v = float(row[c])
            if not (0.0 <= v <= 1.0):
                errs.append(f"{c} {v} out of [0,1]")
        except (ValueError, KeyError):
            errs.append(f"{c} missing/not a number")
    for b in ("shipped", "delivered_on_time", "farmer_paid_full"):
        if str(row.get(b, "")).lower() not in ("true", "false"):
            errs.append(f"{b} must be true/false")
    try:
        sp = float(row["actual_spoilage_pct"])
        if not (0 <= sp <= 100):
            errs.append("actual_spoilage_pct out of [0,100]")
    except (ValueError, KeyError):
        errs.append("actual_spoilage_pct missing/not a number")
    try:
        sat = int(row["buyer_satisfaction"])
        if not (1 <= sat <= 5):
            errs.append("buyer_satisfaction out of [1,5]")
    except (ValueError, KeyError):
        errs.append("buyer_satisfaction missing/not 1-5")
    return errs


def _factor_snapshot(order_id, root):
    """Pull the winning lot's normalized factors from recommend.json, if available."""
    path = os.path.join(ds.order_dir(order_id, root), "recommend.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        rec = json.load(fh)
    w = rec.get("winner")
    if not w:
        return None
    n = w["normalized"]
    return {"recommended_lot": w["variant"], "f_coverage": n["coverage"], "f_price": n["price"],
            "f_route": n["route"], "f_freshness": n["freshness"]}


def append_outcome(row, root=None):
    errs = validate_row(row)
    if errs:
        raise ValueError("invalid outcome row: " + "; ".join(errs))
    path = outcomes_path(root)
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})
    return row


def _cli(argv=None):
    p = argparse.ArgumentParser(description="Record a realized outcome for an order (M12 calibration).")
    p.add_argument("--order", required=True)
    p.add_argument("--decision-date", default="")
    p.add_argument("--recorded-date", default="")
    p.add_argument("--shipped", required=True)
    p.add_argument("--on-time", required=True)
    p.add_argument("--spoilage", required=True, type=float)
    p.add_argument("--satisfaction", required=True, type=int)
    p.add_argument("--paid-full", required=True)
    p.add_argument("--notes", default="")
    # factor snapshot overrides (else pulled from recommend.json)
    for c in ("coverage", "price", "route", "freshness"):
        p.add_argument(f"--f-{c}", type=float, default=None)
    args = p.parse_args(argv)

    snap = _factor_snapshot(args.order, None) or {}
    row = {
        "order_id": args.order, "decision_date": args.decision_date,
        "recommended_lot": snap.get("recommended_lot", ""),
        "f_coverage": args.f_coverage if args.f_coverage is not None else snap.get("f_coverage", ""),
        "f_price": args.f_price if args.f_price is not None else snap.get("f_price", ""),
        "f_route": args.f_route if args.f_route is not None else snap.get("f_route", ""),
        "f_freshness": args.f_freshness if args.f_freshness is not None else snap.get("f_freshness", ""),
        "shipped": args.shipped, "delivered_on_time": args.on_time,
        "actual_spoilage_pct": args.spoilage, "buyer_satisfaction": args.satisfaction,
        "farmer_paid_full": args.paid_full, "notes": args.notes, "recorded_date": args.recorded_date,
    }
    append_outcome(row)
    print(f"[Outcome] recorded {args.order} -> data/outcomes.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
