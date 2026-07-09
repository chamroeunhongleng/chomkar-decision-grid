# DERA-ZN Framework

The decision framework at the core of this repo. **DERA** = Detect → Evaluate → Recommend → Act.
**ZN** = **Zone-Normalized** scoring: candidate-lot factors are min-max normalized to [0,1] across all
candidates (and thus across zones = `province:commune`), so lots from different regions compare fairly in
one decision grid. This normalization is what lets the model **scale across provinces**.

## The four stages

### D — Detect  (`validate_data.py` → `detect.json`)
Audit the buyer order and farmers' declared supply. Schema/range/missing checks + the **volume-gap
check**: is total declared supply of the ordered commodity ≥ the order quantity? Emits
`{clean: bool, blockers: [...], warnings: [...]}`. A blocker halts the pipeline with a recommendation to
renegotiate (quantity, price cap, or timeline).

### E — Evaluate  (`calculate_price.py`, `route_risk.py` → `evaluate.json`)
For each **candidate lot** (a set of farmers whose allocations sum toward the order quantity), compute
the raw factors:
- **coverage** — allocated_kg / order_qty (how well the lot fills the gap)
- **price** — headroom vs the buyer cap, from the 0%-cut cost build-up
- **route** — 1 − route_risk (delivery feasibility)
- **freshness** — spoilage-margin days
Formulas and parameters: [business_rules.md](business_rules.md) §1–§2.

### R — Recommend  (`score_grid.py` → `recommend.json`)
Zone-normalize each factor across candidate lots, apply human-approved weights, and rank. The output is
a **decision grid** (lots × factors, raw + normalized + weighted) and the top-ranked lot as the
recommendation. Formulas: [business_rules.md](business_rules.md) §3.

### A — Act  (`generate_report.py` → `outputs/<order>_result.json` + `reports/*.md`)
Emit the machine artifact and a **bilingual (KM/EN)** human report, structured as **Facts / Assumptions /
Formulas / Recommendation / Requires human approval**, and stamped
`status: "RECOMMENDATION — pending human approval"`. A human (co-op officer / owner) makes the final call.

## Candidate-lot assembly (how Evaluate builds lots)
Deterministic and explainable (no black box). For an order's commodity/quality/zone:
1. Filter farmers by commodity, minimum quality, and a viable harvest date vs delivery date.
2. Rank eligible farmers by a transparent key (e.g. lowest ask, then highest reliability, then nearest).
3. Greedily allocate kg until the order quantity is met → **candidate lot A**.
4. Produce a few **alternative** candidate lots by varying the ranking key (e.g. nearest-first for lower
   route risk; highest-reliability-first) so the grid has real choices to rank.
Each candidate carries its farmer list + per-farmer allocated kg (the audit trail).

## Resume / checkpoint contract  (`dera_state.py`)
Each order has a run directory `outputs/<order_id>/` containing per-stage JSON and a manifest:
```json
{
  "order_id": "order_001",
  "updated": "<iso-8601>",
  "stages": {
    "detect":    {"status": "done", "file": "detect.json",    "input_hash": "<sha256>"},
    "evaluate":  {"status": "done", "file": "evaluate.json",  "input_hash": "<sha256>"},
    "recommend": {"status": "todo", "file": "recommend.json", "input_hash": null},
    "act":       {"status": "todo", "file": null,             "input_hash": null}
  }
}
```
**Rules**
- Before running a stage, compute an `input_hash` over that stage's inputs (relevant CSV rows + upstream
  stage outputs + the business parameters used).
- `should_run(stage, input_hash)` → **skip** (reuse the existing file) when the stage is `done` **and**
  the hash is unchanged; otherwise recompute.
- On success, write the stage file and `mark_done(stage, file, input_hash)`.
- The orchestrator (`/run-dera`) walks D→E→R→A, skipping satisfied stages — so a crashed or partial run
  resumes at the first incomplete/changed stage instead of redoing everything.
- Changing an input (or a business parameter) changes the hash and **correctly forces recompute** of that
  stage and everything downstream.

## Time note
Timestamps (`updated`) are provided by the calling process. Tools accept an injectable clock so tests and
resumable runs stay deterministic.
