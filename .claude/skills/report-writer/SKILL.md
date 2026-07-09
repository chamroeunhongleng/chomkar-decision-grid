---
description: Use this skill to present the final Chomkar decision report for one order — bilingual (Khmer/English), with 0%-cut farmer payouts, the ranked grid, and the mandatory human-approval checklist. Trigger only after Detect, Evaluate, and Recommend are complete. DERA-ZN Act stage.
argument-hint: [order_id]
disable-model-invocation: true
---

# Report Writer Skill — DERA-ZN stage A (Act)

## Goal
Present the final, bilingual decision report for one order to a non-technical co-op officer, and surface
the human-approval gate. One job: present the report. It does not compute anything.

> `disable-model-invocation: true` so the final report is produced only when explicitly requested
> (via `/decision-report` or `/run-dera`) — never auto-generated before the earlier stages are done.

## Inputs
- `order_id`. Requires detect.json + evaluate.json + recommend.json to already exist.
- Reads: `outputs/<order_id>/<order_id>_result.json` and `reports/<order_id>_decision_report.md`.

## Steps
1. Run: `py tools/generate_report.py --order <order_id>` (writes the artifact + the bilingual report).
2. Read the artifact and the generated markdown report.
3. Present the report; end with the approval checklist verbatim.

## Output format
Present, in Khmer + English: the **status** verbatim · recommended lot · **0%-cut farmer payout table**
(paid in full) · price build-up · ranked grid · then the **"Requires human approval"** checklist as
pending items. The canonical layout is produced by `generate_report.py` — do not re-template it in prose.

## Rules
- Cite only figures from the generated artifact; never compute or restate unread numbers.
- Keep it bilingual and readable for a non-technical officer.
- If status is `BLOCKED` or `CANNOT FULFILL`, present that plainly and recommend renegotiation — do not
  manufacture a recommendation.

## Verification checklist
Run the full [decision-quality checklist](checklists/decision_quality_checklist.md) before presenting.
Minimum:
- [ ] Status shown verbatim.
- [ ] Farmer payouts sum to Σ(ask × kg) (0% cut).
- [ ] "Requires human approval" section present and unresolved.
- [ ] No number invented; all from the artifact.

## Boundary
Claude supports the decision. The human approves the decision. **Never** approve, commit, or finalize on
the user's behalf.
