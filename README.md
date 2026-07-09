# chomkar-decision-grid

A **decision-intelligence layer** for agricultural lot aggregation, modeled on the real
[Chomkar](https://chomkar.com) platform — a pre-harvest marketplace that consolidates Cambodian
smallholder farmers' supply into buyer-sized lots (1–3 tons) with a **0% cut of produce price**.

This project automates Chomkar's hardest, currently-manual step — **assembling the right consolidated
lot for a buyer order** — using a Claude Code workflow (slash commands + skills) sitting on top of
deterministic Python tools. It is a data-science / decision-support experiment, not the Chomkar product
itself.

## The decision problem
Given a buyer order (commodity, 1–3 ton quantity, quality, delivery, price cap), decide **which farmers'
pre-harvest declarations to combine** into a lot that:
- **closes the volume gap** (many sub-ton farmers → one buyer-sized lot),
- is **feasible** to deliver (transport + perishability + weather risk),
- is **priced fairly** — farmers receive their full ask (**0% platform cut**), within the buyer's cap,
- and is presented as an **auditable recommendation a human co-op officer approves.**

## DERA-ZN — the decision framework
A four-stage loop; **ZN = Zone-Normalized** (factor scores normalized 0–1 across provinces/communes so
candidate lots are comparable in one grid):

| Stage | Does | Output |
|---|---|---|
| **D — Detect** | Audit the order + declared supply; volume-gap check | `detect.json` |
| **E — Evaluate** | Score candidate lot assemblies (coverage, price, route/perishability) | `evaluate.json` |
| **R — Recommend** | Zone-normalize → weighted decision grid → rank lots | `recommend.json` |
| **A — Act** | Emit artifact + bilingual report, **marked pending human approval** | `order_XXX_result.json`, `reports/*.md` |

## Core principle
**Claude recommends. Humans approve.** Deterministic Python code is the source of truth for every
number (pricing, payout, risk, scores). Claude skills interpret and draft recommendations on top — they
never invent numbers and never finalize a business decision. See [AGENTS.md](AGENTS.md).

## Quickstart
> **Windows note:** use the `py` launcher (bare `python` may hit the Microsoft Store stub). On
> macOS/Linux/CI use `python`.

```bash
# From Claude Code — the full loop (Detect→Evaluate→Recommend→Act + auditor gate), resumable:
#   /run-dera order_001
# Individual stages: /audit-order  /match-farmers  /price-order  /analyze-route  /decision-report
# Learning loop:     /outcome order_001

# Or run the deterministic engine directly (one command does the whole loop + audit):
py tools/run_dera.py --order order_001

# ...or stage by stage:
py tools/validate_data.py      --order order_001   # Detect
py tools/evaluate.py           --order order_001   # Evaluate (lots + price + route)
py tools/score_grid.py         --order order_001   # Recommend (zone-normalized grid)
py tools/generate_report.py    --order order_001   # Act (bilingual report)
py tools/audit_recommendation.py --order order_001 # independent invariant audit
py tools/calibrate_weights.py                      # propose weight nudges from outcomes (proposal only)

# Tests + lint:
py -m unittest discover -s tests
py tools/lint_skills.py
```
Outputs land in `outputs/order_001/`; the human-readable report in `reports/`.
Regenerate the synthetic data anytime with `py scripts/generate_synthetic_data.py` (deterministic).

## Layout
- `.claude/commands/`, `.claude/skills/` — the Claude Code workflow (+ `settings.json` permissions)
- `docs/` — product brief, data dictionary, business rules, DERA framework, testing checklist
- `data/` — synthetic multi-province CSVs (leafy-green vegetables, KHR + USD) + `outcomes.csv` ledger
- `tools/` — deterministic Python (source of truth for all numbers)
- `tests/` — unit tests · `scripts/` — data generator · `.github/workflows/` — CI
- `notebooks/` — experiments · `reports/` — generated reports · `outputs/` — per-order run state

## Status
Pre-pilot experiment. Synthetic data only. Not connected to the live Chomkar platform. Currency is
Cambodian Riel (KHR) with USD equivalents (~4000 KHR/USD, configurable).

CI (`.github/workflows/ci.yml`) runs tests + lint + an end-to-end audited run — it activates once the
repo is pushed to GitHub. The repo is **not** git-initialized yet; run `git init` and push when ready.
