"""
seed_demo.py
------------
Creates a realistic demo shop for VyapariAI.   Run (after build_reference + load_reference):

    python -m app.ml.seed_demo

Login afterwards:  demo@vyapariai.com / demo1234

IDEMPOTENT: every run first deletes the demo user's old data and then recreates it.
Fixed random seed -> the same data every time (good for tests and for the viva).

How the two data layers are used
  MACRO  (reference_prices table, from the WPI file): supplier purchase prices
         unit_price = reference wholesale on that date x supplier factor x small noise
  MICRO  (data/demand_profile.json, from the retail datasets): how much the shop sells
         - category_share  -> splits the daily sales budget between Fresh / Milk / Grocery
         - demand_noise    -> day-to-day randomness of sales
         - month_index     -> mild monthly seasonality (damped)
         Weekend uplift and Indian festival bumps are ASSUMPTIONS written in this file.
"""
import json
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import delete, inspect as sa_inspect, select, func

from app.database import Base, SessionLocal, engine
from app import models
from app.models import (Product, Purchase, ReferencePrice, Sale, Shop, Supplier,
                        User, supplier_products)

# ------------------------------------------------------------------ settings
SEED = 42
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROFILE_JSON = BACKEND_DIR / "data" / "demand_profile.json"
GROUND_TRUTH_CSV = BACKEND_DIR / "data" / "anomaly_ground_truth.csv"

DEMO_EMAIL = "demo@vyapariai.com"
DEMO_PASSWORD = "demo1234"
SHOP_NAME = "Sharma General Store"
SHOP_CITY = "Nagpur"

HISTORY_DAYS = 365                 # 12 months of history
DAILY_SALES_BUDGET = 9000.0        # Rs of these 10 products sold on an average day (ASSUMPTION)
LEAD_TIME_DAYS = 3                 # supplier delivery time used for reorder levels
SAFETY_DAYS = 2
N_SPIKES, N_DROPS = 21, 4          # 25 injected anomalies in total
MIN_DAYS_BETWEEN_ANOMALIES = 14    # per product, so detectors have clean data in between

# Weekday multipliers (Mon..Sun). ASSUMPTION: people shop more on Fri-Sun.
WEEKDAY_FACTOR = [0.92, 0.92, 0.95, 0.98, 1.08, 1.30, 1.25]
# Festival dates (Nagpur / Maharashtra). Approximate - edit freely. Demand ramps up over the 7 days before.
FESTIVALS = {
    "Dussehra": date(2025, 10, 2), "Diwali": date(2025, 10, 20), "Makar Sankranti": date(2026, 1, 14),
    "Holi": date(2026, 3, 4), "Gudi Padwa": date(2026, 3, 19), "Eid": date(2026, 3, 21),
    "Raksha Bandhan": date(2026, 8, 28), "Ganesh Chaturthi": date(2026, 9, 14),
}
FESTIVAL_PEAK_BUMP = 0.45          # +45 % demand on the festival day for fully sensitive items

# ------------------------------------------------------------------ suppliers
# factor = price vs market (1.00 = market), noise = +/- random band around that price
SUPPLIERS = {
    "ABC Traders":    {"factor": 0.98, "noise": 0.015, "contact": "9822000001", "pick_weight": 3.0},  # cheap, stable
    "Sharma Foods":   {"factor": 1.06, "noise": 0.015, "contact": "9822000002", "pick_weight": 2.0},  # dear, stable
    "XYZ Wholesale":  {"factor": 1.00, "noise": 0.080, "contact": "9822000003", "pick_weight": 2.5},  # average, volatile
    "GoodFood Co.":   {"factor": 1.00, "noise": 0.020, "contact": "9822000004", "pick_weight": 2.0},  # average
}

# ------------------------------------------------------------------ products
# name, category, unit, reference commodity, demand profile category, weight inside that category,
# festival sensitivity (0..1), suppliers that sell it, ends_low (stock below reorder level at the end)
PRODUCTS = [
    ("Rice",         "Grains",     "kg",     "Rice",         "Grocery", 1.5, 0.6, ["ABC Traders", "Sharma Foods", "XYZ Wholesale"], False),
    ("Wheat Atta",   "Grains",     "kg",     "Wheat Atta",   "Grocery", 2.0, 0.8, ["ABC Traders", "GoodFood Co.", "XYZ Wholesale"], False),
    ("Sugar",        "Staples",    "kg",     "Sugar",        "Grocery", 1.2, 1.0, ["ABC Traders", "Sharma Foods", "GoodFood Co."], False),
    ("Toor Dal",     "Pulses",     "kg",     "Toor Dal",     "Grocery", 0.8, 0.7, ["Sharma Foods", "XYZ Wholesale", "GoodFood Co."], True),
    ("Soyabean Oil", "Oils",       "litre",  "Soyabean Oil", "Grocery", 1.0, 1.0, ["ABC Traders", "XYZ Wholesale"], False),
    ("Salt",         "Staples",    "packet", "Salt",         "Grocery", 0.3, 0.2, ["Sharma Foods", "GoodFood Co."], False),
    ("Onion",        "Vegetables", "kg",     "Onion",        "Fresh",   1.4, 0.3, ["XYZ Wholesale", "GoodFood Co."], False),
    ("Potato",       "Vegetables", "kg",     "Potato",       "Fresh",   1.4, 0.3, ["XYZ Wholesale", "GoodFood Co."], False),
    ("Tomato",       "Vegetables", "kg",     "Tomato",       "Fresh",   1.0, 0.3, ["XYZ Wholesale", "ABC Traders"], True),
    ("Milk",         "Dairy",      "litre",  "Milk",         "Milk",    1.0, 0.8, ["GoodFood Co.", "Sharma Foods"], False),
]

# logical field -> possible real column names (so a small naming difference in Person A's models.py doesn't crash us)
ALIASES = {
    "hashed_password": ["hashed_password", "password_hash", "password"],
    "full_name": ["full_name", "name", "username"],
    "shop_name": ["shop_name", "name"],
    "location": ["location", "city", "address"],
    "owner_id": ["user_id", "owner_id"],
    "total": ["total", "total_amount", "amount"],
}
_warned: set[str] = set()


def build(Model, **fields):
    """Create a Model object using only columns that really exist (with alias support)."""
    attrs = {a.key for a in sa_inspect(Model).column_attrs}
    out = {}
    for logical, value in fields.items():
        for candidate in ALIASES.get(logical, [logical]):
            if candidate in attrs:
                out[candidate] = value
                break
        else:
            key = f"{Model.__name__}.{logical}"
            if key not in _warned:
                _warned.add(key)
                print(f"[note] {key} has no matching column - skipped")
    return Model(**out)


def hash_password(plain: str) -> str:
    """Use the project's own hashing helper if it exists, otherwise passlib bcrypt directly."""
    from app import auth
    for name in ("get_password_hash", "hash_password"):
        if hasattr(auth, name):
            return getattr(auth, name)(plain)
    from passlib.context import CryptContext
    return CryptContext(schemes=["bcrypt"], deprecated="auto").hash(plain)


# ================================================================ helpers
def load_profile() -> dict:
    default = {"category_share": {"Fresh": 0.36, "Milk": 0.17, "Grocery": 0.24},
               "demand_noise": 0.25, "month_index": {str(m): 1.0 for m in range(1, 13)}}
    if PROFILE_JSON.exists():
        return json.loads(PROFILE_JSON.read_text())
    print("[note] demand_profile.json missing -> using defaults (run app.ml.build_demand_profile)")
    return default


def load_reference(db, commodities, start: date, end: date) -> dict[str, pd.DataFrame]:
    """commodity -> DataFrame indexed by date with wholesale_price / retail_price columns."""
    out = {}
    for c in commodities:
        rows = db.execute(
            select(ReferencePrice.price_date, ReferencePrice.wholesale_price, ReferencePrice.retail_price)
            .where(ReferencePrice.commodity == c, ReferencePrice.price_date >= start, ReferencePrice.price_date <= end)
            .order_by(ReferencePrice.price_date)
        ).all()
        if not rows:
            raise SystemExit(f"No reference prices for '{c}'. Run build_reference and load_reference first.")
        df = pd.DataFrame(rows, columns=["d", "wholesale", "retail"])
        df["d"] = pd.to_datetime(df["d"])
        df = df.set_index("d").reindex(pd.date_range(start, end)).ffill().bfill()   # safety: fill tiny gaps
        out[c] = df
    return out


def festival_ramp(d: date) -> float:
    """0 .. 1: grows over the 7 days before a festival, 1.0 on the festival day itself."""
    best = 0.0
    for fday in FESTIVALS.values():
        delta = (fday - d).days
        if 0 <= delta <= 7:
            best = max(best, 1 - delta / 8)
    return best


def delete_demo_data(db) -> None:
    """Remove the demo user, its shop and everything that belongs to the shop."""
    user = db.execute(select(User).where(User.email == DEMO_EMAIL)).scalar_one_or_none()
    if user is None:
        return
    owner_col = next(c for c in ALIASES["owner_id"] if hasattr(Shop, c))
    shop = db.execute(select(Shop).where(getattr(Shop, owner_col) == user.id)).scalar_one_or_none()
    if shop is not None:
        supplier_ids = [s for (s,) in db.execute(select(Supplier.id).where(Supplier.shop_id == shop.id))]
        if supplier_ids:
            db.execute(delete(supplier_products).where(supplier_products.c.supplier_id.in_(supplier_ids)))
        # children first, then products/suppliers, then the shop
        for name in ("Alert", "ActivityLog", "AdvisorMessage", "Sale", "Purchase", "Product", "Supplier"):
            Model = getattr(models, name, None)
            if Model is not None and hasattr(Model, "shop_id"):
                db.execute(delete(Model).where(Model.shop_id == shop.id))
        db.delete(shop)
    db.delete(user)
    db.commit()
    print("[reset] old demo data removed")


# ================================================================ simulation
def simulate_product(rng, spec, days, ref, profile, shares, n_in_cat):
    """
    Returns (demand list, purchase plan) for ONE product.
    Stock is simulated day by day so it can never go negative:
    each purchase quantity = demand until the next purchase + a buffer - stock on hand.
    """
    name, _, unit, commodity, pcat, weight, fest_sens, _, ends_low = spec
    N = len(days)

    # average units per day = (budget share of this product) / retail price at the start
    start_retail = float(ref[commodity]["retail"].iloc[0])
    product_budget = DAILY_SALES_BUDGET * shares[pcat] * weight / n_in_cat[pcat]
    avg_units = product_budget / start_retail

    sigma = profile["demand_noise"]
    month_idx = profile["month_index"]
    demand = []
    step = 1.0 if unit == "packet" else 0.5
    for d in days:
        month_factor = 1 + 0.35 * (month_idx[str(d.month)] - 1)          # damped: raw index swings too hard
        fest_factor = 1 + FESTIVAL_PEAK_BUMP * fest_sens * festival_ramp(d)
        noise = math.exp(rng.normal(0, sigma) - sigma ** 2 / 2)            # mean 1 log-normal noise
        q = avg_units * WEEKDAY_FACTOR[d.weekday()] * month_factor * fest_factor * noise
        demand.append(max(0.0, round(q / step) * step))

    reorder_level = max(5, math.ceil(avg_units * (LEAD_TIME_DAYS + SAFETY_DAYS) / 5) * 5)
    opening = math.ceil(avg_units * 10 / 5) * 5

    # weekly purchase days: every 7 days (+/- 1 day jitter)
    idx = int(rng.integers(0, 6))
    purchase_idx = []
    while idx < N:
        purchase_idx.append(idx)
        idx += 7 + int(rng.integers(-1, 2))

    mid_buffer = 0.6 * reorder_level
    end_buffer = 0.4 * reorder_level if ends_low else 1.5 * reorder_level
    # stock on the day of the first purchase = opening stock minus what was sold before that day
    qty_by_idx, stock = {}, float(opening) - sum(demand[:purchase_idx[0]])
    for k, i in enumerate(purchase_idx):
        last = k == len(purchase_idx) - 1
        next_i = N if last else purchase_idx[k + 1]
        need = sum(demand[i:next_i]) + (end_buffer if last else mid_buffer) - stock
        qty = max(5, math.ceil(need / 5) * 5)                              # lots of 5 units, at least 5
        qty_by_idx[i] = qty
        stock += qty - sum(demand[i:next_i])
        assert stock >= -1e-9, "stock went negative - bug in simulation"
    return demand, qty_by_idx, reorder_level, opening, avg_units


def pick_anomalies(rng, purchases):
    """Choose N_SPIKES + N_DROPS purchases; same product at least 14 days apart."""
    order = rng.permutation(len(purchases))
    chosen, last_by_product = [], {}
    kinds = ["spike"] * N_SPIKES + ["drop"] * N_DROPS
    rng.shuffle(kinds)
    for i in order:
        if len(chosen) == len(kinds):
            break
        p = purchases[i]
        if any(abs((p["date"] - d).days) < MIN_DAYS_BETWEEN_ANOMALIES for d in last_by_product.get(p["product"], [])):
            continue
        last_by_product.setdefault(p["product"], []).append(p["date"])
        chosen.append((i, kinds[len(chosen)]))
    return chosen


# ================================================================ main
def main() -> None:
    rng = np.random.default_rng(SEED)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # ---- date window: 12 months ending at the newest reference date (never in the future)
        newest = db.execute(select(func.max(ReferencePrice.price_date))).scalar()
        if newest is None:
            raise SystemExit("reference_prices is empty. Run: build_reference, then load_reference.")
        end = min(date.today(), newest)
        start = end - timedelta(days=HISTORY_DAYS - 1)
        days = [start + timedelta(days=i) for i in range(HISTORY_DAYS)]
        print(f"Demo window: {start} -> {end}")

        profile = load_profile()
        commodities = sorted({p[3] for p in PRODUCTS})
        ref = load_reference(db, commodities, start, end)

        # category shares restricted to the categories this shop actually sells, re-normalised to 1
        used_cats = {p[4] for p in PRODUCTS}
        raw = {c: profile["category_share"][c] for c in used_cats}
        shares = {c: v / sum(raw.values()) for c, v in raw.items()}
        n_in_cat = {c: sum(p[5] for p in PRODUCTS if p[4] == c) for c in used_cats}   # sum of weights

        delete_demo_data(db)

        # ---- user, shop
        user = build(User, email=DEMO_EMAIL, hashed_password=hash_password(DEMO_PASSWORD), full_name="Demo Shopkeeper")
        db.add(user)
        db.flush()
        shop = build(Shop, owner_id=user.id, shop_name=SHOP_NAME, location=SHOP_CITY, shop_type="General Store")
        db.add(shop)
        db.flush()

        # ---- suppliers
        supplier_obj = {}
        for sname, cfg in SUPPLIERS.items():
            s = build(Supplier, shop_id=shop.id, name=sname, contact=cfg["contact"], address=SHOP_CITY)
            db.add(s)
            supplier_obj[sname] = s
        db.flush()

        # ---- products + simulation
        purchases_plan, sales_rows, product_obj, sim = [], [], {}, {}
        for spec in PRODUCTS:
            name, category, unit, commodity, *_ = spec
            demand, qty_by_idx, reorder, opening, avg_units = simulate_product(rng, spec, days, ref, profile, shares, n_in_cat)
            sim[name] = (demand, qty_by_idx)
            p = build(Product, shop_id=shop.id, name=name, category=category, unit=unit,
                      reorder_level=reorder, current_stock=0.0, reference_commodity=commodity)
            db.add(p)
            product_obj[name] = (p, opening)
        db.flush()

        # supplier <-> product mapping
        links = [{"supplier_id": supplier_obj[s].id, "product_id": product_obj[spec[0]][0].id}
                 for spec in PRODUCTS for s in spec[7]]
        db.execute(supplier_products.insert(), links)

        # ---- purchases (price = reference wholesale x supplier factor x noise)
        for spec in PRODUCTS:
            name, _, unit, commodity, *_rest = spec
            sup_names = spec[7]
            weights = np.array([SUPPLIERS[s]["pick_weight"] for s in sup_names])
            weights = weights / weights.sum()
            _, qty_by_idx = sim[name]
            for i, qty in qty_by_idx.items():
                sname = str(rng.choice(sup_names, p=weights))
                cfg = SUPPLIERS[sname]
                market = float(ref[commodity]["wholesale"].iloc[i])
                noise = rng.uniform(-cfg["noise"], cfg["noise"])
                price = market * cfg["factor"] * (1 + noise)
                purchases_plan.append({"product": name, "supplier": sname, "date": days[i], "qty": float(qty),
                                       "price": price, "market": market})

        # ---- inject anomalies (~25)
        chosen = pick_anomalies(rng, purchases_plan)
        anomaly_info = {}
        for i, kind in chosen:
            pct = rng.uniform(20, 45) if kind == "spike" else -rng.uniform(20, 30)
            purchases_plan[i]["price"] *= 1 + pct / 100
            anomaly_info[i] = (kind, round(float(pct), 1))

        purchase_objs = []
        for i, pl in enumerate(purchases_plan):
            price = round(pl["price"], 2)
            o = build(Purchase, shop_id=shop.id, product_id=product_obj[pl["product"]][0].id,
                      supplier_id=supplier_obj[pl["supplier"]].id, quantity=pl["qty"], unit_price=price,
                      total=round(price * pl["qty"], 2), purchase_date=pl["date"])
            purchase_objs.append(o)
        db.add_all(purchase_objs)
        db.flush()                                         # now every purchase has an id

        gt = [{"purchase_id": purchase_objs[i].id, "purchase_date": purchases_plan[i]["date"].isoformat(),
               "product": purchases_plan[i]["product"], "anomaly_type": kind, "magnitude_pct": pct}
              for i, (kind, pct) in sorted(anomaly_info.items(), key=lambda kv: purchases_plan[kv[0]]["date"])]
        pd.DataFrame(gt).to_csv(GROUND_TRUTH_CSV, index=False)

        # ---- sales: shop reprices every Monday = reference retail x 1.03, rounded to 50 paise
        sale_objs = []
        for spec in PRODUCTS:
            name, _, unit, commodity, *_rest = spec
            demand, _ = sim[name]
            sell_price = None
            for i, d in enumerate(days):
                if sell_price is None or d.weekday() == 0:
                    sell_price = round(float(ref[commodity]["retail"].iloc[i]) * 1.03 * 2) / 2
                if demand[i] > 0:
                    sale_objs.append(build(Sale, shop_id=shop.id, product_id=product_obj[name][0].id,
                                           quantity=demand[i], unit_price=sell_price,
                                           total=round(demand[i] * sell_price, 2), sale_date=d))
            product_obj[name][0].selling_price = sell_price
        db.add_all(sale_objs)

        # ---- current stock = opening + purchases - sales
        for spec in PRODUCTS:
            name = spec[0]
            p, opening = product_obj[name]
            demand, qty_by_idx = sim[name]
            p.current_stock = round(opening + sum(qty_by_idx.values()) - sum(demand), 2)
        db.commit()

        # ================= summary & self-check
        print("\n=== DEMO SEED SUMMARY ===")
        print(f"Login          : {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print(f"Shop           : {SHOP_NAME}, {SHOP_CITY}")
        print(f"Products       : {len(PRODUCTS)}   Suppliers: {len(SUPPLIERS)}   Links: {len(links)}")
        print(f"Purchases      : {len(purchase_objs)}   Sales rows: {len(sale_objs)}")
        print(f"Anomalies      : {len(gt)} ({sum(1 for g in gt if g['anomaly_type']=='spike')} spikes, "
              f"{sum(1 for g in gt if g['anomaly_type']=='drop')} drops) -> {GROUND_TRUTH_CSV.name}")
        pdf = pd.DataFrame(purchases_plan)
        pdf["ratio"] = pdf["price"] / pdf["market"]
        clean = pdf.drop(index=list(anomaly_info))            # behaviour of suppliers WITHOUT the injected anomalies
        print("\nSupplier price vs market (anomalies excluded):")
        print(clean.groupby("supplier")["ratio"].agg(avg_vs_market="mean", std="std", n="size").round(3).to_string())
        print("\nStock check (current_stock must be >= 0):")
        low = []
        for spec in PRODUCTS:
            p, _ = product_obj[spec[0]]
            flag = "LOW" if p.current_stock < p.reorder_level else "ok"
            if flag == "LOW":
                low.append(p.name)
            print(f"  {p.name:<13} stock {p.current_stock:>7.1f} {p.unit:<6} reorder {p.reorder_level:>5.0f}  {flag}")
            assert p.current_stock >= 0
        print(f"\nBelow reorder level: {', '.join(low) or 'none'}")
        total_sales = sum(s.quantity * s.unit_price for s in sale_objs)
        print(f"Total sales value: Rs {total_sales:,.0f}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
