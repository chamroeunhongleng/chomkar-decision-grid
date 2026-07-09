# Data Dictionary — chomkar-decision-grid

All data in `data/` is **synthetic** (no real farmers/buyers). Multi-province, leafy-green vegetables,
prices in **Cambodian Riel (KHR)**. A **zone** is identified as `province:commune`.

> This is the M0 specification. The CSVs themselves are generated in **M1** to match exactly these
> columns, units, and ranges. If a tool needs a column not listed here, update this file first.

## Conventions
- **Currency:** KHR (integer riel). USD equivalents are derived in code, not stored (rate ~4000 KHR/USD).
- **Quantities:** kilograms (kg), integer.
- **Dates:** `YYYY-MM-DD`.
- **Booleans:** `true` / `false`.
- **Quality grade:** ordinal `A` > `B` > `C`.
- **Provinces (seed):** Kampong Cham, Takeo, Kandal, Siem Reap.
- **Commodities (seed, leafy greens):** bok_choy, morning_glory, cabbage, cucumber, long_bean,
  leaf_mustard.

## farmers.csv — pre-harvest declared supply
One row per farmer's declaration. Seeded so **each farmer declares a sub-ton amount (200–600 kg)**, so
several must combine to fill a 1–3 ton order (the volume gap).

| Column | Type | Notes / range |
|---|---|---|
| `farmer_id` | str | e.g. `F001`, unique |
| `name` | str | synthetic Khmer name |
| `village` | str | |
| `commune` | str | |
| `province` | str | one of the seed provinces |
| `declared_crop` | str | one of the seed commodities |
| `declared_qty_kg` | int | 200–600 |
| `expected_harvest_date` | date | within ~2 weeks of order delivery dates |
| `quality_grade` | str | A / B / C |
| `cold_storage` | bool | farmer has cold storage access |
| `reliability_score` | float | 0.0–1.0 (past-delivery reliability) |
| `ask_price_per_kg_khr` | int | farmer's asking price (paid in full — 0% cut) |
| `lat` | float | for distance/route context |
| `lon` | float | |

## buyer_orders.csv
One row per buyer order. `order_001` is the worked example.

| Column | Type | Notes / range |
|---|---|---|
| `order_id` | str | e.g. `order_001` |
| `buyer_name` | str | |
| `commodity` | str | one of the seed commodities |
| `quantity_kg` | int | 1000–3000 (buyer minimum lot) |
| `quality_required` | str | A / B / C (minimum acceptable) |
| `max_price_per_kg_khr` | int | buyer's price cap per kg |
| `delivery_province` | str | |
| `delivery_commune` | str | |
| `delivery_date` | date | |
| `perishability_days` | int | days produce stays sellable after harvest (e.g. 2–5) |
| `penalty_per_day_khr` | int | late-delivery penalty per kg per day |

## transport_costs.csv
Cost/feasibility of moving produce between zones.

| Column | Type | Notes / range |
|---|---|---|
| `route_id` | str | unique |
| `from_zone` | str | `province:commune` |
| `to_zone` | str | `province:commune` |
| `distance_km` | int | |
| `cost_per_kg_khr` | int | transport cost per kg |
| `road_quality` | str | good / fair / poor |
| `refrigerated` | bool | refrigerated transport available on this route |
| `avg_transit_hours` | float | |

## weather_sample.csv
Weather per zone per date, feeding route/perishability risk.

| Column | Type | Notes / range |
|---|---|---|
| `province` | str | |
| `commune` | str | |
| `date` | date | |
| `temp_c` | float | |
| `rainfall_mm` | float | |
| `humidity_pct` | float | 0–100 |
| `flood_risk` | str | low / medium / high |
| `forecast` | str | short text, e.g. `heavy_rain`, `clear` |

## market_prices.csv
Reference market prices per commodity/province/date (context for pricing sanity checks).

| Column | Type | Notes / range |
|---|---|---|
| `commodity` | str | |
| `date` | date | |
| `province` | str | |
| `wholesale_price_per_kg_khr` | int | |
| `retail_price_per_kg_khr` | int | |
| `trend` | str | up / flat / down |

## Referential integrity (enforced by validate_data.py in M3)
- Every `buyer_orders.commodity` should have enough matching `farmers.declared_crop` supply to
  potentially fill it (else Detect flags a **volume-gap blocker**).
- Zones referenced in orders/farmers should appear in `transport_costs` and `weather_sample`.
- Harvest dates should precede/around delivery dates.

## Regenerating the data
The CSVs are produced deterministically by [`scripts/generate_synthetic_data.py`](../scripts/generate_synthetic_data.py)
(stdlib only; distances via haversine from commune coordinates; weather/prices via fixed formulas):
```
py scripts/generate_synthetic_data.py
```
Re-running reproduces byte-identical files. To change the dataset, edit the explicit `FARMERS` / `ORDERS`
lists in that script and re-run.

## Worked-example order scenarios (current seed: 26 farmers, 5 orders)
Designed so the pipeline exercises both success and failure paths:
| Order | Commodity | Qty | Grade | Cap (KHR/kg) | Scenario |
|---|---|---|---|---|---|
| `order_001` | bok_choy | 1500 | B | 3800 | **Worked example** — fillable, real volume gap (needs several sub-ton farmers) |
| `order_002` | morning_glory | 1200 | B | 2900 | Fillable |
| `order_003` | cabbage | 1500 | A | 2400 | Fillable (grade-A cabbage supply = 1650 kg) |
| `order_004` | long_bean | 3000 | B | 3500 | **Volume-gap blocker** — total supply 1350 kg < 3000 |
| `order_005` | cucumber | 1000 | B | 2000 | **Price-cap edge** — supply exists, but cap 2000 < feasible cost → "cannot fulfill" |

Supply totals by crop: bok_choy 2550 · morning_glory 2000 · cabbage 2500 · cucumber 1700 ·
long_bean 1350 · leaf_mustard 1050 kg.
