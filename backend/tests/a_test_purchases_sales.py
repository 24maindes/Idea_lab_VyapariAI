"""Purchases, sales, inventory and the sales summary."""
import datetime as dt

from conftest import TODAY


def buy(client, d, qty=10, price=40.0, date=None):
    return client.post("/api/purchases", headers=d["headers"], json={
        "productId": d["product"]["id"], "supplierId": d["supplier"]["id"], "quantity": qty, "unitPrice": price,
        "purchaseDate": (date or TODAY).isoformat()})


def sell(client, d, qty=1, price=None, date=None):
    body = {"productId": d["product"]["id"], "quantity": qty, "saleDate": (date or TODAY).isoformat()}
    if price is not None:
        body["unitPrice"] = price
    return client.post("/api/sales", headers=d["headers"], json=body)


def stock(client, d):
    return client.get("/api/products", headers=d["headers"]).json()[0]["currentStock"]


def test_purchase_raises_stock_and_returns_total(client, shop_with_data):
    r = buy(client, shop_with_data, qty=40, price=42.5)
    assert r.status_code == 201
    b = r.json()
    assert b["total"] == 1700.0 and b["productName"] == "Rice" and b["supplierName"] == "ABC Traders"
    assert stock(client, shop_with_data) == 40


def test_delete_purchase_restores_stock(client, shop_with_data):
    pid = buy(client, shop_with_data, qty=40).json()["id"]
    assert client.delete(f"/api/purchases/{pid}", headers=shop_with_data["headers"]).status_code == 204
    assert stock(client, shop_with_data) == 0


def test_delete_purchase_blocked_when_stock_already_sold(client, shop_with_data):
    pid = buy(client, shop_with_data, qty=10).json()["id"]
    sell(client, shop_with_data, qty=8)
    r = client.delete(f"/api/purchases/{pid}", headers=shop_with_data["headers"])
    assert r.status_code == 409 and "already sold" in r.json()["detail"]
    assert stock(client, shop_with_data) == 2


def test_purchase_validation(client, shop_with_data):
    d = shop_with_data
    assert buy(client, d, qty=0).status_code == 422
    assert buy(client, d, qty=-5).status_code == 422
    assert buy(client, d, price=0).status_code == 422
    r = buy(client, d, date=TODAY + dt.timedelta(days=2))
    assert r.status_code == 422 and "future" in r.json()["detail"]
    assert stock(client, d) == 0                                     # nothing was saved


def test_purchase_list_filters_sort_and_pages(client, shop_with_data):
    d = shop_with_data
    for i, price in enumerate([40, 45, 41]):
        buy(client, d, qty=1, price=price, date=TODAY - dt.timedelta(days=i))
    body = client.get("/api/purchases?pageSize=2&sort=price_desc", headers=d["headers"]).json()
    assert body["total"] == 3 and [x["unitPrice"] for x in body["items"]] == [45, 41]
    body = client.get("/api/purchases?page=2&pageSize=2&sort=price_desc", headers=d["headers"]).json()
    assert [x["unitPrice"] for x in body["items"]] == [40]
    frm = (TODAY - dt.timedelta(days=1)).isoformat()
    assert client.get(f"/api/purchases?from={frm}", headers=d["headers"]).json()["total"] == 2
    assert client.get("/api/purchases?sort=nonsense", headers=d["headers"]).status_code == 422


def test_sale_reduces_stock_and_defaults_to_selling_price(client, shop_with_data):
    d = shop_with_data
    buy(client, d, qty=20)
    r = sell(client, d, qty=5)
    assert r.status_code == 201 and r.json()["unitPrice"] == 50 and r.json()["total"] == 250
    assert stock(client, d) == 15


def test_sale_above_stock_is_400_with_message(client, shop_with_data):
    d = shop_with_data
    buy(client, d, qty=3)
    r = sell(client, d, qty=5)
    assert r.status_code == 400 and r.json()["detail"] == "Only 3 kg in stock"
    assert stock(client, d) == 3


def test_sale_needs_a_price(client, register_user, create_shop, create_product, create_supplier):
    h = register_user("np@test.com")
    create_shop(h)
    p = create_product(h, "Salt", openingStock=10)                  # no selling price
    r = client.post("/api/sales", headers=h, json={"productId": p["id"], "quantity": 1, "saleDate": TODAY.isoformat()})
    assert r.status_code == 400


def test_delete_sale_restores_stock(client, shop_with_data):
    d = shop_with_data
    buy(client, d, qty=10)
    sid = sell(client, d, qty=4).json()["id"]
    assert stock(client, d) == 6
    assert client.delete(f"/api/sales/{sid}", headers=d["headers"]).status_code == 204
    assert stock(client, d) == 10


def test_sales_summary_on_tiny_dataset(client, shop_with_data):
    d = shop_with_data
    buy(client, d, qty=100, price=40, date=TODAY - dt.timedelta(days=20))      # cost basis Rs 40
    sell(client, d, qty=10, price=50, date=TODAY - dt.timedelta(days=4))       # first sale 4 days ago -> 5 days
    sell(client, d, qty=5, price=60, date=TODAY)
    s = client.get("/api/sales/summary?days=30", headers=d["headers"]).json()
    assert s["totals"]["today"] == {"revenue": 300.0, "units": 5.0}
    assert s["totals"]["last7Days"] == {"revenue": 800.0, "units": 15.0}
    p = s["products"][0]
    assert p["productName"] == "Rice" and p["qtySold"] == 15 and p["revenue"] == 800
    assert p["avgDailySales"] == 3.0                                           # 15 units / 5 days
    assert p["grossProfit"] == 800 - 15 * 40                                   # 200


def test_inventory_fields(client, shop_with_data):
    d = shop_with_data
    buy(client, d, qty=30, price=40, date=TODAY - dt.timedelta(days=3))
    sell(client, d, qty=6, date=TODAY - dt.timedelta(days=2))
    row = client.get("/api/inventory", headers=d["headers"]).json()[0]
    assert row["currentStock"] == 24 and row["lastPurchasePrice"] == 40 and row["stockValue"] == 960
    assert row["avgDailySales"] == 2.0 and row["daysOfCover"] == 12.0          # 6 units over 3 days; 24 / 2
    assert row["status"] == "In Stock"


def test_inventory_without_sales_has_null_cover(client, shop_with_data):
    row = client.get("/api/inventory", headers=shop_with_data["headers"]).json()[0]
    assert row["avgDailySales"] is None and row["daysOfCover"] is None and row["lastPurchaseDate"] is None


def test_other_shop_cannot_touch_my_data(client, shop_with_data, register_user, create_shop):
    d = shop_with_data
    pid = buy(client, d, qty=10).json()["id"]
    sid = sell(client, d, qty=1).json()["id"]
    h2 = register_user("other@test.com")
    create_shop(h2)
    assert client.get("/api/products", headers=h2).json() == []
    assert client.delete(f"/api/purchases/{pid}", headers=h2).status_code == 404
    assert client.delete(f"/api/sales/{sid}", headers=h2).status_code == 404
    assert client.delete(f"/api/products/{d['product']['id']}", headers=h2).status_code == 404
    assert client.post("/api/purchases", headers=h2, json={"productId": d["product"]["id"], "supplierId": d["supplier"]["id"],
                       "quantity": 1, "unitPrice": 1, "purchaseDate": TODAY.isoformat()}).status_code == 404
    assert client.get("/api/purchases", headers=h2).json()["total"] == 0


def test_endpoints_need_login(client):
    for path in ["/api/products", "/api/suppliers", "/api/purchases", "/api/sales", "/api/inventory", "/api/activity"]:
        assert client.get(path).status_code == 401, path
