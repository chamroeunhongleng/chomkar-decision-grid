<!-- Add a logo/animation here later, e.g. <img src="assets/chomkar_animation.gif" width="200"> -->
<p align="center">🌾 → 📦 → 📊 → ✅</p>

# Chomkar Decision Grid

[![CI](https://github.com/chamroeunhongleng/chomkar-decision-grid/actions/workflows/ci.yml/badge.svg)](https://github.com/chamroeunhongleng/chomkar-decision-grid/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

An agricultural **decision-intelligence framework** built on [Claude Code](https://claude.com/claude-code).
Give it a buyer order, and it decides **which smallholder farmers to combine, at what price, and by which
route** — then hands a co-op officer an auditable, bilingual recommendation to approve or reject.

> Note: This is an independent open-source data-science project. It is not affiliated with, endorsed by,
> or maintained by Anthropic (Claude Code is referenced only as the toolchain) — nor by
> [Chomkar](https://chomkar.com), whose public pre-harvest aggregation model inspired the problem this
> project models. All data is synthetic; no real farmers, buyers, or payments are involved.

<p align="center">
  <i>Claude recommends. Humans approve.<br>
  Deterministic code owns every number; AI explains, never invents.</i>
</p>

## What this is

A structured workflow that turns Claude Code into a **lot-assembly decision assistant** for pre-harvest
agriculture. The problem it models is Chomkar's "volume gap": individual small farms declare sub-ton
amounts (200–600 kg), but commercial buyers need 1–3 ton lots — so someone must decide *which farmers to
combine*. That decision is currently manual. This project makes it repeatable, explainable, and
**zone-normalized** so it scales across provinces.

The decision framework is **DERA-ZN** — Detect → Evaluate → Recommend → Act, with Zone-Normalized
scoring — plus an always-on audit gate and an outcome-calibration learning loop.

```
/run-dera order_001
     |
     v
  Detect ────────> Evaluate ─────────> Recommend ────────> Act ─────────> Audit gate
  volume-gap        3 candidate lots     zone-normalized     bilingual       independent
  + data audit      0%-cut pricing       decision grid       KM/EN report    invariant
                    route/spoilage       ranks the lots      + artifact      re-check
                    risk
     |
     v
  "RECOMMENDATION — pending human approval"        (or BLOCKED / CANNOT FULFILL, honestly)
```

Every stage checkpoints to `outputs/<order_id>/state.json`, so crashed or repeated runs **resume** from
the first incomplete stage instead of recomputing.

## Prerequisites

- [Claude Code](https://claude.com/claude-code) (CLI) — for the slash-command workflow
- Python 3.10+ — the entire engine is **stdlib-only** (no pandas, no third-party deps)
- Optional: `nbformat` + `nbclient` + `ipykernel` — only if you want to re-execute the
  [notebooks](notebooks/) (`pip install nbformat nbclient ipykernel`)

> **Windows note:** use the `py` launcher (bare `python` may hit the Microsoft Store stub). On
> macOS/Linux/CI use `python`.

## Quick start

### 1. Clone

```bash
git clone https://github.com/chamroeunhongleng/chomkar-decision-grid.git
cd chomkar-decision-grid
```

### 2. Run the full decision loop

```bash
claude
# Then inside Claude Code:
/run-dera order_001
```

This runs Detect → Evaluate → Recommend → Act → Audit for the worked example and presents a bilingual
(Khmer/English) recommendation ending with a **"Requires human approval"** checklist.

No Claude needed for the engine itself:

```bash
py tools/run_dera.py --order order_001
```

### 3. Try the honest failure modes

```bash
/run-dera order_004     # volume gap: supply 1,350 kg < 3,000 kg needed -> BLOCKED
/run-dera order_005     # buyer cap below cost -> CANNOT FULFILL, recommend renegotiate
```

The system refuses rather than fabricates — a blocked order never becomes a shipped lot.

### 4. Verify everything yourself

```bash
py -m unittest discover -s tests    # 62 unit tests
py tools/lint_skills.py             # skills/commands convention lint
py scripts/generate_synthetic_data.py   # regenerate the dataset (byte-identical, deterministic)
```

## Commands

`/run-dera` is the orchestrator. Six more commands break the loop apart or extend it:

- **`/audit-order <id>`** — Detect only: data audit + the volume-gap check (is there enough qualifying
  supply at the required grade?). Blockers stop the pipeline with a renegotiation recommendation.
- **`/match-farmers <id>`** — Evaluate (assembly): builds the three candidate lots — *cheapest-first*
  (max price headroom), *nearest-first* (min route risk), *reliability-first* (safest farmers) — showing
  exactly which farmers and how many kg each.
- **`/price-order <id>`** — Evaluate (pricing): the 0%-cut cost build-up per lot — full farmer payout +
  transport + handling + spoilage buffer → blended price vs the buyer's cap. `--sweep` explores the
  provisional handling fee against real data instead of guessing it.
- **`/analyze-route <id>`** — Evaluate (risk): transit × heat × flood × road × perishability, minus
  refrigeration relief; reports each lot's spoilage margin in days.
- **`/decision-report <id>`** — Recommend + Act: ranks the lots in the zone-normalized grid and writes
  the bilingual decision report + machine artifact.
- **`/outcome <id>`** — the learning loop: record what actually happened after delivery (spoilage,
  on-time, satisfaction, paid-in-full). After 3+ recorded outcomes it **proposes** evidence-based grid
  weight adjustments — which a human approves by editing `docs/business_rules.md`. Nothing self-applies.

## File structure

```
chomkar-decision-grid/
├── CLAUDE.md                          # Project brain: role, domain profile, workflow, verification checklist
├── AGENTS.md                          # Universal AI-agent operating rules (recommends-not-decides, etc.)
├── .claude/
│   ├── commands/
│   │   ├── run-dera.md                # /run-dera orchestrator (resumable, audited)
│   │   ├── audit-order.md             # /audit-order  (Detect)
│   │   ├── match-farmers.md           # /match-farmers (Evaluate: lot assembly)
│   │   ├── price-order.md             # /price-order  (Evaluate: 0%-cut pricing)
│   │   ├── analyze-route.md           # /analyze-route (Evaluate: route/spoilage risk)
│   │   ├── decision-report.md         # /decision-report (Recommend + Act)
│   │   └── outcome.md                 # /outcome (record results, propose calibration)
│   ├── skills/                        # One skill = one job; cite the tool, never compute in prose
│   │   ├── data-auditor/              # Detect reasoning
│   │   ├── farmer-matcher/            # Lot-assembly reasoning
│   │   ├── pricing-analyst/           # Pricing reasoning (+ formulas.md reference)
│   │   ├── route-risk-analyst/        # Route/perishability reasoning
│   │   ├── decision-grid/             # Grid-ranking reasoning
│   │   ├── report-writer/             # Final report (disable-model-invocation + quality checklist)
│   │   ├── recommendation-auditor/    # Adversarial reviewer on top of the deterministic audit
│   │   └── calibration-analyst/       # Outcome recording + weight-proposal explanation
│   └── settings.json                  # Claude Code permissions (scoped to tools/tests)
├── docs/
│   ├── product_brief.md               # The Chomkar model + what this project adds
│   ├── data_dictionary.md             # Every CSV column, units, ranges, worked-example scenarios
│   ├── business_rules.md              # AUDITABLE: formulas + human-approved parameters
│   ├── dera_framework.md              # DERA-ZN stages, grid math, resume contract
│   └── testing_checklist.md           # Automated + manual validation steps
├── data/
│   ├── farmers.csv                    # 26 pre-harvest declarations (sub-ton, multi-province)
│   ├── buyer_orders.csv               # 5 orders incl. designed failure cases
│   ├── transport_costs.csv            # 40 zone-to-zone routes
│   ├── weather_sample.csv             # 120 zone-day weather rows
│   ├── market_prices.csv              # Reference wholesale/retail prices
│   └── outcomes.csv                   # Append-only realized-outcome ledger (feeds calibration)
├── tools/                             # DETERMINISTIC CORE — source of truth for every number
│   ├── run_dera.py                    # Orchestrator: D -> E -> R -> A -> Audit, resumable
│   ├── dera_state.py                  # Checkpoint/resume engine (input-hash stage skipping)
│   ├── validate_data.py               # Detect: schema, ranges, volume-gap blocker
│   ├── assemble_lots.py               # Candidate-lot assembly (money decision = code, not prose)
│   ├── calculate_price.py             # 0%-cut cost build-up + handling-fee sweep
│   ├── route_risk.py                  # Route/perishability risk (rainy-season weights)
│   ├── evaluate.py                    # Evaluate assembler -> evaluate.json
│   ├── score_grid.py                  # Zone-normalized weighted grid -> recommend.json
│   ├── generate_report.py             # Bilingual KM/EN report + pending-approval artifact
│   ├── audit_recommendation.py        # Independent invariant re-check (the audit gate)
│   ├── record_outcome.py              # Append validated outcomes to the ledger
│   ├── calibrate_weights.py           # PROPOSE bounded weight nudges from outcomes
│   ├── lint_skills.py                 # Enforce skill/command conventions in CI
│   ├── config.py                      # All business parameters, mirrored from business_rules.md
│   └── dataio.py                      # Shared CSV loading/parsing
├── tests/                             # 62 unit tests (invariants, edge cases, negative paths)
├── notebooks/                         # Experiments — import the tools, never re-implement the math
│   ├── 01_data_cleaning.ipynb         # Dataset audit + volume-gap picture
│   ├── 02_order_feasibility.ipynb     # Lot assembly, risk, grid ranking, all-orders sweep
│   └── 03_pricing_profit_split.ipynb  # The 0%-cut split of the blended price + fee sensitivity
├── scripts/
│   └── generate_synthetic_data.py     # Deterministic dataset generator (re-run = identical bytes)
├── reports/                           # Generated bilingual decision reports
├── outputs/                           # Per-order run state (gitignored; regenerated by the tools)
└── .github/workflows/ci.yml           # CI: tests, lint, audited e2e run, notebook execution
```

## How `/run-dera` works

The orchestrator runs a **deterministic pipeline with an adversarial audit** before anything reaches a
human:

1. **Detect** — audit the order + declared supply. The headline check is the **volume gap**: enough
   qualifying supply at the required grade? A blocker halts everything with a renegotiation
   recommendation.
2. **Evaluate** — assemble the three candidate lots, price each with the **0% platform cut** (farmers
   receive their full ask; handling and spoilage are platform-borne, added on top, never deducted), and
   score each lot's route/perishability risk against delivery-date weather.
3. **Recommend** — the **zone-normalized decision grid**: each factor (coverage, price headroom,
   route safety, freshness) is min-max normalized across the candidate lots, then combined with
   human-approved weights. Normalization is what makes lots from different provinces comparable.
4. **Act** — emit the machine artifact (status: `RECOMMENDATION - pending human approval`) and a
   bilingual Khmer/English report structured as **Facts / Assumptions / Formulas / Recommendation /
   Requires human approval**.
5. **Audit gate** — an independent checker re-derives everything from the raw CSVs: payout == Σ(ask × kg),
   nobody allocated beyond their declaration, the order exactly filled, the price under the cap, the
   grid winner reproducible. Any failure flips the status to `BLOCKED BY AUDIT` — a bad recommendation
   cannot reach the human quietly.

### What makes this workflow different

- **Deterministic core, AI shell.** Every number — pricing, payouts, risk scores, rankings — comes from
  stdlib-only Python that is unit-tested and re-runnable. The Claude skills *interpret and cite* those
  numbers; a CI linter (`lint_skills.py`) enforces that no skill computes money in prose.
- **The 0%-cut invariant is enforced three times.** In the pricing code, in the unit tests, and
  independently in the audit gate, which recomputes payouts from the raw CSVs rather than trusting the
  pipeline's own output.
- **Honest failure modes are designed in.** The dataset ships with an unfillable order and an
  under-priced order; the correct output for both is a refusal with a renegotiation recommendation, and
  CI asserts it stays that way.
- **Resume, not recompute.** Each stage hashes its inputs; unchanged stages are skipped on re-run.
  Changing a business parameter automatically invalidates and recomputes everything downstream of it.
- **A learning loop with a human gate.** `/outcome` records real results; `calibrate_weights.py`
  correlates decision factors with realized success and *proposes* bounded weight nudges (±0.05,
  renormalized). Applying them means a human edits `docs/business_rules.md` — the system never rewrites
  its own decision criteria.
- **Reports a non-technical co-op officer can act on.** Bilingual KM/EN, KHR with USD equivalents, the
  full farmer-payout table, and an explicit approval checklist — no black boxes.

## Customization

### Which files to edit

| File | What to change |
|------|---------------|
| `docs/business_rules.md` | The human-owned formulas and parameters (pricing, risk, grid weights) |
| `tools/config.py` | The code mirror of those parameters — keep the two in sync |
| `scripts/generate_synthetic_data.py` | The `FARMERS` / `ORDERS` seed lists (explicit, auditable) |
| `docs/data_dictionary.md` | Column contract — update it first if a tool needs a new column |
| `.claude/skills/*/SKILL.md` | Reasoning instructions per stage (must pass `lint_skills.py`) |

### Swapping in real data

The CSVs follow a fixed, documented schema ([docs/data_dictionary.md](docs/data_dictionary.md)). Drop
real farmer declarations, orders, routes, and weather into the same columns and the entire pipeline —
including the audit gate — works unchanged. Detect will tell you honestly if the real data has gaps.

### Extending the decision model

- **New provinces/communes:** add zones to the generator (or your real data) — zone-normalization
  handles cross-region comparison automatically.
- **New commodities:** add crops with their perishability profiles; the route-risk model already keys
  on the order's perishability window.
- **Different weights:** run orders, record `/outcome`, and let the calibration proposal argue from
  evidence — then approve the change yourself.

## Tips for better results

- **Record every outcome.** The calibration loop is only as good as its ledger. Even three honest
  outcomes shift the weight proposal meaningfully (the seed data already suggests: route and freshness
  up, price down).
- **Use the handling-fee sweep before fixing the fee.** `py tools/calculate_price.py --order <id> --sweep`
  shows exactly how much coordination cost each order can absorb — set the fee from evidence, not
  guesswork.
- **Read the audit trail, not just the verdict.** Every artifact separates facts, assumptions, and
  formulas, and restates the parameters used — so a reviewer can reconstruct any recommendation
  months later.

## Status

Pre-pilot experiment. Synthetic data only; not connected to the live Chomkar platform. Currency is
Cambodian Riel (KHR) with USD equivalents (~4,000 KHR/USD, configurable in one place). CI runs the full
test suite, the skill lint, an audited end-to-end run, and executes all notebooks on every push.

## Contributing

Issues and PRs are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for setup, conventions (the
deterministic-core / skills-cite-never-compute rules that keep this auditable), and the local checks
to run before opening a PR. Please also read the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE) — see the LICENSE file for the full text.

## Acknowledgements

- [Chomkar](https://chomkar.com) — the real pre-harvest aggregation platform whose public model
  (volume-gap consolidation, 0% cut, co-op officers) inspired this decision layer
- [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search) — the Claude Code
  project structure this repo's conventions (skills, verification checklists, CI lint) are modeled on
- Built with [Claude Code](https://claude.com/claude-code) by [Anthropic](https://anthropic.com)
