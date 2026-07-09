# Pricing formulas — 0% cut (reference for pricing-analyst)

Canonical source: [docs/business_rules.md §1](../../../docs/business_rules.md). Implemented deterministically
by [`tools/calculate_price.py`](../../../tools/calculate_price.py). **Do not compute these in prose — read
the results from the tool.** This file exists so the skill body stays short.

## Invariant
```
farmer_payout = Σ (ask_price_per_kg × allocated_kg)      # 0% platform cut — farmers paid in full
```
Handling and spoilage are **platform-borne** and added on top; they are NEVER subtracted from
farmer_payout.

## Cost build-up (per candidate lot)
```
transport_cost  = Σ (route_cost_per_kg × allocated_kg)          # farmer zone -> delivery zone
handling_cost   = HANDLING_FEE_PER_KG × total_kg                # PROVISIONAL 150 KHR/kg (tunable)
spoilage_buffer = SPOILAGE_BUFFER_PCT × farmer_payout           # 5% (approved)
total_cost      = farmer_payout + transport_cost + handling_cost + spoilage_buffer
blended_price   = total_cost / total_kg
headroom        = buyer_max_price_per_kg − blended_price        # >= 0 => FEASIBLE
usd             = khr_amount / KHR_PER_USD                       # 4000 KHR/USD (display)
```

## Feasibility
- `headroom >= 0` → the lot fits under the buyer's cap.
- `headroom < 0` → "cannot fulfill within cap — recommend renegotiate" (do NOT ship at a loss).

## What this model is NOT
This is a 0%-cut coordination model, matching chomkar.com. It intentionally has **no platform margin,
no cooperator fee, no profit split**. If a margin/fee model is ever wanted, that is a business change
requiring a human decision (a new approval gate) and an edit to docs/business_rules.md — not something
the skill decides.
