---
description: DERA-ZN Evaluate — 0%-cut pricing for an order: full farmer payout, transport, handling, spoilage, blended price, and headroom vs the buyer cap.
argument-hint: <order_id>  (e.g. order_001)
---

Price order `$1` (DERA-ZN **Evaluate** — pricing, 0% cut).

1. Run: `py tools/calculate_price.py --order $1` (add `--sweep` to explore the provisional handling fee).
2. Use the **pricing-analyst** skill to interpret the cost build-up for each candidate lot.
3. Present, per lot: farmer payout (KHR + USD, paid in full — 0% cut), transport, handling (provisional
   150 KHR/kg), spoilage buffer, total cost, blended price/kg, and headroom vs cap (feasible?).

Never deduct handling/spoilage from farmer payout. Do not finalize the handling fee — recommend, the
human decides. Cite figures from the tool; no prose arithmetic.
