---
description: Use this skill to explain the zone-normalized decision grid that ranks candidate Chomkar lots and to say which lot wins and why. DERA-ZN Recommend stage — grid ranking.
argument-hint: [order_id]
---

# Decision Grid Skill — DERA-ZN stage R (Recommend)

## Goal
Explain how candidate lots are ranked into a single recommendation via zone-normalized scoring, and why
the winner won. One job: the ranking. It does not assemble lots or price them.

## Inputs
- `order_id`.
- Reads: `outputs/<order_id>/recommend.json` (produced by `py tools/score_grid.py --order <order_id>`).

## Steps
1. Run: `py tools/score_grid.py --order <order_id>`.
2. Read `recommend.json` → `ranked[]`, `winner`, `weights`.
3. Present the grid and explain the winner; if `winner` is null, recommend renegotiation.

## Formula (reference — the tool computes it)
Each factor (coverage, price=headroom, route=1−risk, freshness=spoilage margin) is **min-max normalized
to [0,1] across the candidate lots** (the "ZN" step), then combined with approved **balanced** weights
(coverage .35 / price .30 / route .20 / freshness .15). See docs/business_rules.md §3.

## Output format
Return: the ranked grid (variant · normalized factors · score) · the winner · a one-paragraph "why it
won" (which normalized factors carried it) · the tradeoff vs runner-up · human-approval reminder.

## Rules
- Cite scores and normalized values from `recommend.json`; never re-rank or compute a score in prose.
- Changing the weights is a business decision — describe the likely effect if asked, but do not
  silently re-weight.
- If no lot is feasible, recommend renegotiation; do not fabricate a pick.

## Verification checklist
- [ ] `recommend.json` read (not guessed).
- [ ] Winner matches the highest-scoring feasible lot in the file.
- [ ] "Why it won" references the normalized factors, not invented reasoning.
- [ ] Null winner → renegotiation recommended, no fabricated pick.

## Boundary
Claude supports the decision. The human approves the decision.
