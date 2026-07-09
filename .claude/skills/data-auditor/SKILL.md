---
description: Use this skill to audit a Chomkar buyer order and farmers' declared supply — check missing fields, invalid values, quantity/quality mismatch, and the volume gap (declared supply vs order quantity) — before any pricing or matching. DERA-ZN Detect stage.
argument-hint: [order_id]
---

# Data Auditor Skill — DERA-ZN stage D (Detect)

## Goal
Give a single go / no-go read on whether an order's data is clean and whether there is enough declared
supply (at the required grade) to fill it. One job: audit + volume-gap check. Nothing else.

## Inputs
- `order_id` (e.g. `order_001`).
- Reads: `data/*.csv` via the tool, and the tool's output `outputs/<order_id>/detect.json`.

## Steps
1. Run: `py tools/validate_data.py --order <order_id>` (prefer this tool over any manual checking).
2. Read `outputs/<order_id>/detect.json`.
3. Report the verdict (`clean`), the supply picture, blockers, and warnings — citing the JSON.
4. If blocked, recommend renegotiating quantity, grade, or timeline. Do not proceed to later stages.

## What the numbers mean
- `supply.qualifying_kg` vs `supply.required_qty_kg` (+ `n_qualifying_farmers`) = the volume-gap picture.
- `blockers[].code`: `VOLUME_GAP` (supply < demand at grade), `SCHEMA`, `ORDER_NOT_FOUND`, `EMPTY_TABLE`.
- `warnings[]`: non-blocking (e.g. `NO_ROUTE_TO_DELIVERY`, `SINGLE_FARMER`).

## Output format
Return: verdict (proceed / stop) · supply vs demand · each blocker (code + plain explanation) ·
warnings · recommended next step. Bilingual-friendly, plain language for a co-op officer.

## Rules
- Cite every figure from `detect.json`; never estimate supply, counts, or shortfalls in prose.
- Do not invent missing values. If data is missing, say so and stop.
- Prefer the tool over manual arithmetic.

## Verification checklist
Before finishing, verify:
- [ ] `validate_data.py` was actually run and `detect.json` read (not guessed).
- [ ] Supply vs demand stated with the tool's numbers.
- [ ] Every blocker reported with its code and a plain explanation.
- [ ] A blocked order is NOT presented as fulfillable.
- [ ] No fabricated values.

## Boundary
Claude supports the decision. The human approves the decision.
