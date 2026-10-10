"""
routers/products.py - products of the logged-in shop.

GET    /api/products?q=&category=     list (search by name, filter by category)
POST   /api/products                  create (opening stock becomes current stock)
PUT    /api/products/{id}             update
DELETE /api/products/{id}             delete (409 if it already has purchases or sales)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_shop
from app.models import Alert, Product, Purchase, Sale, Shop, supplier_products
from app.schemas import ProductCreate, ProductOut, ProductUpdate
from app.services.activity import log_activity
from app.services.cache import invalidate_shop
from app.services.common import commodity_exists, get_shop_product, stock_status

router = APIRouter(prefix="/api/products", tags=["products"])


def to_out(p: Product) -> dict:
    return {
        "id": p.id, "name": p.name, "category": p.category, "unit": p.unit,
        "current_stock": p.current_stock, "reorder_level": p.reorder_level,
        "selling_price": p.selling_price, "reference_commodity": p.reference_commodity,
        "stock_status": stock_status(p.current_stock, p.reorder_level),
    }


def _check_name_free(db: Session, shop_id: int, name: str, exclude_id: int | None = None) -> None:
    q = select(Product.id).where(Product.shop_id == shop_id, func.lower(Product.name) == name.strip().lower())
    if exclude_id is not None:
        q = q.where(Product.id != exclude_id)
    if db.execute(q).first() is not None:
        raise HTTPException(status_code=409, detail="A product with this name already exists")


def _check_commodity(db: Session, commodity: str | None) -> str | None:
    commodity = (commodity or "").strip() or None             # "" means "None"
    if commodity and not commodity_exists(db, commodity):
        raise HTTPException(status_code=422, detail=f"Unknown reference commodity '{commodity}'")
    return commodity


@router.get("", response_model=list[ProductOut])
def list_products(q: str | None = Query(None), category: str | None = Query(None),
                  db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    query = select(Product).where(Product.shop_id == shop.id)
    if q and q.strip():
        query = query.where(Product.name.ilike(f"%{q.strip()}%"))
    if category and category != "All":
        query = query.where(Product.category == category)
    return [to_out(p) for p in db.execute(query.order_by(Product.name)).scalars()]


@router.post("", response_model=ProductOut, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Product name is required")
    _check_name_free(db, shop.id, name)
    p = Product(
        shop_id=shop.id, name=name, category=payload.category, unit=payload.unit,
        current_stock=payload.opening_stock, reorder_level=payload.reorder_level,
        selling_price=payload.selling_price, reference_commodity=_check_commodity(db, payload.reference_commodity),
    )
    db.add(p)
    log_activity(db, shop.id, "product", f"Product added - {p.name} ({p.unit})")
    db.commit()
    db.refresh(p)
    invalidate_shop(shop.id)
    return to_out(p)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db),
                   shop: Shop = Depends(get_current_shop)):
    p = get_shop_product(db, shop.id, product_id)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None:
        changes["name"] = changes["name"].strip()
        if not changes["name"]:
            raise HTTPException(status_code=422, detail="Product name is required")
        _check_name_free(db, shop.id, changes["name"], exclude_id=p.id)
    if "reference_commodity" in changes:
        changes["reference_commodity"] = _check_commodity(db, changes["reference_commodity"])
    for field, value in changes.items():
        if value is None and field not in ("category", "selling_price", "reference_commodity"):
            continue                                            # these three may be cleared with null
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    invalidate_shop(shop.id)
    return to_out(p)


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    p = get_shop_product(db, shop.id, product_id)
    used = (db.execute(select(func.count()).select_from(Purchase).where(Purchase.product_id == p.id)).scalar()
            or db.execute(select(func.count()).select_from(Sale).where(Sale.product_id == p.id)).scalar())
    if used:
        raise HTTPException(status_code=409, detail="Product has purchases or sales and cannot be deleted")
    db.execute(delete(supplier_products).where(supplier_products.c.product_id == p.id))
    db.execute(delete(Alert).where(Alert.product_id == p.id))
    db.delete(p)
    db.commit()
    invalidate_shop(shop.id)
