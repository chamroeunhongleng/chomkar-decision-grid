---
description: Run the full DERA-ZN decision loop (Detect→Evaluate→Recommend→Act) for an order — resumable, ends with a recommendation pending your approval.
argument-hint: <order_id>  (e.g. order_001)
---

Run the full **DERA-ZN** decision loop for order `$1`.

Use the deterministic orchestrator, then narrate with the skills. **Claude recommends; a human approves —
never approve or commit on the user's behalf.**

1. Execute: `py tools/run_dera.py --order $1`
   (This runs Detect→Evaluate→Recommend→Act, skips unchanged stages, and halts after Detect if blocked.
   On Windows use `py`; elsewhere `python`.)
2. If it **stopped at Detect** (a blocker like `VOLUME_GAP`): use the **data-auditor** skill to explain
   the blocker and recommend renegotiating quantity/grade/timeline. Stop — do not fabricate a lot.
3. If it completed: read `outputs/$1/$1_result.json` and `reports/$1_decision_report.md`, then present:
   - the recommended lot and **0%-cut farmer payouts** (use **report-writer**),
   - the ranked decision grid and why the winner won (use **decision-grid**),
   - price headroom (use **pricing-analyst**) and route/spoilage risk (use **route-risk-analyst**).
4. **Always end** with the artifact's **"Requires human approval"** checklist as pending items.

Cite only numbers from the tool outputs — never compute figures in prose.
