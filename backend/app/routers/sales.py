"""
routers/sales.py - record what the shop sold.

POST   /api/sales            add a sale (stock goes DOWN; 400 if there is not enough stock)
GET    /api/sales            list with filters and pages
GET    /api/sales/summary    totals and per-product statistics (?days=30)
DELETE /api/sales/{id}       undo a sale (stock goes back UP)
"""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_shop
from app.models import Product, Sale, Shop
from app.schemas import SaleCreate, SaleOut, SalePage
from app.services.activity import log_activity
from app.services.cache import invalidate_shop
from app.services.common import check_not_future, fmt_qty, get_shop_product
from app.services.sales_summary import get_sales_summary

router = APIRouter(prefix="/api/sales", tags=["sales"])


def to_out(s: Sale, product_name: str, unit: str | None) -> dict:
    return {"id": s.id, "product_id": s.product_id, "product_name": product_name, "unit": unit,
            "quantity": s.quantity, "unit_price": s.unit_price, "total": round(s.quantity * s.unit_price, 2),
            "sale_date": s.sale_date}


@router.post("", response_model=SaleOut, status_code=201)
def create_sale(payload: SaleCreate, db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    product = get_shop_product(db, shop.id, payload.product_id)
    check_not_future(payload.sale_date, "Sale date")
    price = payload.unit_price if payload.unit_price is not None else product.selling_price
    if price is None:
        raise HTTPException(status_code=400, detail="No price given and this product has no selling price set")
    if payload.quantity > product.current_stock + 1e-9:
        raise HTTPException(status_code=400, detail=f"Only {fmt_qty(product.current_stock)} {product.unit} in stock")

    sale = Sale(shop_id=shop.id, product_id=product.id, quantity=payload.quantity, unit_price=price,
                sale_date=payload.sale_date)
    db.add(sale)
    db.flush()
    product.current_stock = round(product.current_stock - payload.quantity, 6)
    log_activity(db, shop.id, "sale", f"Sale recorded - {fmt_qty(payload.quantity)} {product.unit} {product.name}")
    db.commit()
    invalidate_shop(shop.id)
    return to_out(sale, product.name, product.unit)


@router.get("/summary")                                   # declared before /{id} routes
def sales_summary(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    return get_sales_summary(db, shop.id, days)


@router.get("", response_model=SalePage)
def list_sales(
    product_id: int | None = Query(None, alias="productId"),
    date_from: dt.date | None = Query(None, alias="from"),
    date_to: dt.date | None = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    sort: str = Query("date_desc", pattern="^(date|price|total)_(asc|desc)$"),
    db: Session = Depends(get_db),
    shop: Shop = Depends(get_current_shop),
):
    where = [Sale.shop_id == shop.id]
    if product_id is not None:
        where.append(Sale.product_id == product_id)
    if date_from:
        where.append(Sale.sale_date >= date_from)
    if date_to:
        where.append(Sale.sale_date <= date_to)
    column = {"date": Sale.sale_date, "price": Sale.unit_price, "total": Sale.quantity * Sale.unit_price}[sort.split("_")[0]]
    order = column.asc() if sort.endswith("asc") else column.desc()

    total = db.execute(select(func.count()).select_from(Sale).where(*where)).scalar()
    rows = db.execute(
        select(Sale, Product.name, Product.unit).join(Product, Product.id == Sale.product_id)
        .where(*where).order_by(order, Sale.id.desc()).limit(page_size).offset((page - 1) * page_size)
    ).all()
    return {"items": [to_out(s, pn, u) for s, pn, u in rows], "total": total, "page": page, "page_size": page_size}


@router.delete("/{sale_id}", status_code=204)
def delete_sale(sale_id: int, db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    sale = db.execute(select(Sale).where(Sale.id == sale_id, Sale.shop_id == shop.id)).scalar_one_or_none()
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")
    product = db.get(Product, sale.product_id)
    product.current_stock = round(product.current_stock + sale.quantity, 6)
    db.delete(sale)
    db.commit()
    invalidate_shop(shop.id)
