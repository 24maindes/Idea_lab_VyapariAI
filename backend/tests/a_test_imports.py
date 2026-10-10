"""CSV import: dry run, validation messages, all-or-nothing, stock updates, templates."""
import datetime as dt
import io
from pathlib import Path

import pytest

from conftest import TODAY

SAMPLES = Path(__file__).resolve().parents[2] / "docs" / "samples"


def upload(client, headers, kind, content, name="file.csv", **params):
    if isinstance(content, str):
        content = content.encode("utf-8")
    q = "&".join(f"{k}={v}" for k, v in params.items())
    return client.post(f"/api/import/{kind}?{q}", headers=headers, files={"file": (name, io.BytesIO(content), "text/csv")})


def stock(client, d):
    return {p["name"]: p["currentStock"] for p in client.get("/api/products", headers=d["headers"]).json()}


def d(days_ago):
    return (TODAY - dt.timedelta(days=days_ago)).isoformat()


# ---------------------------------------------------------------- products
def test_products_import_creates_rows(client, register_user, create_shop, add_reference):
    add_reference("Rice")
    h = register_user()
    create_shop(h)
    csv_text = "name,category,unit,opening_stock,reorder_level,selling_price,reference_commodity\nRice,Grains,kg,50,20,48,Rice\nSalt,Staples,packet,30,10,,\n"
    r = upload(client, h, "products", csv_text, dryRun="false").json()
    assert r["imported"] and r["rowsValid"] == 2 and r["created"] == {"products": 2}
    prods = {p["name"]: p for p in client.get("/api/products", headers=h).json()}
    assert prods["Rice"]["currentStock"] == 50 and prods["Rice"]["referenceCommodity"] == "Rice" and prods["Salt"]["unit"] == "packet"
    assert "CSV import - 2 products added" in [a["text"] for a in client.get("/api/activity", headers=h).json()]


def test_products_validation_messages(client, register_user, create_shop, create_product):
    h = register_user()
    create_shop(h)
    create_product(h, "Existing")
    csv_text = ("name,category,unit,opening_stock,reorder_level,selling_price,reference_commodity\n"
                ",Grains,kg,1,1,1,\n"                       # row 2: no name
                "A,Grains,bag,1,1,1,\n"                     # row 3: bad unit
                "B,Grains,kg,-4,1,1,\n"                     # row 4: negative stock
                "C,Grains,kg,1,1,abc,\n"                    # row 5: price not a number
                "D,Grains,kg,1,1,1,Unobtainium\n"           # row 6: unknown commodity
                "existing,Grains,kg,1,1,1,\n"               # row 7: already exists (case-insensitive)
                "E,Grains,kg,1,1,1,\nE,Grains,kg,1,1,1,\n") # row 8 ok, row 9 duplicate of 8
    r = upload(client, h, "products", csv_text, dryRun="true").json()
    got = {(e["row"], e["field"]) for e in r["errors"]}
    assert got == {(2, "name"), (3, "unit"), (4, "opening_stock"), (5, "selling_price"), (6, "reference_commodity"), (7, "name"), (9, "name")}
    assert r["rowsTotal"] == 8 and r["rowsValid"] == 1 and r["rowsInvalid"] == 7 and r["dryRun"] is True


# ---------------------------------------------------------------- dry run writes nothing
def test_dry_run_writes_nothing(client, shop_with_data):
    h = shop_with_data["headers"]
    csv_text = f"date,product,supplier,quantity,unit_price\n{d(5)},Rice,ABC Traders,10,40\n"
    r = upload(client, h, "purchases", csv_text, dryRun="true").json()
    assert r["rowsValid"] == 1 and r["errors"] == [] and r["imported"] is False
    assert stock(client, shop_with_data)["Rice"] == 0
    assert client.get("/api/purchases", headers=h).json()["total"] == 0


# ---------------------------------------------------------------- purchases
def test_valid_purchases_import_changes_stock(client, shop_with_data):
    h = shop_with_data["headers"]
    csv_text = f"date,product,supplier,quantity,unit_price\n{d(10)},Rice,ABC Traders,20,40\n{d(3)},rice ,abc traders,5.5,41\n"   # case + spaces tolerated
    r = upload(client, h, "purchases", csv_text, dryRun="false").json()
    assert r["imported"] and r["created"] == {"purchases": 2, "suppliers": 0}
    assert stock(client, shop_with_data)["Rice"] == 25.5
    assert client.get("/api/purchases", headers=h).json()["total"] == 2


def test_purchase_errors_have_row_numbers(client, shop_with_data):
    h = shop_with_data["headers"]
    future = (TODAY + dt.timedelta(days=3)).isoformat()
    csv_text = ("date,product,supplier,quantity,unit_price\n"
                f"{d(5)},Nothing,ABC Traders,10,40\n"           # row 2 unknown product
                f"{d(5)},Rice,Nobody,10,40\n"                   # row 3 unknown supplier
                f"{d(5)},Rice,ABC Traders,0,40\n"               # row 4 quantity 0
                f"{d(5)},Rice,ABC Traders,10,abc\n"             # row 5 price not a number
                f"{future},Rice,ABC Traders,10,40\n"            # row 6 future date
                "not-a-date,Rice,ABC Traders,10,40\n"           # row 7 bad date
                f"{d(2)},Rice,ABC Traders,10,40\n"              # row 8 OK
                f"{d(2)},Rice,ABC Traders,10,40\n")             # row 9 duplicate of row 8
    r = upload(client, h, "purchases", csv_text, dryRun="true").json()
    assert {(e["row"], e["field"]) for e in r["errors"]} == {(2, "product"), (3, "supplier"), (4, "quantity"), (5, "unit_price"), (6, "date"), (7, "date"), (9, "row")}
    assert r["rowsValid"] == 1 and r["rowsInvalid"] == 7


def test_all_or_nothing_unless_skip_invalid(client, shop_with_data):
    h = shop_with_data["headers"]
    csv_text = f"date,product,supplier,quantity,unit_price\n{d(5)},Rice,ABC Traders,10,40\n{d(4)},Nothing,ABC Traders,10,40\n"
    r = upload(client, h, "purchases", csv_text, dryRun="false").json()
    assert r["imported"] is False and r["created"] == {} and "Nothing was imported" in r["message"]
    assert stock(client, shop_with_data)["Rice"] == 0                       # even the valid row was NOT saved
    r = upload(client, h, "purchases", csv_text, dryRun="false", skipInvalid="true").json()
    assert r["imported"] and r["rowsValid"] == 1 and r["rowsInvalid"] == 1
    assert stock(client, shop_with_data)["Rice"] == 10


def test_create_missing_suppliers(client, shop_with_data):
    h = shop_with_data["headers"]
    csv_text = f"date,product,supplier,quantity,unit_price\n{d(5)},Rice,Brand New Traders,10,40\n{d(4)},Rice,brand new traders,5,41\n"
    r = upload(client, h, "purchases", csv_text, dryRun="false", createMissingSuppliers="true").json()
    assert r["imported"] and r["created"] == {"purchases": 2, "suppliers": 1}      # one supplier, created once
    assert "Brand New Traders" in [s["name"] for s in client.get("/api/suppliers", headers=h).json()]


def test_import_of_purchases_runs_the_anomaly_scan(client, shop_with_data):
    h = shop_with_data["headers"]
    rows = "".join(f"{d(60 - 7 * i)},Rice,ABC Traders,10,40\n" for i in range(8)) + f"{d(1)},Rice,ABC Traders,10,58\n"   # 8 normal ones (60..11 days ago), last one +45 %
    upload(client, h, "purchases", "date,product,supplier,quantity,unit_price\n" + rows, dryRun="false")
    kinds = [a["type"] for a in client.get("/api/alerts", headers=h).json()]
    assert "price_anomaly" in kinds


# ---------------------------------------------------------------- sales
def test_sales_processed_chronologically(client, shop_with_data):
    h = shop_with_data["headers"]
    client.post("/api/purchases", headers=h, json={"productId": shop_with_data["product"]["id"], "supplierId": shop_with_data["supplier"]["id"],
                "quantity": 10, "unitPrice": 40, "purchaseDate": d(20)})
    # listed out of order: the 8 kg sale is earlier, so the later 5 kg sale would push stock to -3
    csv_text = f"date,product,quantity,unit_price\n{d(2)},Rice,5,50\n{d(5)},Rice,8,50\n"
    r = upload(client, h, "sales", csv_text, dryRun="true").json()
    assert [(e["row"], e["field"]) for e in r["errors"]] == [(2, "quantity")] and "below zero" in r["errors"][0]["message"]
    ok = upload(client, h, "sales", f"date,product,quantity,unit_price\n{d(2)},Rice,2,50\n{d(5)},Rice,8,50\n", dryRun="false").json()
    assert ok["imported"] and stock(client, shop_with_data)["Rice"] == 0


# ---------------------------------------------------------------- file level problems
@pytest.mark.parametrize("content, status, phrase", [
    (b"", 422, "empty"),
    ("date,product\n2026-01-01,Rice\n", 422, "Missing column"),
    ("date,product,supplier,quantity,unit_price\n", 422, "no data rows"),
    (b"\xff\xfe\x00bad", 422, "UTF-8"),
])
def test_bad_files(client, shop_with_data, content, status, phrase):
    r = upload(client, shop_with_data["headers"], "purchases", content, dryRun="true")
    assert r.status_code == status and phrase in r.json()["detail"]


def test_bom_and_comma_numbers_are_handled(client, shop_with_data):
    h = shop_with_data["headers"]
    text = "\ufeffdate,product,supplier,quantity,unit_price\n" + f'{d(3)},Rice,ABC Traders,"1,000",40\n'
    r = upload(client, h, "purchases", text, dryRun="false").json()
    assert r["imported"] and stock(client, shop_with_data)["Rice"] == 1000


def test_file_over_5mb_is_rejected(client, shop_with_data):
    big = b"date,product,supplier,quantity,unit_price\n" + b"x" * (5 * 1024 * 1024 + 10)
    assert upload(client, shop_with_data["headers"], "purchases", big, dryRun="true").status_code == 413


def test_unknown_type_and_login_required(client, shop_with_data):
    assert upload(client, shop_with_data["headers"], "invoices", "a,b\n1,2\n").status_code == 404
    assert client.post("/api/import/products", files={"file": ("f.csv", b"name,unit\nA,kg\n")}).status_code == 401


def test_imports_stay_inside_the_shop(client, shop_with_data, register_user, create_shop):
    h2 = register_user("o@test.com")
    create_shop(h2)
    csv_text = f"date,product,supplier,quantity,unit_price\n{d(3)},Rice,ABC Traders,10,40\n"
    r = upload(client, h2, "purchases", csv_text, dryRun="true").json()
    assert r["rowsValid"] == 0 and {e["field"] for e in r["errors"]} == {"product", "supplier"}      # the other shop's data is invisible


# ---------------------------------------------------------------- templates and the two sample files
@pytest.mark.parametrize("kind", ["products", "purchases", "sales"])
def test_templates_download(client, shop_with_data, kind):
    r = client.get(f"/api/import/template/{kind}", headers=shop_with_data["headers"])
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv") and f"{kind}_template.csv" in r.headers["content-disposition"]
    lines = r.text.strip().splitlines()
    assert len(lines) == 3 and "," in lines[0]
    assert client.get("/api/import/template/nothing", headers=shop_with_data["headers"]).status_code == 404


def test_sample_files(client, register_user, create_shop, add_reference):
    add_reference("Rice")
    h = register_user()
    create_shop(h)
    for name, unit in [("Rice", "kg"), ("Wheat Atta", "kg"), ("Sugar", "kg"), ("Toor Dal", "kg")]:
        client.post("/api/products", headers=h, json={"name": name, "unit": unit})
    for s in ("ABC Traders", "GoodFood Co."):
        client.post("/api/suppliers", headers=h, json={"name": s})
    good = (SAMPLES / "purchases_valid_20.csv").read_bytes()
    r = upload(client, h, "purchases", good, dryRun="true").json()
    assert r["rowsTotal"] == 20 and r["rowsValid"] == 20 and r["errors"] == []
    bad = (SAMPLES / "purchases_with_5_errors.csv").read_bytes()
    r = upload(client, h, "purchases", bad, dryRun="true").json()
    assert r["rowsInvalid"] == 5 and sorted(e["row"] for e in r["errors"]) == [3, 5, 7, 9, 11]
    assert upload(client, h, "purchases", good, dryRun="false").json()["created"]["purchases"] == 20
