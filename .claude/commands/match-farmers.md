---
description: DERA-ZN Evaluate — assemble candidate consolidated lots (cheapest/nearest/reliability) that fill an order from sub-ton farmer declarations.
argument-hint: <order_id>  (e.g. order_001)
---

Assemble candidate lots for order `$1` (DERA-ZN **Evaluate** — lot assembly).

1. Run: `py tools/evaluate.py --order $1` (builds `outputs/$1/evaluate.json` with the candidate lots).
2. Use the **farmer-matcher** skill to interpret `candidates[]`.
3. For each variant (cheapest_first / nearest_first / reliability_first), show the farmer list
   (id · zone · allocated_kg), coverage, and a one-line rationale. Note farmers common to all variants.

Do not rank the winner here (that is `/decision-report`). Cite farmer IDs and kg from `evaluate.json`;
never invent an allocation.
