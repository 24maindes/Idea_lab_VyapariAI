"""
routers/imports.py - CSV bulk import.

POST /api/import/{type}?dryRun=true|false&createMissingSuppliers=false&skipInvalid=false     (multipart file upload)
GET  /api/import/template/{type}                                                           (sample CSV download)

type = products | purchases | sales
A dry run checks the file and writes NOTHING. A real import is all-or-nothing unless skipInvalid=true.
"""
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_shop
from app.models import Shop
from app.services import importer as imp
from app.services.activity import log_activity
from app.services.anomaly_service import scan_shop
from app.services.cache import invalidate_shop

router = APIRouter(prefix="/api/import", tags=["import"])
TYPES = ("products", "purchases", "sales")


def _check_type(kind: str) -> None:
    if kind not in TYPES:
        raise HTTPException(status_code=404, detail=f"Unknown import type '{kind}'. Use one of: {', '.join(TYPES)}")


@router.get("/template/{kind}")
def template(kind: str, user_shop: Shop = Depends(get_current_shop)):
    _check_type(kind)
    return Response(content=imp.template_csv(kind), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{kind}_template.csv"'})


@router.post("/{kind}")
async def import_csv(
    kind: str,
    file: UploadFile = File(...),
    dry_run: bool = Query(True, alias="dryRun"),
    create_missing_suppliers: bool = Query(False, alias="createMissingSuppliers"),
    skip_invalid: bool = Query(False, alias="skipInvalid"),
    db: Session = Depends(get_db),
    shop: Shop = Depends(get_current_shop),
):
    _check_type(kind)
    raw = await file.read(imp.MAX_BYTES + 1)
    rows = imp.read_csv(raw, kind)

    if kind == "products":
        good, errors = imp.validate_products(db, shop, rows)
    elif kind == "purchases":
        good, errors, _ = imp.validate_purchases(db, shop, rows, create_missing_suppliers)
    else:
        good, errors = imp.validate_sales(db, shop, rows)

    invalid_rows = len({e["row"] for e in errors})
    result = {"rowsTotal": len(rows), "rowsValid": len(good), "rowsInvalid": invalid_rows, "errors": errors[:200],
              "created": {}, "dryRun": dry_run, "imported": False, "message": ""}

    if dry_run:
        result["message"] = "Dry run: nothing was saved." + (" The file is ready to import." if not errors else " Fix the errors below, then import.")
        return result
    if errors and not skip_invalid:
        result["message"] = f"Nothing was imported because {invalid_rows} row(s) have errors. Fix them or choose 'skip invalid rows'."
        return result
    if not good:
        result["message"] = "There are no valid rows to import."
        return result

    # ---- real import: ONE transaction
    try:
        if kind == "products":
            created = imp.apply_products(db, shop, good)
        elif kind == "purchases":
            created = imp.apply_purchases(db, shop, good)
        else:
            created = imp.apply_sales(db, shop, good)
        log_activity(db, shop.id, "import", f"CSV import - {len(good)} {kind} added")
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="The import failed and nothing was saved. Please try again.")

    invalidate_shop(shop.id)
    if kind == "purchases":
        try:
            scan_shop(db, shop)                           # imported purchases are checked for unusual prices
        except Exception:
            db.rollback()
    result.update(created=created, imported=True, message=f"Imported {len(good)} {kind}.")
    return result
