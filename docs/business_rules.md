# Business Rules — chomkar-decision-grid

**Auditable** definitions of every formula and parameter used to turn data into a recommendation. This
is the human-owned document: **changing any formula or parameter here is a business decision that a human
approves.** Code in `tools/` must implement exactly what is written here, and cite this file.

Each rule separates: **Facts** (from data) · **Assumptions** (stated) · **Formula** · **Parameters**
(human-approved) · **Output**.

> Status of parameters below: **PROPOSED — pending human approval.** Values are reasonable defaults for
> the M4 (pricing) and M6 (grid) approval gates; the user confirms or edits them there.

---

## 1. Pricing & farmer payout (implemented by `calculate_price.py`, M4)

**Invariant — 0% platform cut:** farmers are paid their full declared `ask_price_per_kg_khr`. The
platform takes **no margin** on produce. This invariant must hold in code and be unit-tested.

**Facts (from data):** each selected farmer's `ask_price_per_kg_khr` and allocated kg; route
`cost_per_kg_khr`; buyer `max_price_per_kg_khr`, `perishability_days`.

**Assumptions:**
- Handling fee covers grading/packing/coordination and is a flat per-kg amount (NOT taken from farmers).
- Spoilage buffer reserves a % of value against expected loss on perishables.

**Formulas (per candidate lot):**
```
farmer_payout_khr      = Σ (farmer_ask_price_per_kg × allocated_kg)          # 0% cut → paid in full
transport_cost_khr     = Σ (route_cost_per_kg × allocated_kg)
handling_cost_khr      = HANDLING_FEE_PER_KG × total_kg
spoilage_buffer_khr    = SPOILAGE_BUFFER_PCT × farmer_payout_khr
total_cost_khr         = farmer_payout_khr + transport_cost_khr + handling_cost_khr + spoilage_buffer_khr
blended_price_per_kg   = total_cost_khr / total_kg
headroom_per_kg_khr    = buyer_max_price_per_kg − blended_price_per_kg       # ≥ 0 ⇒ feasible
usd_equivalent         = khr_amount / KHR_PER_USD
```
**Feasibility:** a lot is price-feasible when `blended_price_per_kg ≤ buyer_max_price_per_kg`
(`headroom_per_kg_khr ≥ 0`). Otherwise Detect/Evaluate flags "cannot fulfill within cap — recommend
renegotiate."

**Parameters (M4 gate — status shown):**
| Name | Value | Status | Meaning |
|---|---|---|---|
| `HANDLING_FEE_PER_KG` | 150 KHR/kg | **PROVISIONAL / tunable** | grading/packing/coordination, platform-borne. User chose to let the model + outcomes inform the real value; overridable via `--handling-fee`, explorable via `--sweep`, candidate for M12 calibration. |
| `SPOILAGE_BUFFER_PCT` | 0.05 (5%) | **APPROVED** | reserve against perishable loss |
| `KHR_PER_USD` | 4000 | approved (display only) | KHR→USD display rate |

**Candidate-lot assembly (APPROVED — M4):** generate **3 variants** — `cheapest_first`, `nearest_first`
(lowest transport distance to delivery), `reliability_first` — and let the M6 grid rank across them.
Allocation is greedy: sort qualifying farmers by the variant key, allocate kg until the order is filled
(last farmer partially allocated); never allocate beyond a farmer's `declared_qty_kg`.

---

## 2. Route & perishability risk (implemented by `route_risk.py`, M5)

**Facts:** route `distance_km`, `avg_transit_hours`, `road_quality`, `refrigerated`; zone weather
`temp_c`, `flood_risk`; order `perishability_days`.

**Assumptions:** longer transit + higher heat + shorter perishability window + no refrigeration ⇒ higher
spoilage risk; poor roads and flood risk add risk.

**Formula (risk normalized to [0,1], higher = worse):**
```
transit_risk   = clamp(avg_transit_hours / MAX_ACCEPTABLE_HOURS, 0, 1)
perish_risk    = clamp((avg_transit_hours/24) / perishability_days, 0, 1)
heat_risk      = clamp((temp_c − TEMP_SAFE_C) / (TEMP_MAX_C − TEMP_SAFE_C), 0, 1)
road_risk      = {good:0.0, fair:0.4, poor:0.8}[road_quality]
flood_risk_n   = {low:0.0, medium:0.5, high:1.0}[flood_risk]
refrig_relief  = REFRIG_RELIEF if refrigerated else 0.0     # subtracts risk

route_risk = clamp( W_TRANSIT·transit_risk + W_PERISH·perish_risk + W_HEAT·heat_risk
                    + W_ROAD·road_risk + W_FLOOD·flood_risk_n − refrig_relief, 0, 1)
spoilage_margin_days = perishability_days − (avg_transit_hours / 24)          # >0 desirable
```
**Parameters (M6 gate — status shown):**
| Name | Value | Status |
|---|---|---|
| `MAX_ACCEPTABLE_HOURS` | 12 | approved |
| `TEMP_SAFE_C` / `TEMP_MAX_C` | 25 / 40 | approved |
| `REFRIG_RELIEF` | 0.25 | approved |
| sub-weights `transit,perish,heat,road,flood` | **0.15, 0.30, 0.25, 0.10, 0.20** (sum 1.0) | **APPROVED** — "rainy-season perishable" profile (weights flood/heat/perishability higher for wet-season leafy greens) |

---

## 3. Zone-Normalized decision grid (implemented by `score_grid.py`, M6)

Ranks candidate **lots** for an order. Four per-lot factors, each first computed as a raw value, then
**min-max normalized to [0,1] across all candidate lots** (the "ZN" step), then combined.

**Factors (raw → higher-is-better after orientation):**
| Factor | Raw source | Orientation |
|---|---|---|
| `coverage` | allocated_kg / order_qty_kg (capped at 1.0) | higher better |
| `price` | headroom_per_kg_khr (from Rule 1) | higher better |
| `route` | 1 − route_risk (from Rule 2) | higher better |
| `freshness` | spoilage_margin_days (from Rule 2), clamped ≥0 | higher better |

**Zone-normalization (per factor `f` across candidate lots):**
```
norm_f(lot) = (raw_f(lot) − min_f) / (max_f − min_f)      # if max==min ⇒ 1.0 for all
```
**Composite DERA-ZN score:**
```
score(lot) = W_COVERAGE·norm_coverage + W_PRICE·norm_price + W_ROUTE·norm_route + W_FRESH·norm_freshness
```
Lots are ranked by `score` descending; the top lot is the **recommendation** (pending human approval).

**Factor weights (APPROVED — M6 gate; "balanced" profile; sum to 1.0):**
| Name | Value | Rationale |
|---|---|---|
| `W_COVERAGE` | 0.35 | filling the volume gap is the core purpose |
| `W_PRICE` | 0.30 | staying within the buyer cap / value |
| `W_ROUTE` | 0.20 | delivery feasibility |
| `W_FRESH` | 0.15 | perishable produce spoilage margin |

**Ties:** break by higher `coverage`, then higher `reliability_score` mean of the lot's farmers.

---

## Change control
- Any edit to a value in this file is a **human decision**. Code reads these as named constants (ideally
  from one config location) so the audit trail is explicit.
- Every report generated (`generate_report.py`) restates the parameters used, so a reader can audit which
  version of the rules produced a recommendation.
