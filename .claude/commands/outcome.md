---
description: DERA-ZN M12 — record a Chomkar order's real delivery outcome, then (if enough data) surface a proposed grid-weight recalibration for human approval.
argument-hint: <order_id>  (then the observed result)
---

Record the real outcome for order `$1` and check for a calibration proposal (DERA-ZN **learning loop**).

1. Ask the user for what actually happened (or take it from their message): shipped? delivered on time?
   spoilage %? buyer satisfaction (1–5)? farmers paid in full? Then run:
   `py tools/record_outcome.py --order $1 --shipped <t/f> --on-time <t/f> --spoilage <pct> \
    --satisfaction <1-5> --paid-full <t/f> --notes "<short note>"`
   (This appends to `data/outcomes.csv`, snapshotting the winning lot's decision factors.)
2. Run `py tools/calibrate_weights.py` and use the **calibration-analyst** skill to explain the result.
3. If ≥ 3 outcomes exist, present the **current → proposed** grid weights and the evidence
   (which factors correlated with good/bad outcomes).

**This is a proposal only.** Applying new weights is a human decision — the user edits
`docs/business_rules.md §3` and `config.GRID_WEIGHTS`. Never change the weights yourself; never record a
fabricated outcome.
