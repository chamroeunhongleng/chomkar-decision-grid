"""audit_recommendation.py — DERA-ZN auditor gate (M11, deterministic half).

An INDEPENDENT re-check of a decision artifact against the invariants, recomputed from
the raw data (not trusting the pipeline's own numbers). Mirrors the drafter->reviewer
pattern: this is the mechanical reviewer; a fresh AI reviewer agent (the
`recommendation-auditor` skill) adds qualitative critique on top but cannot override a
deterministic FAIL.

Checks for a recommendation:
  - zero_cut          farmer_payout == Σ(ask_from_csv × allocated_kg)  (and artifact asks match CSV)
  - no_overallocation  each farmer's allocated_kg <= declared_qty_kg (from CSV)
  - volume_filled      Σ allocated_kg == order quantity
  - within_cap         blended_price <= buyer cap
  - freshness          spoilage_margin_days >= 0
  - grid_reproduces    re-running the grid on evaluate.json yields the same winner

For a BLOCKED / CANNOT-FULFILL artifact, verifies the block is justified.

A failed check is a hard block: the artifact status is flipped to
"BLOCKED BY AUDIT - pending human review" and an `audit` summary is attached.

Writes outputs/<order>/audit.json. Pure check functions are unit-tested.

Run:  py tools/audit_recommendation.py --order order_001
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dataio
import dera_state as ds
import score_grid as sg

STATUS_AUDIT_BLOCKED = "BLOCKED BY AUDIT - pending human review"


def _chk(name, passed, detail):
    return {"check": name, "passed": bool(passed), "detail": detail}


def audit_recommendation(artifact, farmers, order, evaluate):
    """Pure: return list of check dicts for a recommendation artifact."""
    checks = []
    rec = artifact["recommendation"]
    ask_by_id = {f["farmer_id"]: dataio.to_int(f["ask_price_per_kg_khr"]) for f in farmers}
    declared_by_id = {f["farmer_id"]: dataio.to_int(f["declared_qty_kg"]) for f in farmers}

    # 1. zero-cut: recompute payout from CSV asks; also confirm artifact asks == CSV asks
    recompute = 0
    asks_match = True
    for a in rec["farmers"]:
        csv_ask = ask_by_id.get(a["farmer_id"])
        if csv_ask is None or csv_ask != a["ask_price_per_kg_khr"]:
            asks_match = False
        recompute += (csv_ask or 0) * a["allocated_kg"]
    checks.append(_chk("zero_cut",
                       asks_match and recompute == rec["farmer_payout_khr"],
                       f"recomputed payout {recompute:,} vs artifact {rec['farmer_payout_khr']:,}; "
                       f"asks_match={asks_match}"))

    # 2. no over-allocation beyond declared
    over = [a["farmer_id"] for a in rec["farmers"]
            if a["allocated_kg"] > declared_by_id.get(a["farmer_id"], 0)]
    checks.append(_chk("no_overallocation", not over,
                       "ok" if not over else f"over-allocated farmers: {over}"))

    # 3. volume filled exactly
    total_alloc = sum(a["allocated_kg"] for a in rec["farmers"])
    req = dataio.to_int(order["quantity_kg"])
    checks.append(_chk("volume_filled", total_alloc == req,
                       f"allocated {total_alloc} vs order {req}"))

    # 4. within cap
    cap = dataio.to_int(order["max_price_per_kg_khr"])
    checks.append(_chk("within_cap", rec["blended_price_per_kg_khr"] <= cap,
                       f"blended {rec['blended_price_per_kg_khr']} vs cap {cap}"))

    # 5. freshness margin non-negative
    checks.append(_chk("freshness", rec["spoilage_margin_days"] >= 0,
                       f"spoilage_margin_days = {rec['spoilage_margin_days']}"))

    # 6. grid reproduces the same winner
    grid = sg.build_grid(evaluate.get("candidates", []))
    winner = grid["winner"]["variant"] if grid["winner"] else None
    checks.append(_chk("grid_reproduces", winner == rec["variant"],
                       f"re-run winner {winner} vs artifact {rec['variant']}"))
    return checks


def audit_block(artifact, farmers, order, evaluate):
    """Pure: verify a BLOCKED / CANNOT-FULFILL artifact is justified."""
    status = artifact["status"]
    if status.startswith("BLOCKED"):
        # volume gap: qualifying supply < order qty
        commodity = order["commodity"]
        req = dataio.to_int(order["quantity_kg"])
        import config
        qkg = sum(dataio.to_int(f["declared_qty_kg"]) for f in farmers
                  if f["declared_crop"] == commodity
                  and config.grade_meets(f["quality_grade"], order["quality_required"]))
        return [_chk("block_justified", qkg < req,
                     f"qualifying supply {qkg} vs order {req} (block requires supply < demand)")]
    if status.startswith("CANNOT FULFILL"):
        grid = sg.build_grid(evaluate.get("candidates", []))
        return [_chk("nofill_justified", grid["winner"] is None,
                     "no feasible candidate exists" if grid["winner"] is None
                     else f"a feasible lot exists ({grid['winner']['variant']}) — block NOT justified")]
    return [_chk("status_recognized", False, f"unexpected status {status!r}")]


def run_audit(order_id, root=None):
    art_path = os.path.join(ds.order_dir(order_id, root), f"{order_id}_result.json")
    if not os.path.exists(art_path):
        raise FileNotFoundError(f"{art_path} missing — run Act first.")
    with open(art_path, encoding="utf-8") as fh:
        artifact = json.load(fh)
    farmers = dataio.load_farmers(root)
    order = dataio.get_order(order_id, root=root)
    eval_path = os.path.join(ds.order_dir(order_id, root), "evaluate.json")
    evaluate = {}
    if os.path.exists(eval_path):
        with open(eval_path, encoding="utf-8") as fh:
            evaluate = json.load(fh)

    if artifact.get("recommendation"):
        checks = audit_recommendation(artifact, farmers, order, evaluate)
    else:
        checks = audit_block(artifact, farmers, order, evaluate)

    passed = all(c["passed"] for c in checks)
    issues = [c for c in checks if not c["passed"]]
    audit = {"stage": "audit", "order_id": order_id, "passed": passed,
             "checks": checks, "issues": issues}

    with open(os.path.join(ds.order_dir(order_id, root), "audit.json"), "w", encoding="utf-8") as fh:
        json.dump(audit, fh, indent=2, ensure_ascii=False)

    # Attach to the artifact; flip status on failure (hard block).
    artifact["audit"] = {"passed": passed, "n_issues": len(issues),
                         "issues": [f"{c['check']}: {c['detail']}" for c in issues]}
    if not passed:
        artifact["status"] = STATUS_AUDIT_BLOCKED
        artifact["requires_human_approval"] = [
            "AUDIT FAILED — do NOT act on this recommendation. Review the issues in audit.json."
        ] + artifact.get("requires_human_approval", [])
    with open(art_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2, ensure_ascii=False)
    return audit


def _cli(argv=None):
    p = argparse.ArgumentParser(description="Independently audit a DERA-ZN decision artifact.")
    p.add_argument("--order", required=True)
    args = p.parse_args(argv)
    audit = run_audit(args.order)
    verdict = "PASSED" if audit["passed"] else "FAILED"
    print(f"[Audit] {args.order}: {verdict}")
    for c in audit["checks"]:
        mark = "ok " if c["passed"] else "XX "
        print(f"  {mark}{c['check']}: {c['detail']}")
    return 0 if audit["passed"] else 3


if __name__ == "__main__":
    raise SystemExit(_cli())
