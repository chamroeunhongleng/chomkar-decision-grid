"""run_dera.py — DERA-ZN orchestrator (deterministic backbone for /run-dera).

Runs Detect -> Evaluate -> Recommend -> Act for an order, skipping stages whose inputs
are unchanged (resume), and halting after Detect if it found blockers (a still-emitted
Act artifact records the BLOCKED status). This is the deterministic engine; the
/run-dera slash command wraps it and adds narrative via the skills.

Run:  py tools/run_dera.py --order order_001
      py tools/run_dera.py --order order_001 --force
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_recommendation as au
import evaluate as ev
import generate_report as act
import score_grid as sg
import validate_data as vd


def run(order_id, root=None, force=False, now=None, handling_fee=None):
    steps = []
    detect, skipped = vd.run_detect(order_id, root=root, force=force, now=now)
    steps.append(("detect", detect.get("clean"), skipped))

    if not detect.get("clean", False):
        # Emit the BLOCKED artifact (Act reads detect.json), audit it, and stop.
        act.run_act(order_id, root=root, force=True, now=now)
        audit = au.run_audit(order_id, root=root)
        steps.append(("audit", "PASSED" if audit["passed"] else "FAILED", False))
        # reload artifact (audit may have patched it)
        artifact, _ = act.run_act(order_id, root=root, now=now)
        return {"stopped_at": "detect", "detect": detect, "artifact": artifact,
                "audit": audit, "steps": steps}

    evaluate_res, skipped = ev.run_evaluate(order_id, root=root, handling_fee=handling_fee, force=force, now=now)
    steps.append(("evaluate", evaluate_res.get("n_feasible"), skipped))

    recommend, skipped = sg.run_recommend(order_id, root=root, force=force, now=now)
    steps.append(("recommend", recommend.get("winner") and recommend["winner"]["variant"], skipped))

    act.run_act(order_id, root=root, force=force, now=now)

    # Always-on auditor gate (M11): independent invariant re-check before the human sees it.
    audit = au.run_audit(order_id, root=root)
    steps.append(("audit", "PASSED" if audit["passed"] else "FAILED", False))

    # reload the (possibly audit-patched) artifact for reporting
    artifact = act._load(order_id, root, f"{order_id}_result.json")
    return {"stopped_at": None, "detect": detect, "evaluate": evaluate_res,
            "recommend": recommend, "artifact": artifact, "audit": audit, "steps": steps}


def _cli(argv=None):
    p = argparse.ArgumentParser(description="Run the full DERA-ZN loop for an order (resumable).")
    p.add_argument("--order", required=True)
    p.add_argument("--force", action="store_true", help="ignore resume cache; recompute all stages")
    p.add_argument("--handling-fee", type=int, default=None)
    p.add_argument("--now")
    args = p.parse_args(argv)

    res = run(args.order, force=args.force, handling_fee=args.handling_fee, now=args.now)
    print(f"=== DERA-ZN: {args.order} ===")
    for name, info, skipped in res["steps"]:
        tag = " (cached)" if skipped else ""
        print(f"  {name:>10}: {info}{tag}")
    art = res["artifact"]
    if art.get("audit"):
        a = art["audit"]
        print(f"\nAudit gate: {'PASSED' if a['passed'] else 'FAILED'}"
              + ("" if a["passed"] else f" — {a['issues']}"))
    print(f"\nStatus: {art['status']}")
    if art.get("recommendation"):
        r = art["recommendation"]
        print(f"Recommended lot: {r['variant']} — {r['n_farmers']} farmers, {r['total_kg']:,} kg, "
              f"payout {r['farmer_payout_khr']:,} KHR, blended {r['blended_price_per_kg_khr']:,} KHR/kg, "
              f"headroom {r['headroom_per_kg_khr']:,} KHR/kg")
    print("Requires human approval:")
    for a in art["requires_human_approval"]:
        print(f"  - {a}")
    print(f"\nReport: reports/{args.order}_decision_report.md")
    return 2 if res["stopped_at"] else 0


if __name__ == "__main__":
    raise SystemExit(_cli())
