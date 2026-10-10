"""
services/common.py - small helpers shared by several routers.
"""
import datetime as dt

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product, ReferencePrice, Supplier


def fmt_qty(x: float) -> str:
    """40.0 -> '40', 2.5 -> '2.5' (short numbers for messages)."""
    return f"{x:g}"


def stock_status(stock: float, reorder_level: float) -> str:
    if stock <= 0:
        return "Out of Stock"
    if stock <= reorder_level:
        return "Low Stock"
    return "In Stock"


def get_shop_product(db: Session, shop_id: int, product_id: int) -> Product:
    """A product, but ONLY if it belongs to this shop (other shops' ids look like 'not found')."""
    p = db.execute(select(Product).where(Product.id == product_id, Product.shop_id == shop_id)).scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return p


def get_shop_supplier(db: Session, shop_id: int, supplier_id: int) -> Supplier:
    s = db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.shop_id == shop_id)).scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return s


def commodity_exists(db: Session, name: str) -> bool:
    return db.execute(select(ReferencePrice.id).where(ReferencePrice.commodity == name).limit(1)).first() is not None


def check_not_future(d: dt.date, what: str = "Date") -> None:
    if d > dt.date.today():
        raise HTTPException(status_code=422, detail=f"{what} cannot be in the future")
