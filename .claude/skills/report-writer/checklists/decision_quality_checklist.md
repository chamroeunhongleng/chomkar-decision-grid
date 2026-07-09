# Decision-quality checklist (report-writer)

Run before presenting any decision report. All items must pass; report pass/fail.

## Source of truth
- [ ] Every figure in the report was read from `outputs/<order_id>/<order_id>_result.json` — none computed in prose.
- [ ] Re-running the pipeline on unchanged inputs would produce the same numbers (deterministic).

## 0% cut & payouts
- [ ] Farmer payout table sums to Σ(ask_price × allocated_kg).
- [ ] Handling fee and spoilage buffer are shown as platform-borne lines, not deducted from farmers.
- [ ] Handling fee is labelled provisional (150 KHR/kg).

## Feasibility & honesty
- [ ] Recommended lot fills the order quantity (coverage 1.0) with multiple farmers (volume gap closed).
- [ ] `blended_price ≤ buyer_cap`; if not, the report says "cannot fulfill — renegotiate", not a shipped lot.
- [ ] A blocked/infeasible order is presented as such — no fabricated recommendation.

## Presentation
- [ ] Bilingual (Khmer + English) and readable by a non-technical co-op officer.
- [ ] Every KHR figure has a USD equivalent.
- [ ] Status shown verbatim (`RECOMMENDATION - pending human approval` / `BLOCKED ...` / `CANNOT FULFILL ...`).

## Approval gate
- [ ] The "Requires human approval" section is present and left as pending (unchecked) items.
- [ ] The report does not approve, commit, or finalize anything on the human's behalf.
