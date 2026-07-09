---
description: DERA-ZN Recommend + Act — build the zone-normalized decision grid and produce the final bilingual decision report for an order (pending human approval).
argument-hint: <order_id>  (e.g. order_001)
---

Produce the decision report for order `$1` (DERA-ZN **Recommend + Act**).

Run only after Detect + Evaluate exist for the order (or run `/run-dera $1` for the whole loop).

1. Recommend: `py tools/score_grid.py --order $1` → `outputs/$1/recommend.json`.
   Use the **decision-grid** skill to explain the ranking and why the winner won.
2. Act: `py tools/generate_report.py --order $1` → `outputs/$1/$1_result.json` +
   `reports/$1_decision_report.md`. Use the **report-writer** skill to present it.
3. Present the bilingual report: status (verbatim), recommended lot, **0%-cut farmer payout table**,
   price build-up, ranked grid.
4. **Always end** with the artifact's **"Requires human approval"** checklist as pending items.

If no lot is feasible (or the order was blocked at Detect), present that plainly and recommend
renegotiation. **Never** approve or commit on the user's behalf — Claude recommends, the human approves.
