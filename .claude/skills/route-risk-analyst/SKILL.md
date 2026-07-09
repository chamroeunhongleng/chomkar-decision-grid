---
description: Use this skill to explain a Chomkar lot's transport and perishability risk — transit time, heat, road quality, flood risk, refrigeration, and spoilage margin — and whether the delivery is safe. DERA-ZN Evaluate stage — route risk.
argument-hint: [order_id]
---

# Route Risk Analyst Skill — DERA-ZN stage E (route & perishability)

## Goal
Explain how risky the delivery is for a candidate lot and how much spoilage margin remains. One job:
route/perishability risk. Not pricing, not ranking.

## Inputs
- `order_id`.
- Reads: the `route` block of each candidate in `outputs/<order_id>/evaluate.json`, or
  `py tools/route_risk.py --order <order_id>`.

## Steps
1. Run: `py tools/route_risk.py --order <order_id>` (prefer this over manual estimation).
2. Read the `route_risk` (0–1), `spoilage_margin_days`, and per-leg detail.
3. Explain the drivers and flag red flags (small/negative margin, high risk).

## Formula (reference — the tool computes it)
`route_risk` (0–1, higher=worse) blends transit / perishability / heat / road / flood, minus a relief
if refrigerated. Approved "rainy-season" weights: transit .15 / perish .30 / heat .25 / road .10 /
flood .20 (docs/business_rules.md §2). `spoilage_margin_days = perishability − transit_days`, taken
from the tightest leg.

## Output format
Return: overall route_risk · spoilage margin (days) · main risk drivers · delivery-zone weather used ·
refrigeration recommendation · human-approval reminder.

## Rules
- Cite `route_risk`, margins, and weather from the tool; never invent a risk number or weather value.
- If route or weather data is missing, say so (the tool falls back to pessimistic/default values).
- Prefer the tool over prose math.

## Verification checklist
- [ ] `route_risk.py` run / `route` block read (not guessed).
- [ ] Route risk stated as a 0–1 value from the tool.
- [ ] Spoilage margin reported; a negative/thin margin is flagged.
- [ ] Refrigeration recommendation given when margin is tight.
- [ ] No fabricated weather or risk values.

## Boundary
Claude supports the decision. The human approves the decision.
