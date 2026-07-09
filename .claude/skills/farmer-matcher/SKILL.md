---
description: Use this skill to explain how sub-ton farmer declarations are combined into candidate consolidated lots (cheapest / nearest / reliability variants) that fill a 1–3 ton Chomkar order. DERA-ZN Evaluate stage — lot assembly.
argument-hint: [order_id]
---

# Farmer Matcher Skill — DERA-ZN stage E (lot assembly)

## Goal
Explain the candidate consolidated lots that close the volume gap for one order. One job: describe the
lots and their tradeoffs. Ranking the winner is the decision-grid skill's job, not this one.

## Inputs
- `order_id`.
- Reads: `outputs/<order_id>/evaluate.json` → `candidates[]` (produced by `py tools/evaluate.py`,
  which calls the deterministic assembler `tools/assemble_lots.py`).

## Steps
1. Ensure Evaluate has run: `py tools/evaluate.py --order <order_id>`.
2. Read the `candidates[]` in `outputs/<order_id>/evaluate.json`.
3. For each variant, describe its `allocations[]` and `coverage`.

## How lots are assembled (reference — the tool does this)
Three variants (docs/business_rules.md §3): `cheapest_first`, `nearest_first` (lowest transport
distance to delivery), `reliability_first`. Greedy fill from qualifying farmers (commodity + grade),
never exceeding a farmer's `declared_qty_kg`; the last farmer may be partially allocated.

## Output format
Per variant: farmer list (id · zone · allocated_kg) · total_kg · coverage · one-line rationale
(who is in and why). Note which farmers appear in all variants (robust picks).

## Rules
- Cite farmer IDs and kg from `evaluate.json`; never invent an allocation or change kg amounts.
- Prefer the tool over manual matching.
- Do not pick the winner here.

## Verification checklist
- [ ] `evaluate.json` was read (not guessed).
- [ ] Each allocation ≤ that farmer's declared quantity.
- [ ] Allocations in each filled lot sum to the order quantity (coverage 1.0).
- [ ] No fabricated farmers or amounts.

## Boundary
Claude supports the decision. The human approves the decision.
