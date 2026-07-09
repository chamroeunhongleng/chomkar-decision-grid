"""generate_report.py — DERA-ZN stage A (Act): decision artifact + bilingual report.

Reads detect.json + evaluate.json + recommend.json and emits:
  - outputs/<order>/<order>_result.json  — machine artifact, status
        "RECOMMENDATION - pending human approval"  (never auto-approved)
  - reports/<order>_decision_report.md    — bilingual (Khmer + English) report,
        structured Facts / Assumptions / Formulas / Recommendation / Requires human approval

Deterministic; skills add narrative on top but the numbers come from here. Handles
resume state. If Detect blocked the order, or no lot is feasible, the artifact says so
and recommends renegotiation rather than presenting a false recommendation.

Run:  py tools/generate_report.py --order order_001
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import dataio
import dera_state as ds

STAGE = "act"
STATUS_REC = "RECOMMENDATION - pending human approval"
STATUS_BLOCKED = "BLOCKED - pending human review"
STATUS_NOFILL = "CANNOT FULFILL - pending human review"


def _load(order_id, root, name):
    path = os.path.join(ds.order_dir(order_id, root), name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build_artifact(order_id, order, detect, evaluate, recommend):
    """Assemble the machine decision artifact (pure)."""
    assumptions = [
        "Farmers are paid their full declared ask price (0% platform cut).",
        f"Handling fee {config.HANDLING_FEE_PER_KG} KHR/kg is platform-borne and PROVISIONAL (tunable).",
        f"Spoilage buffer is {config.SPOILAGE_BUFFER_PCT:.0%} of farmer payout.",
        "Route risk uses weather at the delivery zone on the delivery date.",
        "All data is SYNTHETIC — not real farmers, buyers, or payments.",
    ]
    formulas = [
        "farmer_payout = Σ(ask_price × allocated_kg)   [0% cut]",
        "total_cost = farmer_payout + transport + handling + spoilage_buffer",
        "blended_price = total_cost / total_kg ; headroom = buyer_cap − blended_price",
        "route_risk = Σ w·(transit,perish,heat,road,flood) − refrig_relief   [0..1]",
        "grid score = Σ W·zone_normalized(coverage, price, route, freshness)",
    ]

    art = {
        "artifact": "dera_zn_decision",
        "order_id": order_id,
        "status": STATUS_REC,
        "order": {
            "buyer": order.get("buyer_name"),
            "commodity": order.get("commodity"),
            "quantity_kg": dataio.to_int(order["quantity_kg"]),
            "quality_required": order.get("quality_required"),
            "max_price_per_kg_khr": dataio.to_int(order["max_price_per_kg_khr"]),
            "delivery": f"{order.get('delivery_province')}:{order.get('delivery_commune')}",
            "delivery_date": order.get("delivery_date"),
            "perishability_days": dataio.to_int(order["perishability_days"]),
        },
        "detect": {
            "clean": detect.get("clean") if detect else None,
            "blockers": detect.get("blockers", []) if detect else [],
            "warnings": detect.get("warnings", []) if detect else [],
            "supply": detect.get("supply") if detect else None,
        },
        "assumptions": assumptions,
        "formulas": formulas,
        "params_used": {
            "handling_fee_per_kg_khr": config.HANDLING_FEE_PER_KG,
            "spoilage_buffer_pct": config.SPOILAGE_BUFFER_PCT,
            "route_risk_weights": config.ROUTE_RISK_WEIGHTS,
            "grid_weights": config.GRID_WEIGHTS,
            "khr_per_usd": config.KHR_PER_USD,
        },
        "grid_ranking": [],
        "recommendation": None,
        "requires_human_approval": [],
    }

    # Blocked at Detect?
    if detect and not detect.get("clean", True):
        art["status"] = STATUS_BLOCKED
        art["requires_human_approval"] = [
            "Detect found blockers (see detect.blockers). Decide whether to renegotiate the order "
            "(quantity, grade, timeline) or reject it."]
        return art

    winner = recommend.get("winner") if recommend else None
    art["grid_ranking"] = [
        {"variant": r["variant"], "score": r["score"], "blended_price_per_kg_khr": r["blended_price_per_kg_khr"],
         "headroom_per_kg_khr": r["headroom_per_kg_khr"], "route_risk": r["route_risk"],
         "spoilage_margin_days": r["spoilage_margin_days"]}
        for r in (recommend.get("ranked", []) if recommend else [])]

    if not winner:
        art["status"] = STATUS_NOFILL
        art["requires_human_approval"] = [
            "No candidate lot is feasible within the buyer's price cap. Decide whether to renegotiate "
            "the cap/quantity or decline."]
        return art

    # Pull the winning lot's allocations + pricing from evaluate.json
    cand = next((c for c in evaluate.get("candidates", []) if c["variant"] == winner["variant"]), None)
    farmers_pay = []
    if cand:
        for a in cand["allocations"]:
            payout = a["ask_price_per_kg_khr"] * a["allocated_kg"]
            farmers_pay.append({
                "farmer_id": a["farmer_id"], "zone": a["zone"], "grade": a.get("grade"),
                "allocated_kg": a["allocated_kg"], "ask_price_per_kg_khr": a["ask_price_per_kg_khr"],
                "payout_khr": payout, "payout_usd": config.khr_to_usd(payout),
            })
    pricing = cand["pricing"] if cand else {}

    art["recommendation"] = {
        "variant": winner["variant"],
        "score": winner["score"],
        "n_farmers": winner["n_farmers"],
        "total_kg": cand["pricing"]["total_kg"] if cand else None,
        "farmers": farmers_pay,
        "farmer_payout_khr": pricing.get("farmer_payout_khr"),
        "farmer_payout_usd": config.khr_to_usd(pricing.get("farmer_payout_khr", 0)),
        "transport_cost_khr": pricing.get("transport_cost_khr"),
        "handling_cost_khr": pricing.get("handling_cost_khr"),
        "spoilage_buffer_khr": pricing.get("spoilage_buffer_khr"),
        "total_cost_khr": pricing.get("total_cost_khr"),
        "blended_price_per_kg_khr": pricing.get("blended_price_per_kg_khr"),
        "buyer_max_price_per_kg_khr": pricing.get("buyer_max_price_per_kg_khr"),
        "headroom_per_kg_khr": pricing.get("headroom_per_kg_khr"),
        "route_risk": winner["route_risk"],
        "spoilage_margin_days": winner["spoilage_margin_days"],
        "breakdown": pricing.get("breakdown", []),
    }
    approvals = [
        "Approve this lot and the per-farmer payouts before committing to the buyer.",
        f"Confirm the handling fee (currently provisional {config.HANDLING_FEE_PER_KG} KHR/kg).",
        "Confirm delivery logistics / refrigeration for the recommended route.",
    ]
    if pricing.get("headroom_per_kg_khr", 0) < 100:
        approvals.insert(0, f"NOTE: headroom is thin ({pricing.get('headroom_per_kg_khr')} KHR/kg) — "
                            "confirm the price is acceptable.")
    art["requires_human_approval"] = approvals
    return art


# --------------------------------------------------------------------------- #
# Bilingual (Khmer + English) markdown rendering
# --------------------------------------------------------------------------- #
def render_markdown(art):
    o = art["order"]
    lines = []
    add = lines.append
    add(f"# Decision Report — {art['order_id']}  ·  របាយការណ៍សម្រេចចិត្ត")
    add("")
    add(f"> **Status / ស្ថានភាព:** `{art['status']}`")
    add("> _Claude recommends; a human approves. / Claude ណែនាំ មនុស្សអនុម័ត។_")
    add("")
    add("## Order / ការបញ្ជាទិញ")
    add(f"- **Buyer / អ្នកទិញ:** {o['buyer']}")
    add(f"- **Commodity / ទំនិញ:** {o['commodity']} — **{o['quantity_kg']:,} kg**, grade ≥ {o['quality_required']}")
    add(f"- **Price cap / ពិដានតម្លៃ:** {o['max_price_per_kg_khr']:,} KHR/kg (${config.khr_to_usd(o['max_price_per_kg_khr'])})")
    add(f"- **Delivery / ការដឹកជញ្ជូន:** {o['delivery']} on {o['delivery_date']} · perishability {o['perishability_days']}d")
    add("")

    # Detect summary
    d = art["detect"]
    add("## Detect / ការត្រួតពិនិត្យ")
    if d.get("supply"):
        s = d["supply"]
        add(f"- Supply / ការផ្គត់ផ្គង់: **{s['qualifying_kg']:,} kg** of {s['commodity']} at grade ≥ "
            f"{s['quality_required']} from {s['n_qualifying_farmers']} farmers (needs {s['required_qty_kg']:,} kg).")
    if d.get("blockers"):
        add("- **Blockers / ឧបសគ្គ:**")
        for b in d["blockers"]:
            add(f"  - `{b['code']}` — {b['message']}")
    else:
        add("- No blockers. / គ្មានឧបសគ្គ។")
    add("")

    rec = art["recommendation"]
    if rec:
        add("## Recommendation / អនុសាសន៍")
        add(f"**Recommended lot / ឡូតុំដែលបានណែនាំ:** `{rec['variant']}` "
            f"(grid score {rec['score']}) — {rec['n_farmers']} farmers, {rec['total_kg']:,} kg.")
        add("")
        add("### Farmer payouts / ការទូទាត់ដល់កសិករ (0% cut — paid in full / បង់ពេញ)")
        add("| Farmer | Zone | kg | Ask KHR/kg | Payout KHR | Payout USD |")
        add("|---|---|---:|---:|---:|---:|")
        for f in rec["farmers"]:
            add(f"| {f['farmer_id']} | {f['zone']} | {f['allocated_kg']:,} | {f['ask_price_per_kg_khr']:,} "
                f"| {f['payout_khr']:,} | ${f['payout_usd']} |")
        add(f"| **Total / សរុប** |  | **{rec['total_kg']:,}** |  | **{rec['farmer_payout_khr']:,}** "
            f"| **${rec['farmer_payout_usd']}** |")
        add("")
        add("### Price build-up / ការគណនាតម្លៃ")
        for step in rec["breakdown"]:
            add(f"- {step}")
        add("")
        add(f"- **Blended price / តម្លៃលាយ:** {rec['blended_price_per_kg_khr']:,} KHR/kg "
            f"vs cap {rec['buyer_max_price_per_kg_khr']:,} → **headroom {rec['headroom_per_kg_khr']:,} KHR/kg**")
        add(f"- **Route risk / ហានិភ័យផ្លូវ:** {rec['route_risk']} · "
            f"**spoilage margin / រយៈពេលនៅស្រស់:** {rec['spoilage_margin_days']} days")
        add("")

    # Grid ranking
    if art["grid_ranking"]:
        add("### Decision grid / តារាងសម្រេចចិត្ត (all candidates)")
        add("| Rank | Variant | Score | Blended KHR/kg | Headroom | Route risk | Spoilage margin |")
        add("|---:|---|---:|---:|---:|---:|---:|")
        for i, r in enumerate(art["grid_ranking"], 1):
            add(f"| {i} | {r['variant']} | {r['score']} | {r['blended_price_per_kg_khr']:,} "
                f"| {r['headroom_per_kg_khr']:,} | {r['route_risk']} | {r['spoilage_margin_days']} |")
        add("")

    add("## Assumptions / ការសន្មត")
    for a in art["assumptions"]:
        add(f"- {a}")
    add("")
    add("## Formulas used / រូបមន្តដែលបានប្រើ")
    for f in art["formulas"]:
        add(f"- `{f}`")
    add("")
    add("## ⚠️ Requires human approval / ត្រូវការការអនុម័តពីមនុស្ស")
    for r in art["requires_human_approval"]:
        add(f"- [ ] {r}")
    add("")
    add("---")
    add(f"_Params: handling {art['params_used']['handling_fee_per_kg_khr']} KHR/kg · "
        f"spoilage {art['params_used']['spoilage_buffer_pct']:.0%} · "
        f"grid {art['params_used']['grid_weights']} · rate {art['params_used']['khr_per_usd']} KHR/USD._")
    add("_Generated by chomkar-decision-grid (DERA-ZN). Synthetic data. / "
        "បង្កើតដោយ chomkar-decision-grid ។ ទិន្នន័យសាកល្បង។_")
    return "\n".join(lines) + "\n"


def run_act(order_id, root=None, force=False, now=None, report_name=None):
    order = dataio.get_order(order_id, root=root)
    detect = _load(order_id, root, "detect.json")
    evaluate = _load(order_id, root, "evaluate.json")
    recommend = _load(order_id, root, "recommend.json")

    input_hash = ds.hash_inputs("act", detect, recommend, config.HANDLING_FEE_PER_KG)
    state = ds.load_state(order_id, root)
    result_path = os.path.join(ds.order_dir(order_id, root), f"{order_id}_result.json")
    if not force and not ds.should_run(state, STAGE, input_hash) and os.path.exists(result_path):
        with open(result_path, encoding="utf-8") as fh:
            return json.load(fh), True

    art = build_artifact(order_id, order, detect, evaluate, recommend)

    os.makedirs(ds.order_dir(order_id, root), exist_ok=True)
    with open(result_path, "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, ensure_ascii=False)

    reports_dir = os.path.join(dataio.repo_root(root), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, report_name or f"{order_id}_decision_report.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(art))

    ds.mark_done(state, STAGE, f"{order_id}_result.json", input_hash, now=now)
    ds.save_state(state, root, now=now)
    return art, False


def _cli(argv=None):
    p = argparse.ArgumentParser(description="DERA-ZN Act: decision artifact + bilingual report.")
    p.add_argument("--order", required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--now")
    p.add_argument("--report-name", help="override report filename in reports/")
    args = p.parse_args(argv)
    art, skipped = run_act(args.order, force=args.force, now=args.now, report_name=args.report_name)
    tag = " (resumed / cached)" if skipped else ""
    print(f"[Act] {art['order_id']}: {art['status']}{tag}")
    if art["recommendation"]:
        r = art["recommendation"]
        print(f"  recommend {r['variant']}: {r['n_farmers']} farmers, {r['total_kg']:,} kg, "
              f"payout {r['farmer_payout_khr']:,} KHR, blended {r['blended_price_per_kg_khr']:,} KHR/kg, "
              f"headroom {r['headroom_per_kg_khr']:,}")
    print(f"  artifact: outputs/{art['order_id']}/{art['order_id']}_result.json")
    print(f"  report:   reports/{args.report_name or art['order_id'] + '_decision_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
