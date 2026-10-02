"""
eda_plots.py
------------
Exploratory data analysis figures (PNG) saved in  <repo>/docs/figures/

    python -m app.ml.eda_plots

Figures
  1. reference_<commodity>.png       one line plot per commodity (wholesale + retail), real vs synthetic part marked
  2. reference_all_normalised.png    all commodities with price = 100 at the start (compare trends)
  3. demo_vs_reference_<product>.png demo shop purchase prices (dots, coloured by supplier) over the
                                     reference wholesale line, for 3 products. Injected anomalies are circled.
"""
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                      # no window needed, write files only
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Product, Purchase, ReferencePrice, Supplier, User

BACKEND_DIR = Path(__file__).resolve().parents[2]
FIG_DIR = BACKEND_DIR.parent / "docs" / "figures"
GROUND_TRUTH_CSV = BACKEND_DIR / "data" / "anomaly_ground_truth.csv"
DEMO_EMAIL = "demo@vyapariai.com"
OVERLAY_PRODUCTS = ["Rice", "Onion", "Toor Dal"]   # stable staple, volatile vegetable, pricey pulse

sns.set_theme(style="whitegrid", context="notebook")
PALETTE = {"wholesale": "#0F4C5C", "retail": "#E9785B"}   # VyapariAI primary / accent


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def load_reference(db) -> pd.DataFrame:
    rows = db.execute(select(ReferencePrice.commodity, ReferencePrice.price_date, ReferencePrice.wholesale_price,
                             ReferencePrice.retail_price, ReferencePrice.unit, ReferencePrice.source)).all()
    df = pd.DataFrame(rows, columns=["commodity", "date", "wholesale", "retail", "unit", "source"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def plot_each_commodity(ref: pd.DataFrame) -> None:
    for name, g in ref.groupby("commodity"):
        fig, ax = plt.subplots(figsize=(9, 4))
        sns.lineplot(data=g, x="date", y="wholesale", ax=ax, color=PALETTE["wholesale"], label="wholesale")
        sns.lineplot(data=g, x="date", y="retail", ax=ax, color=PALETTE["retail"], label="retail", alpha=0.8)
        # shade the synthetic tail (only for commodities that have both real and synthetic rows)
        syn = g[g["source"] == "synthetic"]
        if 0 < len(syn) < len(g):
            ax.axvspan(syn["date"].min(), syn["date"].max(), color="grey", alpha=0.12, label="synthetic part")
        ax.set_title(f"{name} - reference price (Rs per {g['unit'].iloc[0]})")
        ax.set_xlabel("")
        ax.set_ylabel(f"Rs / {g['unit'].iloc[0]}")
        ax.legend()
        fig.tight_layout()
        fig.savefig(FIG_DIR / f"reference_{slug(name)}.png", dpi=130)
        plt.close(fig)


def plot_normalised(ref: pd.DataFrame) -> None:
    """Every commodity indexed to 100 at its first day -> shows who rose fastest."""
    ref = ref.sort_values("date").copy()
    ref["index"] = ref.groupby("commodity")["wholesale"].transform(lambda s: s / s.iloc[0] * 100)
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(data=ref, x="date", y="index", hue="commodity", ax=ax, linewidth=1.2)
    ax.set_title("All commodities, wholesale price indexed to 100 at the first date")
    ax.set_xlabel("")
    ax.legend(ncol=3, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "reference_all_normalised.png", dpi=130)
    plt.close(fig)


def plot_demo_vs_reference(db, ref: pd.DataFrame) -> None:
    user = db.execute(select(User).where(User.email == DEMO_EMAIL)).scalar_one_or_none()
    if user is None:
        print("[skip] demo user not found - run seed_demo first")
        return
    products = {p.name: p for p in db.execute(select(Product)).scalars()
                if p.name in OVERLAY_PRODUCTS and p.shop_id == _shop_id(db, user)}
    suppliers = {s.id: s.name for s in db.execute(select(Supplier)).scalars()}
    truth = pd.read_csv(GROUND_TRUTH_CSV) if GROUND_TRUTH_CSV.exists() else pd.DataFrame(columns=["purchase_id"])

    for pname in OVERLAY_PRODUCTS:
        p = products.get(pname)
        if p is None:
            continue
        rows = db.execute(select(Purchase.id, Purchase.purchase_date, Purchase.unit_price, Purchase.supplier_id)
                          .where(Purchase.product_id == p.id)).all()
        pur = pd.DataFrame(rows, columns=["id", "date", "price", "supplier_id"])
        pur["date"] = pd.to_datetime(pur["date"])
        pur["supplier"] = pur["supplier_id"].map(suppliers)
        line = ref[(ref["commodity"] == p.reference_commodity) & (ref["date"].between(pur["date"].min(), pur["date"].max()))]

        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(line["date"], line["wholesale"], color="grey", linewidth=1.5, label="reference wholesale")
        sns.scatterplot(data=pur, x="date", y="price", hue="supplier", ax=ax, s=35)
        bad = pur[pur["id"].isin(truth["purchase_id"])]
        ax.scatter(bad["date"], bad["price"], s=160, facecolors="none", edgecolors="red", linewidths=1.5,
                   label="injected anomaly")
        ax.set_title(f"{pname}: purchase prices vs reference (Rs per {p.unit})")
        ax.set_xlabel("")
        ax.set_ylabel(f"Rs / {p.unit}")
        ax.legend(fontsize=8, ncol=2)
        fig.tight_layout()
        fig.savefig(FIG_DIR / f"demo_vs_reference_{slug(pname)}.png", dpi=130)
        plt.close(fig)


def _shop_id(db, user):
    from app.models import Shop
    col = "user_id" if hasattr(Shop, "user_id") else "owner_id"
    return db.execute(select(Shop.id).where(getattr(Shop, col) == user.id)).scalar_one()


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        ref = load_reference(db)
        if ref.empty:
            raise SystemExit("reference_prices is empty. Run build_reference and load_reference first.")
        plot_each_commodity(ref)
        plot_normalised(ref)
        plot_demo_vs_reference(db, ref)
    finally:
        db.close()
    print(f"Saved {len(list(FIG_DIR.glob('*.png')))} figures in {FIG_DIR}")


if __name__ == "__main__":
    main()
