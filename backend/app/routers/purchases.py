"""
routers/purchases.py - record what the shop bought from suppliers.

POST   /api/purchases        add a purchase (stock goes UP in the same transaction)
GET    /api/purchases        list with filters, sorting and pages
DELETE /api/purchases/{id}   undo a purchase (stock goes back DOWN; 409 if that would make stock negative)
"""
import datetime as dt
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_shop
from app.models import Alert, Product, Purchase, Shop, Supplier
from app.schemas import PurchaseCreate, PurchaseOut, PurchasePage
from app.services.activity import log_activity
from app.services.cache import invalidate_shop
from app.services.common import check_not_future, fmt_qty, get_shop_product, get_shop_supplier
from app.services.purchase_hooks import after_purchase

router = APIRouter(prefix="/api/purchases", tags=["purchases"])

SORTS = {
    "date_desc": (Purchase.purchase_date.desc(), Purchase.id.desc()),
    "date_asc": (Purchase.purchase_date.asc(), Purchase.id.asc()),
    "price_desc": (Purchase.unit_price.desc(), Purchase.id.desc()),
    "price_asc": (Purchase.unit_price.asc(), Purchase.id.asc()),
}


def to_out(p: Purchase, product_name: str, unit: str | None, supplier_name: str | None, insights=None) -> dict:
    return {
        "id": p.id, "product_id": p.product_id, "product_name": product_name, "unit": unit,
        "supplier_id": p.supplier_id, "supplier_name": supplier_name, "quantity": p.quantity,
        "unit_price": p.unit_price, "total": round(p.quantity * p.unit_price, 2),
        "purchase_date": p.purchase_date, "insights": insights,
    }


@router.post("", response_model=PurchaseOut, status_code=201)
def create_purchase(payload: PurchaseCreate, db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    product = get_shop_product(db, shop.id, payload.product_id)          # 404 if it is another shop's product
    supplier = get_shop_supplier(db, shop.id, payload.supplier_id)
    check_not_future(payload.purchase_date, "Purchase date")

    purchase = Purchase(shop_id=shop.id, product_id=product.id, supplier_id=supplier.id,
                        quantity=payload.quantity, unit_price=payload.unit_price,
                        purchase_date=payload.purchase_date)
    db.add(purchase)
    db.flush()                                                           # gives the purchase an id
    product.current_stock = round(product.current_stock + payload.quantity, 6)
    log_activity(db, shop.id, "purchase",
                 f"Purchase recorded - {fmt_qty(payload.quantity)} {product.unit} {product.name}")
    insights = after_purchase(db, purchase)                              # e.g. {"anomaly": {...}}
    db.commit()
    invalidate_shop(shop.id)
    return to_out(purchase, product.name, product.unit, supplier.name, insights)


@router.get("", response_model=PurchasePage)
def list_purchases(
    product_id: int | None = Query(None, alias="productId"),
    supplier_id: int | None = Query(None, alias="supplierId"),
    date_from: dt.date | None = Query(None, alias="from"),
    date_to: dt.date | None = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    sort: Literal["date_desc", "date_asc", "price_desc", "price_asc"] = "date_desc",
    db: Session = Depends(get_db),
    shop: Shop = Depends(get_current_shop),
):
    where = [Purchase.shop_id == shop.id]
    if product_id is not None:
        where.append(Purchase.product_id == product_id)
    if supplier_id is not None:
        where.append(Purchase.supplier_id == supplier_id)
    if date_from:
        where.append(Purchase.purchase_date >= date_from)
    if date_to:
        where.append(Purchase.purchase_date <= date_to)

    total = db.execute(select(func.count()).select_from(Purchase).where(*where)).scalar()
    rows = db.execute(
        select(Purchase, Product.name, Product.unit, Supplier.name)
        .join(Product, Product.id == Purchase.product_id)
        .outerjoin(Supplier, Supplier.id == Purchase.supplier_id)
        .where(*where).order_by(*SORTS[sort]).limit(page_size).offset((page - 1) * page_size)
    ).all()
    return {"items": [to_out(p, pn, u, sn) for p, pn, u, sn in rows], "total": total, "page": page, "page_size": page_size}


@router.delete("/{purchase_id}", status_code=204)
def delete_purchase(purchase_id: int, db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    purchase = db.execute(select(Purchase).where(Purchase.id == purchase_id, Purchase.shop_id == shop.id)).scalar_one_or_none()
    if purchase is None:
        raise HTTPException(status_code=404, detail="Purchase not found")
    product = db.get(Product, purchase.product_id)
    new_stock = round(product.current_stock - purchase.quantity, 6)
    if new_stock < 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: {fmt_qty(purchase.quantity)} {product.unit} of {product.name} "
                   f"from this purchase were already sold (only {fmt_qty(product.current_stock)} {product.unit} in stock)")
    product.current_stock = new_stock
    db.execute(delete(Alert).where(Alert.purchase_id == purchase.id))   # its alerts make no sense any more
    db.delete(purchase)
    db.commit()
    invalidate_shop(shop.id)
