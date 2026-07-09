---
description: DERA-ZN Detect — audit a buyer order + farmers' declared supply and run the volume-gap check for one order.
argument-hint: <order_id>  (e.g. order_001)
---

Audit order `$1` (DERA-ZN **Detect** stage).

1. Run: `py tools/validate_data.py --order $1` (writes `outputs/$1/detect.json`).
2. Use the **data-auditor** skill to interpret `outputs/$1/detect.json`.
3. Report: clean/blocked verdict, supply vs demand (qualifying kg vs order qty), each blocker, warnings,
   and the recommended next step.

If a blocker like `VOLUME_GAP` is present, stop and recommend renegotiating quantity/grade/timeline — do
not proceed to matching or pricing. Cite numbers from `detect.json`; do not compute them in prose.
