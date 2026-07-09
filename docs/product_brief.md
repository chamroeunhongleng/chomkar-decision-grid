# Product Brief — chomkar-decision-grid

## The real platform (chomkar.com)
**Chomkar** is a pre-harvest lot-aggregation marketplace for Cambodian smallholder farmers. It exists to
solve the **volume gap**: a single small farm cannot meet a commercial buyer's minimum order (1–3 tons),
so farmers are forced to sell through middlemen who control the price.

Chomkar aggregates many farmers' **pre-harvest supply declarations** into one consolidated lot that meets
a buyer's demand, and takes a **0% cut of the produce price** — it captures value through coordination
efficiency, not margin extraction. Zero farmer fees.

### The six-step loop
1. Buyer submits requirements (commodity, quantity, quality, delivery, price cap).
2. Farmers declare available supply — **before harvest**.
3. **Co-op officer assembles a consolidated lot** from multiple farmers. ← *the hard, manual step*
4. Buyer reviews and accepts.
5. Delivery occurs.
6. Payment settles.

### Actors
- **Farmers** — smallholders who declare pre-harvest supply through a cooperative officer.
- **Buyers** — commercial purchasers needing 1–3 ton quantities.
- **Co-op officers** — non-technical intermediaries who assemble lots. **The primary user of our
  decision reports.**

### Context specifics
- **Region:** Cambodia; pilot in Kampong Cham province (Kang Meas district).
- **Commodity featured:** bok choy and other leafy-green vegetables (perishable).
- **Language:** Khmer-first (English secondary).
- **Documentation:** photo + crop records, reviewable by buyers.

## What this project adds
The manual step 3 — deciding **which farmers to combine into which lot** — is where good decisions save
money and spoilage. `chomkar-decision-grid` is a **decision-intelligence layer** that automates and makes
this decision **auditable and repeatable**, so the model can **scale beyond one province**.

It is a data-science / decision-support experiment. It does **not** replace human judgment: it produces a
ranked, explainable recommendation that a co-op officer approves (**Claude recommends, humans approve**).

### Goal
Improve and scale Chomkar's lot-assembly decision with a structured framework (**DERA-ZN**), extending to
**multiple provinces** (Kampong Cham + Takeo, Kandal, Siem Reap) while preserving the 0%-cut ethos.

### Non-goals
- Not the Chomkar product/app itself; no real user data, no payments, no live integration.
- AI does not decide prices, payouts, or which lot ships — it recommends; a human decides.
- Not a forecasting/ML model (yet) — deterministic scoring first, transparent and auditable.
