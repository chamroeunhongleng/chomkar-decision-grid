# Testing Checklist — chomkar-decision-grid

**A task is not done until it is validated.** (AGENTS.md rule 6.) This file lists the automated tests and
the manual/edge checks for each mission. Reference it from CLAUDE.md's Verification Checklist.

## How to run
```bash
python -m pytest tests/            # preferred
python -m unittest discover tests  # stdlib fallback (no pytest install needed)
```
Full deterministic pipeline on the worked example:
```bash
python tools/validate_data.py   --order order_001
python tools/calculate_price.py --order order_001
python tools/route_risk.py      --order order_001
python tools/score_grid.py      --order order_001
python tools/generate_report.py --order order_001
```

## Unit tests (per tool)
- **dera_state** (M2): `should_run` skips a `done`+unchanged stage; recomputes when the input hash
  changes; `mark_done` persists status/file/hash; state round-trips through JSON.
- **validate_data** (M3): passes clean data; flags a **volume-gap blocker** when Σ declared supply <
  order qty; flags schema/range/missing errors; unknown zone → warning.
- **calculate_price** (M4): **0%-cut invariant** — `farmer_payout == Σ(ask × allocated_kg)`; handling &
  spoilage are added on top, never subtracted from payout; `blended_price_per_kg` math exact; USD
  equivalent = KHR / rate; `headroom` sign correct at/above/below cap.
- **route_risk** (M5): score always in [0,1]; increases with distance/transit-hours/heat/poor-road/flood;
  refrigeration lowers it; `spoilage_margin_days` = perishability − transit days.
- **score_grid** (M6): each factor normalized to [0,1]; equal-values case → all 1.0 (no divide-by-zero);
  weights sum to 1.0; ranking deterministic; documented tie-break applied.

## Manual / integration checks
- **Pipeline (M7):** producing `outputs/order_001/order_001_result.json` + `reports/…md` with a ranked
  grid, KHR+USD figures, and `status: "RECOMMENDATION — pending human approval"`.
- **Volume gap closed:** the recommended lot lists several farmers summing to the 1–3 ton order.
- **Resume (M9):** delete `recommend.json` + the act artifact, re-run `/run-dera order_001`, confirm
  Detect & Evaluate are **skipped** (reused from state) and only Recommend/Act recompute.
- **Skills cite, don't compute (M8):** spot-check a skill's narrative — every number traces to a tool's
  JSON output; none are computed in prose.

## Negative / edge cases (must not produce false positives)
- **Supply < demand:** order qty exceeds total declared supply → Detect **blocker**, pipeline halts with
  a renegotiate recommendation.
- **Cap below cost:** buyer `max_price` < feasible `blended_price_per_kg` → "cannot fulfill within cap —
  recommend renegotiate," not a shipped lot.
- **Perishable + long route:** high route risk / negative spoilage margin → flagged; refrigerated route
  preferred where available.
- **Quality shortfall:** insufficient grade-A supply for a grade-A order → blocker/warning as specified.

## Environment
- Python 3 on PATH; **tools use stdlib only** (`csv`, `json`, `hashlib`, `argparse`) — no third-party
  deps required to run the pipeline. `pytest` is optional (unittest fallback provided).
- Confirmed working on Windows (paths, `python` launcher) during M2.
