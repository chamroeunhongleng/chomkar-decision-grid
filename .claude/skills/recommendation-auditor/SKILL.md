---
description: Use this skill to independently audit a DERA-ZN decision recommendation before a human acts on it — verify the 0%-cut payout, volume fill, price cap, freshness, and grid winner, then add an adversarial critique. Runs as the auditor gate in /run-dera.
argument-hint: [order_id]
---

# Recommendation Auditor Skill — DERA-ZN auditor gate (M11)

## Goal
Act as an independent, skeptical reviewer of a finished recommendation and try to find reasons NOT to
trust it, before it reaches the human. One job: audit. You do not build or re-price the lot.

## Steps
1. Run the deterministic check: `py tools/audit_recommendation.py --order <order_id>`
   (writes `outputs/<order_id>/audit.json` and patches the artifact's status on failure).
2. Read `audit.json`. The deterministic verdict is authoritative — **you cannot override a FAIL.**
3. Add a qualitative critique on top (things the mechanical checks don't catch).

## Deterministic checks (from audit.json — cite them)
`zero_cut` (payout == Σ ask×kg, asks match CSV) · `no_overallocation` (≤ declared) · `volume_filled`
(Σ == order qty) · `within_cap` (blended ≤ cap) · `freshness` (margin ≥ 0) · `grid_reproduces`
(re-run winner matches). Any FAIL = hard block.

## Adversarial critique (your added value)
Look for risks the numbers pass but judgment flags, e.g.:
- Over-reliance on one low-`reliability_score` farmer for most of the volume.
- Thin headroom that a small cost change would erase.
- Tight spoilage margin given the delivery-date weather; would a refrigerated route be safer?
- A single point of failure (one zone, one route) for the whole lot.

## Output format
Return: deterministic verdict (PASSED/FAILED + any issues) · your critique (concerns, each tied to a
cited number) · a recommendation to the human (proceed / proceed-with-caution / do-not-proceed).

## Rules
- Never override a deterministic FAIL. If FAILED, the recommendation must not be acted on.
- Cite numbers from `audit.json` / the artifact; do not recompute in prose.
- You recommend; the human still approves. You do not approve or reject on their behalf.

## Verification checklist
- [ ] `audit_recommendation.py` was run and `audit.json` read.
- [ ] Deterministic verdict reported verbatim.
- [ ] At least one adversarial angle considered, each tied to a real number.
- [ ] No number invented.

## Boundary
Claude supports the decision. The human approves the decision.
