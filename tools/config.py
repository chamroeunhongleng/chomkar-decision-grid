"""config.py — central business parameters (mirror of docs/business_rules.md).

Single, auditable location for constants the code treats as the source of truth.
**Changing a value here is a business decision** — it must match docs/business_rules.md,
which the human owns and approves. Pricing (§1) and grid-weight (§3) parameters are added
at their approval-gate missions (M4, M6).
"""

# Currency display rate (KHR -> USD). Non-margin; display only.
KHR_PER_USD = 4000

# Quality grades, ordinal (A best). Used for "meets required grade" checks.
VALID_GRADES = ("A", "B", "C")
GRADE_RANK = {"A": 3, "B": 2, "C": 1}

# Known provinces in the synthetic dataset (referential sanity only).
VALID_PROVINCES = ("Kampong Cham", "Takeo", "Kandal", "Siem Reap")

# --------------------------------------------------------------------------- #
# Pricing parameters — docs/business_rules.md §1 (0% platform cut invariant)
# --------------------------------------------------------------------------- #
# Spoilage buffer: reserve against perishable loss, as a fraction of farmer payout.
# APPROVED at 5% (M4 gate).
SPOILAGE_BUFFER_PCT = 0.05

# Handling fee (KHR/kg): platform-borne grading/packing/coordination cost, added ON TOP
# of farmer payout — never deducted from farmers. PROVISIONAL DEFAULT: the user chose to
# let the model/data inform the real value rather than fix it now. Treat as tunable:
# overridable via calculate_price.py --handling-fee, explorable via --sweep, and a candidate
# for M12 outcome-calibration. NOT a finalized business decision.
HANDLING_FEE_PER_KG = 150

# Candidate-lot assembly strategies (docs/business_rules.md §3 / dera_framework.md).
# The grid (M6) ranks across these variants.
LOT_VARIANTS = ("cheapest_first", "nearest_first", "reliability_first")

# --------------------------------------------------------------------------- #
# Route & perishability risk — docs/business_rules.md §2
# Route-risk sub-weights are PROVISIONAL, presented for approval at the M6 gate
# alongside the grid weights.
# --------------------------------------------------------------------------- #
MAX_ACCEPTABLE_HOURS = 12          # transit hours mapped to full transit risk
TEMP_SAFE_C = 25                   # below this, no heat risk
TEMP_MAX_C = 40                    # at/above this, full heat risk
REFRIG_RELIEF = 0.25               # risk subtracted when route is refrigerated
# APPROVED (M6 gate): "rainy-season perishable" profile — weights flood/heat/perish higher.
ROUTE_RISK_WEIGHTS = {"transit": 0.15, "perish": 0.30, "heat": 0.25, "road": 0.10, "flood": 0.20}
ROAD_RISK = {"good": 0.0, "fair": 0.4, "poor": 0.8}
FLOOD_RISK_N = {"low": 0.0, "medium": 0.5, "high": 1.0}

# --------------------------------------------------------------------------- #
# Zone-Normalized decision grid — docs/business_rules.md §3
# APPROVED (M6 gate): "balanced" profile. Must sum to 1.0.
# --------------------------------------------------------------------------- #
GRID_WEIGHTS = {"coverage": 0.35, "price": 0.30, "route": 0.20, "freshness": 0.15}

# --------------------------------------------------------------------------- #
# Outcome calibration (M12) — proposal bounds only. calibrate_weights.py PROPOSES
# weight nudges from real outcomes; a human approves by editing this file + §3.
# --------------------------------------------------------------------------- #
CALIBRATION_STEP = 0.05      # max weight nudge per factor per calibration cycle
WEIGHT_FLOOR = 0.02          # a factor's weight never proposed below this
MIN_OUTCOMES_TO_CALIBRATE = 3


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def khr_to_usd(khr):
    """Convert KHR to USD for display. Rounded to cents."""
    return round(khr / KHR_PER_USD, 2)


def grade_meets(farmer_grade, required_grade):
    """True if farmer_grade is at least as good as required_grade (A>=B>=C)."""
    return GRADE_RANK.get(farmer_grade, 0) >= GRADE_RANK.get(required_grade, 0)
