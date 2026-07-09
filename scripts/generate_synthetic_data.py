"""M1 synthetic-data generator for chomkar-decision-grid.

Deterministic (no randomness): builds the 5 CSVs in data/ from an explicit,
auditable farmer/order list. Distances are computed by haversine from commune
coordinates; weather and market prices are derived by fixed formulas.

Regenerates data/*.csv. Deterministic: running it again reproduces identical files.

Run:  py scripts/generate_synthetic_data.py [repo_root]
      (repo_root defaults to the parent of this script's folder)
"""
import csv, math, os, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

# ---- Zones (province:commune) and approximate coordinates -------------------
ZONES = {
    ("Kampong Cham", "Kang Meas"): (12.00, 105.10),
    ("Kampong Cham", "Prek Koy"):  (11.99, 105.46),
    ("Takeo", "Doun Kaev"):        (10.99, 104.78),
    ("Takeo", "Tram Kak"):         (11.10, 104.68),
    ("Kandal", "Ta Khmau"):        (11.48, 104.94),
    ("Kandal", "Kien Svay"):       (11.55, 105.05),
    ("Siem Reap", "Puok"):         (13.41, 103.70),
    ("Siem Reap", "Kralanh"):      (13.52, 103.50),
}
def zkey(p, c): return f"{p}:{c}"

def haversine_km(a, b):
    R = 6371.0
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(h))

# ---- Farmers (pre-harvest declared supply) ----------------------------------
# Each declares a sub-ton amount so several must combine to fill a 1-3t order.
# fields: id, name, province, commune, crop, qty_kg, grade, cold, reliab, ask
FARMERS = [
    # bok_choy (total 2550 kg; order_001 wants 1500)
    ("F001","Sok Chan","Kampong Cham","Kang Meas","bok_choy",500,"A",True ,0.92,3200),
    ("F002","Chea Dara","Kampong Cham","Prek Koy","bok_choy",350,"B",False,0.78,3000),
    ("F005","Mao Sophal","Kandal","Ta Khmau","bok_choy",450,"A",True ,0.88,3400),
    ("F006","Ny Ratha","Kandal","Kien Svay","bok_choy",300,"B",False,0.71,3100),
    ("F010","Kim Sreymom","Takeo","Doun Kaev","bok_choy",400,"B",True ,0.83,2900),
    ("F014","Pich Vanna","Siem Reap","Puok","bok_choy",550,"A",False,0.80,3300),
    # morning_glory (total 2000; order_002 wants 1200)
    ("F003","Heng Lida","Kampong Cham","Kang Meas","morning_glory",400,"B",False,0.75,2200),
    ("F007","Sam Oun","Kandal","Ta Khmau","morning_glory",300,"B",True ,0.82,2400),
    ("F011","Chan Thida","Takeo","Tram Kak","morning_glory",500,"A",False,0.86,2300),
    ("F015","Vong Sokha","Siem Reap","Kralanh","morning_glory",350,"C",False,0.64,2100),
    ("F019","Ros Chanthy","Kampong Cham","Prek Koy","morning_glory",450,"B",True ,0.79,2250),
    # cabbage (total 2500; grade-A total 1650; order_003 wants 1500 grade A)
    ("F004","Long Sovan","Kampong Cham","Prek Koy","cabbage",600,"A",True ,0.90,1900),
    ("F008","Meas Pheak","Kandal","Kien Svay","cabbage",500,"A",True ,0.84,2000),
    ("F012","Tep Nary","Takeo","Doun Kaev","cabbage",450,"B",False,0.73,1800),
    ("F016","Sin Chenda","Siem Reap","Puok","cabbage",550,"A",False,0.81,1950),
    ("F020","Yem Sothea","Siem Reap","Kralanh","cabbage",400,"B",False,0.68,1850),
    # cucumber (total 1700; order_005 wants 1000, but low cap -> infeasible edge)
    ("F009","Khoem Rithy","Kandal","Ta Khmau","cucumber",500,"B",True ,0.85,2600),
    ("F013","Doung Piseth","Takeo","Doun Kaev","cucumber",400,"B",False,0.70,2500),
    ("F017","Nou Soklin","Siem Reap","Puok","cucumber",450,"A",False,0.77,2700),
    ("F021","Chhorn Bopha","Kampong Cham","Kang Meas","cucumber",350,"B",True ,0.80,2550),
    # long_bean (total 1350; order_004 wants 3000 -> volume-gap blocker)
    ("F018","Kong Samnang","Takeo","Tram Kak","long_bean",500,"B",False,0.74,2800),
    ("F022","Seng Chanra","Kandal","Kien Svay","long_bean",450,"B",True ,0.82,2900),
    ("F024","Uch Sovann","Kampong Cham","Prek Koy","long_bean",400,"A",False,0.76,2850),
    # leaf_mustard (variety filler; total 1050)
    ("F023","Preab Sina","Siem Reap","Kralanh","leaf_mustard",300,"B",False,0.69,2400),
    ("F025","Chhun Davy","Takeo","Doun Kaev","leaf_mustard",350,"C",False,0.62,2300),
    ("F026","Roeun Kanha","Kampong Cham","Kang Meas","leaf_mustard",400,"B",True ,0.83,2350),
]

# expected harvest dates (deterministic by index; all just before deliveries)
HARVEST_DAYS = ["2026-07-16","2026-07-17","2026-07-18","2026-07-19","2026-07-20"]

with open(os.path.join(DATA,"farmers.csv"),"w",newline="",encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["farmer_id","name","village","commune","province","declared_crop",
                "declared_qty_kg","expected_harvest_date","quality_grade","cold_storage",
                "reliability_score","ask_price_per_kg_khr","lat","lon"])
    for i,(fid,name,prov,comm,crop,qty,grade,cold,rel,ask) in enumerate(FARMERS):
        lat,lon = ZONES[(prov,comm)]
        village = f"{comm} Village {(i%3)+1}"
        harvest = HARVEST_DAYS[i % len(HARVEST_DAYS)]
        w.writerow([fid,name,village,comm,prov,crop,qty,harvest,grade,
                    str(cold).lower(),f"{rel:.2f}",ask,f"{lat:.4f}",f"{lon:.4f}"])

# ---- Buyer orders -----------------------------------------------------------
# order_001: fillable volume gap (worked example)
# order_002: fillable
# order_003: fillable (grade-A cabbage)
# order_004: NEGATIVE -> supply(1350) < demand(3000): volume-gap blocker
# order_005: NEGATIVE -> max_price below feasible cost: cannot fulfill within cap
ORDERS = [
    ("order_001","Phnom Fresh Market","bok_choy",1500,"B",3800,"Kandal","Ta Khmau","2026-07-22",3,200),
    ("order_002","Green Grocer Co","morning_glory",1200,"B",2900,"Kampong Cham","Kang Meas","2026-07-20",2,180),
    ("order_003","Angkor Veggie Export","cabbage",1500,"A",2400,"Siem Reap","Puok","2026-07-25",5,150),
    ("order_004","Mega Wholesale","long_bean",3000,"B",3500,"Kandal","Kien Svay","2026-07-28",3,220),
    ("order_005","Budget Bazaar","cucumber",1000,"B",2000,"Takeo","Doun Kaev","2026-07-24",4,160),
]
with open(os.path.join(DATA,"buyer_orders.csv"),"w",newline="",encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["order_id","buyer_name","commodity","quantity_kg","quality_required",
                "max_price_per_kg_khr","delivery_province","delivery_commune","delivery_date",
                "perishability_days","penalty_per_day_khr"])
    for row in ORDERS:
        w.writerow(row)

# ---- Transport costs (every zone -> each delivery zone) ----------------------
DELIVERY_ZONES = sorted({(o[6],o[7]) for o in ORDERS})
def road_quality(dist):
    return "good" if dist < 30 else ("fair" if dist < 120 else "poor")
with open(os.path.join(DATA,"transport_costs.csv"),"w",newline="",encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["route_id","from_zone","to_zone","distance_km","cost_per_kg_khr",
                "road_quality","refrigerated","avg_transit_hours"])
    rid = 1
    for (fp,fc),fco in ZONES.items():
        for (tp,tc) in DELIVERY_ZONES:
            if (fp,fc)==(tp,tc):
                dist=0.0; cost=50; rq="good"; refrig=True; hours=0.5
            else:
                dist = haversine_km(fco, ZONES[(tp,tc)])
                cost = round(80 + 2.5*dist)
                rq = road_quality(dist)
                refrig = dist > 70
                hours = round(dist/45.0 + 0.5, 1)
            w.writerow([f"R{rid:03d}", zkey(fp,fc), zkey(tp,tc), round(dist),
                        cost, rq, str(refrig).lower(), hours])
            rid += 1

# ---- Weather (each zone, daily over the order window) -----------------------
DATES = [f"2026-07-{d:02d}" for d in range(16, 31)]
def flood(rain): return "high" if rain>30 else ("medium" if rain>15 else "low")
def forecast(rain): return "heavy_rain" if rain>30 else ("light_rain" if rain>10 else "clear")
with open(os.path.join(DATA,"weather_sample.csv"),"w",newline="",encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["province","commune","date","temp_c","rainfall_mm","humidity_pct","flood_risk","forecast"])
    for zi,((p,c),_) in enumerate(ZONES.items()):
        for di,date in enumerate(DATES):
            # Siem Reap (zi 6,7) wetter -> more route risk variety
            rain = ((di*7 + zi*13) % 38) + (12 if p=="Siem Reap" else 0)
            temp = 29 + ((di + zi) % 6)
            hum = 70 + ((di*3 + zi*5) % 20)
            w.writerow([p, c, date, f"{temp:.1f}", f"{rain:.1f}", f"{hum:.1f}",
                        flood(rain), forecast(rain)])

# ---- Market prices (per commodity x province, reference date) ---------------
CROP_BASE = {"bok_choy":3100,"morning_glory":2250,"cabbage":1900,
             "cucumber":2600,"long_bean":2850,"leaf_mustard":2350}
PROVINCES = ["Kampong Cham","Takeo","Kandal","Siem Reap"]
TRENDS = ["up","flat","down"]
with open(os.path.join(DATA,"market_prices.csv"),"w",newline="",encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["commodity","date","province","wholesale_price_per_kg_khr","retail_price_per_kg_khr","trend"])
    for ci,(crop,base) in enumerate(CROP_BASE.items()):
        for pi,prov in enumerate(PROVINCES):
            wholesale = base + (pi-1)*50            # small regional spread
            retail = round(wholesale*1.4)
            trend = TRENDS[(ci+pi) % 3]
            w.writerow([crop,"2026-07-15",prov,wholesale,retail,trend])

# ---- Summary for verification ----------------------------------------------
from collections import defaultdict
supply = defaultdict(int)
for (_,_,_,_,crop,qty,*_ ) in FARMERS: supply[crop]+=qty
print("farmers:", len(FARMERS))
print("supply by crop:", dict(supply))
for oid,_,comm,qty,grade,*_ in ORDERS:
    print(f"{oid}: {comm} needs {qty}kg (min grade {grade}); total supply={supply[comm]}kg -> "
          f"{'VOLUME-GAP BLOCKER' if supply[comm]<qty else 'fillable'}")
print("zones:", len(ZONES), "delivery_zones:", len(DELIVERY_ZONES))
print("wrote CSVs to", DATA)
