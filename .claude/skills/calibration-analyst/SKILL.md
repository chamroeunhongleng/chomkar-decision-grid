---
description: Use this skill to record a Chomkar order's real outcome and to explain a proposed grid-weight recalibration from accumulated outcomes. Turns the decision grid into a learning system. Proposal only — a human approves any weight change.
argument-hint: [order_id]
---

# Calibration Analyst Skill — DERA-ZN M12 (learning loop)

## Goal
(1) Record what actually happened to a recommended order, and (2) explain whether accumulated outcomes
suggest re-weighting the decision grid. One job: outcomes + calibration. It never changes the weights.

## Steps
1. **Record:** `py tools/record_outcome.py --order <id> --shipped .. --on-time .. --spoilage .. \
   --satisfaction .. --paid-full ..` (appends a row to `data/outcomes.csv`, snapshotting the winning
   lot's normalized factors).
2. **Calibrate:** `py tools/calibrate_weights.py` (writes `outputs/calibration_proposal.json`).
3. Explain the proposal: which factors correlated with good/bad outcomes and the suggested nudge.

## What to explain (from calibration_proposal.json)
- `mean_success` and `n_outcomes` (needs ≥ 3 to propose anything).
- Per factor: `corr_with_success` and the proposed nudge (bounded ±0.05, renormalized to sum 1.0).
  E.g. "route correlated +0.9 → nudge its weight up; price correlated −0.6 → nudge down."
- Present **current → proposed** weights side by side.

## Rules
- This is a **PROPOSAL ONLY.** Do not edit `docs/business_rules.md` or `config.py`. State clearly that a
  human must approve and apply the change.
- Do not record fake outcomes; only real, observed results.
- Cite numbers from the proposal JSON; never compute correlations in prose.

## Verification checklist
- [ ] Proposal read from `calibration_proposal.json` (not guessed).
- [ ] Proposed weights sum to 1.0.
- [ ] It is stated explicitly that the change requires human approval and is not auto-applied.

## Boundary
Claude supports the decision. The human approves the decision — including any weight change.
