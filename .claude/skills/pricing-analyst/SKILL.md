---
description: Use this skill to explain the 0%-cut cost build-up for a Chomkar order — full farmer payout, transport, handling, spoilage buffer, blended price, and headroom vs the buyer cap — and whether the lot is feasible. DERA-ZN Evaluate stage — pricing.
argument-hint: [order_id]
---

# Pricing Analyst Skill — DERA-ZN stage E (pricing, 0% cut)

## Goal
Produce an explainable price for one order under the **0% platform cut** model and confirm farmers are
paid in full. One job: pricing. Not matching, not routing, not reporting.

## Inputs
- `order_id`.
- Reads: the `pricing` block of each candidate in `outputs/<order_id>/evaluate.json`, or the live output
  of `py tools/calculate_price.py --order <order_id>`.

## Steps
1. Run: `py tools/calculate_price.py --order <order_id>` (prefer this tool over manual arithmetic).
2. Read the returned `breakdown[]` and cost fields.
3. Walk through the cost build-up and state the headroom / feasibility.
4. If asked what the handling fee "should be": run `--sweep` and show the tradeoff — recommend, don't decide.

## Formula
See [formulas.md](formulas.md) for the full 0%-cut cost build-up. Key invariant:
`farmer_payout = Σ(ask_price × allocated_kg)` — farmers paid in full; handling & spoilage are
platform-borne and added on top, never subtracted from farmers.

## Output format
Return: farmer payout (KHR + USD) · transport · handling (note: PROVISIONAL 150 KHR/kg) · spoilage
buffer · total cost · blended price/kg · headroom vs cap · feasible? · risks · assumptions ·
human-approval reminder.

## Rules
- Do not invent missing prices; if a farmer ask or route cost is missing, stop and report it.
- Never deduct handling/spoilage from farmer payout (that breaks the 0% cut).
- Do not set or finalize the handling fee — it is a human decision.
- Prefer `calculate_price.py` over prose math; always show KHR with USD.

## Verification checklist
- [ ] `farmer_payout` equals Σ(ask × kg) from the tool (0% cut holds).
- [ ] Handling & spoilage appear as separate lines, not taken from payout.
- [ ] Blended price and headroom cited from the tool.
- [ ] Handling fee flagged as provisional.
- [ ] No invented prices.

## Boundary
Claude supports the decision. The human approves the decision. Final payouts are never finalized here.
