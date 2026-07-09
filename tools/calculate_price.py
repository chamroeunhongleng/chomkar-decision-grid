"""calculate_price.py — DERA-ZN Evaluate: auditable pricing for a candidate lot.

Implements the 0%-cut cost build-up from docs/business_rules.md §1. The invariant:
farmers are paid their full declared ask (farmer_payout = Σ ask*kg); handling and
spoilage are platform-borne and added ON TOP, never deducted from farmers.

    farmer_payout   = Σ (ask_price * allocated_kg)
    transport_cost  = Σ (route_cost_per_kg * allocated_kg)   [farmer zone -> delivery zone]
    handling_cost   = handling_fee_per_kg * total_kg
    spoilage_buffer = spoilage_pct * farmer_payout
    total_cost      = farmer_payout + transport + handling + spoilage_buffer
    blended_price   = total_cost / total_kg
    headroom        = buyer_max_price - blended_price        [>=0 => feasible]

price_lot() is pure (easy to unit-test). The CLI assembles the 3 candidate lots for an
order, prices each, and supports --handling-fee (override) and --sweep (sensitivity), so
the provisional handling fee can be informed by the data rather than guessed.

Run:
    py tools/calculate_price.py --order order_001
    py tools/calculate_price.py --order order_001 --handling-fee 100
    py tools/calculate_price.py --order order_001 --sweep
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble_lots
import config
import dataio


def price_lot(lot, order, transport, handling_fee=None, spoilage_pct=None):
    """Pure 0%-cut cost build-up for one candidate lot. Returns a pricing dict."""
    handling_fee = config.HANDLING_FEE_PER_KG if handling_fee is None else handling_fee
    spoilage_pct = config.SPOILAGE_BUFFER_PCT if spoilage_pct is None else spoilage_pct

    routes = assemble_lots._transport_lookup(transport)
    delivery_zone = lot["delivery_zone"]
    cap = dataio.to_int(order["max_price_per_kg_khr"])

    farmer_payout = 0
    transport_cost = 0
    missing_routes = []
    for a in lot["allocations"]:
        farmer_payout += a["ask_price_per_kg_khr"] * a["allocated_kg"]
        r = routes.get((a["zone"], delivery_zone))
        if r is None:
            missing_routes.append(a["zone"])
        else:
            transport_cost += r["cost_per_kg_khr"] * a["allocated_kg"]

    total_kg = lot["total_kg"]
    handling_cost = round(handling_fee * total_kg)
    spoilage_buffer = round(spoilage_pct * farmer_payout)
    total_cost = farmer_payout + transport_cost + handling_cost + spoilage_buffer
    blended_price = round(total_cost / total_kg, 2) if total_kg else 0.0
    headroom = round(cap - blended_price, 2)

    return {
        "variant": lot["variant"],
        "total_kg": total_kg,
        "buyer_max_price_per_kg_khr": cap,
        # --- cost build-up (KHR) ---
        "farmer_payout_khr": farmer_payout,          # 0% cut: paid in full
        "transport_cost_khr": transport_cost,
        "handling_cost_khr": handling_cost,
        "spoilage_buffer_khr": spoilage_buffer,
        "total_cost_khr": total_cost,
        "blended_price_per_kg_khr": blended_price,
        "headroom_per_kg_khr": headroom,
        "feasible": headroom >= 0 and not missing_routes,
        # --- params + USD mirror (display) ---
        "params": {"handling_fee_per_kg_khr": handling_fee, "spoilage_buffer_pct": spoilage_pct},
        "usd": {
            "farmer_payout": config.khr_to_usd(farmer_payout),
            "total_cost": config.khr_to_usd(total_cost),
            "blended_price_per_kg": config.khr_to_usd(blended_price),
        },
        "transport_data_gap": missing_routes,
        # --- auditable breakdown (facts -> formula -> result) ---
        "breakdown": [
            f"farmer_payout = Σ(ask×kg) = {farmer_payout:,} KHR  (0% cut — paid in full)",
            f"transport = Σ(route_cost×kg) = {transport_cost:,} KHR",
            f"handling = {handling_fee}×{total_kg} = {handling_cost:,} KHR",
            f"spoilage_buffer = {spoilage_pct:.0%}×payout = {spoilage_buffer:,} KHR",
            f"total_cost = {total_cost:,} KHR ; blended = total/{total_kg} = {blended_price:,} KHR/kg",
            f"headroom = cap({cap:,}) − blended({blended_price:,}) = {headroom:,} KHR/kg "
            f"→ {'FEASIBLE' if headroom >= 0 else 'OVER CAP'}",
        ],
    }


def price_order(order_id, root=None, handling_fee=None):
    """Assemble candidate lots for an order and price each. Returns (order, priced_lots)."""
    farmers = dataio.load_farmers(root)
    orders = dataio.load_orders(root)
    transport = dataio.load_transport(root)
    order = dataio.get_order(order_id, orders)
    lots = assemble_lots.build_candidates(order, farmers, transport)
    priced = [{"lot": lot, "pricing": price_lot(lot, order, transport, handling_fee=handling_fee)}
              for lot in lots]
    return order, priced


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _print_priced(order, priced):
    print(f"[Price] {order['order_id']}: {order['commodity']} {order['quantity_kg']} kg, "
          f"cap {int(order['max_price_per_kg_khr']):,} KHR/kg → {order['delivery_province']}:{order['delivery_commune']}")
    for p in priced:
        pr, lot = p["pricing"], p["lot"]
        who = ", ".join(f"{a['farmer_id']}:{a['allocated_kg']}kg" for a in lot["allocations"])
        flag = "FEASIBLE" if pr["feasible"] else "OVER CAP"
        print(f"\n  variant={pr['variant']}  [{flag}]  coverage={lot['coverage']}")
        print(f"    lot: {who}")
        print(f"    farmer_payout={pr['farmer_payout_khr']:,}  transport={pr['transport_cost_khr']:,}  "
              f"handling={pr['handling_cost_khr']:,}  spoilage={pr['spoilage_buffer_khr']:,}")
        print(f"    blended={pr['blended_price_per_kg_khr']:,} KHR/kg  "
              f"(${pr['usd']['blended_price_per_kg']}/kg)  headroom={pr['headroom_per_kg_khr']:,} KHR/kg")


def _print_sweep(order, root, fees):
    farmers = dataio.load_farmers(root)
    transport = dataio.load_transport(root)
    lot = assemble_lots.build_lot(order, farmers, transport, "cheapest_first")
    cap = int(order["max_price_per_kg_khr"])
    print(f"[Sweep] {order['order_id']} cheapest_first lot; buyer cap {cap:,} KHR/kg")
    print(f"  {'handling':>10} | {'blended':>10} | {'headroom':>10} | feasible")
    for fee in fees:
        pr = price_lot(lot, order, transport, handling_fee=fee)
        print(f"  {fee:>10} | {pr['blended_price_per_kg_khr']:>10,} | "
              f"{pr['headroom_per_kg_khr']:>10,} | {pr['feasible']}")


def _cli(argv=None):
    p = argparse.ArgumentParser(description="DERA-ZN Evaluate: price candidate lots (0% cut).")
    p.add_argument("--order", required=True)
    p.add_argument("--handling-fee", type=int, default=None, help="override HANDLING_FEE_PER_KG (KHR/kg)")
    p.add_argument("--sweep", action="store_true", help="handling-fee sensitivity on the cheapest lot")
    args = p.parse_args(argv)

    orders = dataio.load_orders()
    order = dataio.get_order(args.order, orders)
    if args.sweep:
        _print_sweep(order, None, [0, 50, 100, 150, 200, 250, 300])
        return 0
    order, priced = price_order(args.order, handling_fee=args.handling_fee)
    _print_priced(order, priced)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
