"""
routers/inventory.py - one row per product with stock status, last purchase and days of cover.

GET /api/inventory
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_shop
from app.models import Product, Purchase, Shop
from app.services.common import stock_status
from app.services.sales_summary import get_sales_summary

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("")
def inventory(db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    products = db.execute(select(Product).where(Product.shop_id == shop.id).order_by(Product.name)).scalars().all()

    # latest purchase per product (window function: rank purchases newest first, keep rank 1)
    rn = func.row_number().over(partition_by=Purchase.product_id,
                                order_by=(Purchase.purchase_date.desc(), Purchase.id.desc())).label("rn")
    sub = select(Purchase.product_id, Purchase.purchase_date, Purchase.unit_price, rn).where(Purchase.shop_id == shop.id).subquery()
    last = {r[0]: (r[1], r[2]) for r in db.execute(select(sub.c.product_id, sub.c.purchase_date, sub.c.unit_price).where(sub.c.rn == 1))}

    sales = {p["productId"]: p["avgDailySales"] for p in get_sales_summary(db, shop.id, 30)["products"]}

    items = []
    for p in products:
        last_date, last_price = last.get(p.id, (None, None))
        avg = sales.get(p.id)
        items.append({
            "id": p.id, "name": p.name, "category": p.category, "unit": p.unit,
            "currentStock": p.current_stock, "reorderLevel": p.reorder_level,
            "status": stock_status(p.current_stock, p.reorder_level),
            "lastPurchaseDate": last_date, "lastPurchasePrice": last_price,
            "stockValue": round(p.current_stock * last_price, 2) if last_price is not None else 0.0,
            "avgDailySales": avg,
            "daysOfCover": round(p.current_stock / avg, 1) if avg else None,
        })
    return items
