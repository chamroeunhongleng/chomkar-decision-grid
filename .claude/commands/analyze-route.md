---
description: DERA-ZN Evaluate — transport & perishability risk for an order's candidate lots: transit, heat, road, flood, refrigeration, and spoilage margin.
argument-hint: <order_id>  (e.g. order_001)
---

Analyze route risk for order `$1` (DERA-ZN **Evaluate** — route & perishability).

1. Run: `py tools/route_risk.py --order $1` (or read the `route` block of `outputs/$1/evaluate.json`).
2. Use the **route-risk-analyst** skill to interpret it.
3. Present, per candidate lot: route_risk (0–1), spoilage margin (days), the main risk drivers, the
   delivery-zone weather used, and whether a refrigerated route is warranted.

Flag any small or negative spoilage margin. Cite risk numbers and weather from the tool; never estimate
them in prose.
