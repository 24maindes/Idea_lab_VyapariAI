# API overview

Generated from the running app by `python scripts/make_api_overview.py`. All JSON keys are camelCase; money is rupees per unit; dates are `YYYY-MM-DD`. Every endpoint marked **Yes** needs the header `Authorization: Bearer <token>` (get the token from `/api/auth/login`) and only ever returns the logged-in user's own shop data. Interactive documentation: `/docs`.

## Authentication

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| POST | `/api/auth/login` | Login | No |
| GET | `/api/auth/me` | Read Current User | Yes |
| PUT | `/api/auth/password` | Change the logged-in user's password. The OLD password must be right (verified with passlib) | Yes |
| POST | `/api/auth/signup` | Signup | No |

## Shop

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| GET | `/api/shop` | Read Shop | Yes |
| POST | `/api/shop` | One shop per user. A second POST is a 409 conflict (user_id is also UNIQUE in the database) | Yes |
| PUT | `/api/shop` | Update Shop | Yes |

## Products

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| GET | `/api/products` | List Products | Yes |
| POST | `/api/products` | Create Product | Yes |
| DELETE | `/api/products/{product_id}` | Delete Product | Yes |
| PUT | `/api/products/{product_id}` | Update Product | Yes |

## Suppliers

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| GET | `/api/suppliers` | List Suppliers | Yes |
| POST | `/api/suppliers` | Create Supplier | Yes |
| GET | `/api/suppliers/comparison` | Suppliers compared for ONE product: average price, stability, variance vs market, best value | Yes |
| DELETE | `/api/suppliers/{supplier_id}` | Delete Supplier | Yes |
| PUT | `/api/suppliers/{supplier_id}` | Update Supplier | Yes |
| GET | `/api/suppliers/{supplier_id}/prices` | Price history of one supplier for one product, plus the market (reference) price series for the same period | Yes |

## Purchases

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| GET | `/api/purchases` | List Purchases | Yes |
| POST | `/api/purchases` | Create Purchase | Yes |
| DELETE | `/api/purchases/{purchase_id}` | Delete Purchase | Yes |

## Sales

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| GET | `/api/sales` | List Sales | Yes |
| POST | `/api/sales` | Create Sale | Yes |
| GET | `/api/sales/summary` | Sales Summary | Yes |
| DELETE | `/api/sales/{sale_id}` | Delete Sale | Yes |

## Inventory

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| GET | `/api/inventory` | Inventory | Yes |

## Activity

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| GET | `/api/activity` | List Activity | Yes |

## Reference market prices

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| GET | `/api/reference/commodities` | One row per commodity with its date range and data source(s) | Yes |
| GET | `/api/reference/latest` | The most recent price row for one commodity | Yes |
| GET | `/api/reference/prices` | Daily prices, oldest first. If `limit` cuts the list we return the NEWEST `limit` rows | Yes |

## Fair-price analysis

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| GET | `/api/analysis/fair-price` | One row per product of the shop (used for the table and the product dropdown) | Yes |
| GET | `/api/analysis/fair-price/check` | Is this price fair? Used live by the purchase form. No market data is a normal answer, not an error | Yes |
| GET | `/api/analysis/fair-price/{product_id}` | Full detail for one product: stats, reference line, purchase dots, supplier comparison | Yes |

## Price forecasting

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| GET | `/api/forecast/models` | Model Table | Yes |
| POST | `/api/forecast/retrain` | Retrain | Yes |
| GET | `/api/forecast/retrain/status` | Retrain Status | Yes |
| GET | `/api/forecast/{product_id}` | Product Forecast | Yes |

## Alerts and anomaly detection

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| GET | `/api/alerts` | List Alerts | Yes |
| GET | `/api/alerts/count` | Count | Yes |
| PATCH | `/api/alerts/read-all` | Read All | Yes |
| POST | `/api/alerts/scan` | Scan | Yes |
| PATCH | `/api/alerts/{alert_id}/read` | Read One | Yes |

## Recommendations

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| GET | `/api/recommendations/purchase` | Purchase Recommendations | Yes |
| GET | `/api/recommendations/purchase/{product_id}` | Purchase Recommendation | Yes |
| GET | `/api/recommendations/selling-price` | Selling Prices | Yes |
| GET | `/api/recommendations/selling-price/{product_id}` | Selling Price | Yes |

## Dashboard

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| GET | `/api/dashboard/price-trend` | Price Trend | Yes |
| GET | `/api/dashboard/summary` | Summary | Yes |

## CSV import

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| GET | `/api/import/template/{kind}` | Template | Yes |
| POST | `/api/import/{kind}` | Import Csv | Yes |

## AI advisor

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| POST | `/api/advisor/chat` | Chat | Yes |
| DELETE | `/api/advisor/history` | Clear History | Yes |
| GET | `/api/advisor/history` | History | Yes |

## System

| Method | Path | Purpose | Auth required |
|---|---|---|---|
| GET | `/api/health` | Public (no login) - used to check that the server is alive | No |

Total: 53 operations.
