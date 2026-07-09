"""dataio.py — shared CSV loading + parsing helpers for the DERA-ZN tools.

Stdlib-only. Loaders return lists of plain dicts (raw strings, as read); typed
parsing is done by the small to_*() helpers so each tool controls its own coercion
and error handling. Zone = "province:commune".
"""
import csv
import os

DATA_FILES = {
    "farmers": "farmers.csv",
    "orders": "buyer_orders.csv",
    "transport": "transport_costs.csv",
    "weather": "weather_sample.csv",
    "prices": "market_prices.csv",
}


def repo_root(root=None):
    return root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_dir(root=None):
    return os.path.join(repo_root(root), "data")


def _load(name, root=None):
    path = os.path.join(data_dir(root), DATA_FILES[name])
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_farmers(root=None):
    return _load("farmers", root)


def load_orders(root=None):
    return _load("orders", root)


def load_transport(root=None):
    return _load("transport", root)


def load_weather(root=None):
    return _load("weather", root)


def load_prices(root=None):
    return _load("prices", root)


def get_order(order_id, orders=None, root=None):
    """Return the order row dict, or raise KeyError if not found."""
    orders = orders if orders is not None else load_orders(root)
    for o in orders:
        if o["order_id"] == order_id:
            return o
    raise KeyError(f"order {order_id!r} not found in buyer_orders.csv")


# --------------------------------------------------------------------------- #
# Zones
# --------------------------------------------------------------------------- #
def zone(province, commune):
    return f"{province}:{commune}"


def farmer_zone(farmer):
    return zone(farmer["province"], farmer["commune"])


def order_delivery_zone(order):
    return zone(order["delivery_province"], order["delivery_commune"])


# --------------------------------------------------------------------------- #
# Typed parsing (raise ValueError on bad values — callers decide how to report)
# --------------------------------------------------------------------------- #
def to_int(v):
    return int(str(v).strip())


def to_float(v):
    return float(str(v).strip())


def to_bool(v):
    s = str(v).strip().lower()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no", ""):
        return False
    raise ValueError(f"not a boolean: {v!r}")
