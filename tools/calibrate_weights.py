"""calibrate_weights.py — DERA-ZN M12: PROPOSE grid-weight nudges from real outcomes.

Reads data/outcomes.csv, measures how each decision factor (coverage/price/route/freshness)
correlated with realized success, and proposes a small, bounded weight nudge per factor
(±CALIBRATION_STEP, renormalized to sum 1.0).

**Proposal only — this NEVER edits docs/business_rules.md or config.py.** A human approves a
change by editing those files. This tool writes outputs/calibration_proposal.json and prints
the current → proposed weights with the evidence.

Deterministic; pure propose_weights() is unit-tested.

Run:  py tools/calibrate_weights.py
"""
import argparse
import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import dataio

FACTORS = ("coverage", "price", "route", "freshness")


def _success(row):
    """Realized success in [0,1] from a ledger row (mean of available signals)."""
    signals = []
    for b in ("shipped", "delivered_on_time", "farmer_paid_full"):
        signals.append(1.0 if str(row.get(b, "")).lower() == "true" else 0.0)
    try:
        signals.append(1.0 - float(row["actual_spoilage_pct"]) / 100.0)
    except (ValueError, KeyError):
        pass
    try:
        signals.append(int(row["buyer_satisfaction"]) / 5.0)
    except (ValueError, KeyError):
        pass
    return sum(signals) / len(signals) if signals else 0.0


def _pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    sx = sum((x - mx) ** 2 for x in xs)
    sy = sum((y - my) ** 2 for y in ys)
    if sx == 0 or sy == 0:  # a constant factor (e.g. coverage always 1.0) → no signal
        return 0.0
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / math.sqrt(sx * sy)


def propose_weights(outcomes, current=None, step=None):
    """Pure: return a proposal dict. Does not write anything."""
    current = dict(current or config.GRID_WEIGHTS)
    step = config.CALIBRATION_STEP if step is None else step
    n = len(outcomes)
    if n < config.MIN_OUTCOMES_TO_CALIBRATE:
        return {"insufficient": True, "n_outcomes": n,
                "note": f"need >= {config.MIN_OUTCOMES_TO_CALIBRATE} outcomes to calibrate (have {n}).",
                "current": current, "proposed": current, "per_factor": []}

    succ = [_success(r) for r in outcomes]
    per_factor, proposed_raw = [], {}
    for f in FACTORS:
        vals = [float(r[f"f_{f}"]) for r in outcomes]
        corr = _pearson(vals, succ)
        nudge = round(step * corr, 4)                       # bounded to ±step
        prop = max(config.WEIGHT_FLOOR, round(current[f] + nudge, 4))
        proposed_raw[f] = prop
        direction = "up" if nudge > 0 else ("down" if nudge < 0 else "hold")
        per_factor.append({"factor": f, "corr_with_success": round(corr, 3), "nudge": nudge,
                           "current": current[f], "proposed_pre_norm": prop,
                           "rationale": f"{f} correlated {corr:+.2f} with good outcomes → weight {direction}"})

    # renormalize to sum 1.0
    total = sum(proposed_raw.values())
    proposed = {f: round(proposed_raw[f] / total, 4) for f in FACTORS}

    return {"insufficient": False, "n_outcomes": n, "mean_success": round(sum(succ) / n, 3),
            "current": current, "proposed": proposed, "per_factor": per_factor,
            "note": "PROPOSAL ONLY — a human approves by editing docs/business_rules.md §3 and config.GRID_WEIGHTS."}


def load_outcomes(root=None):
    path = os.path.join(dataio.data_dir(root), "outcomes.csv")
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def run(root=None):
    proposal = propose_weights(load_outcomes(root))
    out_dir = os.path.join(dataio.repo_root(root), "outputs")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "calibration_proposal.json"), "w", encoding="utf-8") as fh:
        json.dump(proposal, fh, indent=2, ensure_ascii=False)
    return proposal


def _cli(argv=None):
    argparse.ArgumentParser(description="Propose grid-weight nudges from outcomes (proposal only).").parse_args(argv)
    p = run()
    if p.get("insufficient"):
        print(f"[Calibrate] {p['note']}")
        return 0
    print(f"[Calibrate] {p['n_outcomes']} outcomes, mean success {p['mean_success']}")
    print(f"  {'factor':>10} | {'corr':>6} | {'current':>8} | {'proposed':>8}")
    for r in p["per_factor"]:
        f = r["factor"]
        print(f"  {f:>10} | {r['corr_with_success']:>6} | {p['current'][f]:>8} | {p['proposed'][f]:>8}")
    print(f"\n  {p['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
