"""Products and suppliers API."""
import pytest


def test_product_crud(client, register_user, create_shop, add_reference):
    add_reference("Rice")
    h = register_user()
    create_shop(h)
    r = client.post("/api/products", headers=h, json={"name": "Rice", "category": "Grains", "unit": "kg",
                                                       "openingStock": 25, "reorderLevel": 10, "referenceCommodity": "Rice"})
    assert r.status_code == 201
    p = r.json()
    assert p["currentStock"] == 25 and p["stockStatus"] == "In Stock" and p["referenceCommodity"] == "Rice"

    assert [x["name"] for x in client.get("/api/products", headers=h).json()] == ["Rice"]
    r = client.put(f"/api/products/{p['id']}", headers=h, json={"reorderLevel": 30, "sellingPrice": 55})
    assert r.status_code == 200 and r.json()["stockStatus"] == "Low Stock" and r.json()["sellingPrice"] == 55
    assert client.delete(f"/api/products/{p['id']}", headers=h).status_code == 204
    assert client.get("/api/products", headers=h).json() == []


def test_stock_status_labels(client, register_user, create_shop, create_product):
    h = register_user()
    create_shop(h)
    assert create_product(h, "A", openingStock=0)["stockStatus"] == "Out of Stock"
    assert create_product(h, "B", openingStock=10, reorderLevel=10)["stockStatus"] == "Low Stock"
    assert create_product(h, "C", openingStock=11, reorderLevel=10)["stockStatus"] == "In Stock"


def test_search_and_category_filter(client, register_user, create_shop, create_product):
    h = register_user()
    create_shop(h)
    create_product(h, "Basmati Rice", category="Grains")
    create_product(h, "Sugar", category="Staples")
    assert [p["name"] for p in client.get("/api/products?q=rice", headers=h).json()] == ["Basmati Rice"]
    assert [p["name"] for p in client.get("/api/products?category=Staples", headers=h).json()] == ["Sugar"]


@pytest.mark.parametrize("body, code", [
    ({"name": ""}, 422),
    ({"name": "X", "unit": "bag"}, 422),
    ({"name": "X", "openingStock": -1}, 422),
    ({"name": "X", "sellingPrice": 0}, 422),
    ({"name": "X", "referenceCommodity": "Unobtainium"}, 422),
])
def test_product_validation(client, register_user, create_shop, body, code):
    h = register_user()
    create_shop(h)
    assert client.post("/api/products", headers=h, json=body).status_code == code


def test_duplicate_product_name_409(client, register_user, create_shop, create_product):
    h = register_user()
    create_shop(h)
    create_product(h, "Rice")
    r = client.post("/api/products", headers=h, json={"name": " rice "})
    assert r.status_code == 409


def test_delete_product_with_purchases_409(client, shop_with_data):
    d = shop_with_data
    client.post("/api/purchases", headers=d["headers"], json={
        "productId": d["product"]["id"], "supplierId": d["supplier"]["id"], "quantity": 5, "unitPrice": 40, "purchaseDate": "2020-01-01"})
    r = client.delete(f"/api/products/{d['product']['id']}", headers=d["headers"])
    assert r.status_code == 409 and r.json()["detail"] == "Product has purchases or sales and cannot be deleted"


def test_supplier_crud_with_products(client, register_user, create_shop, create_product):
    h = register_user()
    create_shop(h)
    a, b = create_product(h, "Rice"), create_product(h, "Sugar")
    r = client.post("/api/suppliers", headers=h, json={"name": "ABC", "contact": "123", "productIds": [a["id"], b["id"]]})
    assert r.status_code == 201 and sorted(r.json()["productNames"]) == ["Rice", "Sugar"]
    sid = r.json()["id"]
    r = client.put(f"/api/suppliers/{sid}", headers=h, json={"name": "ABC Traders", "productIds": [a["id"]]})
    assert r.json()["productIds"] == [a["id"]] and r.json()["name"] == "ABC Traders"
    assert client.get("/api/suppliers", headers=h).json()[0]["productNames"] == ["Rice"]
    assert client.delete(f"/api/suppliers/{sid}", headers=h).status_code == 204


def test_supplier_unknown_product_422_and_duplicate_409(client, register_user, create_shop, create_supplier):
    h = register_user()
    create_shop(h)
    assert client.post("/api/suppliers", headers=h, json={"name": "X", "productIds": [999]}).status_code == 422
    create_supplier(h, "ABC")
    assert client.post("/api/suppliers", headers=h, json={"name": "abc"}).status_code == 409


def test_delete_supplier_with_purchases_409(client, shop_with_data):
    d = shop_with_data
    client.post("/api/purchases", headers=d["headers"], json={
        "productId": d["product"]["id"], "supplierId": d["supplier"]["id"], "quantity": 5, "unitPrice": 40, "purchaseDate": "2020-01-01"})
    assert client.delete(f"/api/suppliers/{d['supplier']['id']}", headers=d["headers"]).status_code == 409


def test_activity_logged_on_create(client, register_user, create_shop, create_product, create_supplier):
    h = register_user()
    create_shop(h)
    create_product(h, "Rice")
    create_supplier(h, "ABC")
    texts = [a["text"] for a in client.get("/api/activity?limit=5", headers=h).json()]
    assert "Supplier added - ABC" in texts and "Product added - Rice (kg)" in texts
