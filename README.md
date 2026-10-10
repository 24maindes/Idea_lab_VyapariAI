# VyapariAI - AI-powered price and purchase advisor for local shopkeepers

VyapariAI is a web application built at the **IDEA Lab, Ramdeobaba University** (Computer Science Engineering, 2024-28). Small shopkeepers usually buy and price goods from
experience, so they often overpay suppliers, stock too much or too little, and lose margin. VyapariAI lets a shopkeeper record purchases, sales and stock, compares purchase prices
with market prices, forecasts the market price for the next days, warns about abnormal prices, recommends **what to buy and in what quantity**, suggests a **selling price range**
and explains everything in **English, Hindi or Marathi** (typed or spoken) through an AI advisor that only talks about the shop's own data.

## Features (mapped to the synopsis)
| Synopsis objective | Where in the app | Main code |
|---|---|---|
| Login and shop setup | Login, Signup, Shop Setup, Settings | `routers/auth.py`, `routers/shop.py` |
| Capture products, suppliers, purchases, sales, stock | Products, Suppliers, Purchases, Sales, Inventory, CSV import | `routers/products.py` ... `services/importer.py` |
| Fair-price analysis against reference market prices | Pricing page, live fair-price tag on Purchases | `services/fair_price.py` |
| ML price prediction | Forecast page | `ml/features.py`, `ml/train_forecast.py`, `services/forecast_service.py` |
| Price anomaly detection | Alerts page, warning after saving a purchase | `ml/anomaly.py`, `services/anomaly_service.py` |
| Purchase decision engine (Buy Now / Buy Limited / Wait + quantity) | Recommendations, Dashboard | `services/decision_engine.py` |
| Selling price range | Recommendations (what to sell at) | `services/pricing_engine.py` |
| Simplified supplier comparison | Suppliers > Compare | `services/supplier_stats.py` |
| Dashboard | Dashboard | `routers/dashboard.py` |
| RAG AI advisor, text and voice, English / Hindi / Marathi | AI Advisor page and the round button | `services/advisor/*`, `routers/advisor.py` |

## Architecture
```mermaid
flowchart LR
  U[Shopkeeper browser<br/>React + Tailwind] -->|JSON over HTTPS + login token| API[FastAPI backend]
  API --> DB[(SQLite / PostgreSQL)]
  REF[Reference prices<br/>WPI-based CSV] --> DB
  API --> SVC[Services: fair price, anomaly,<br/>decision, pricing, supplier stats]
  SVC --> ML[ML models<br/>joblib files]
  API --> ADV[Advisor: entities, retrieval,<br/>prompt, grounding check]
  ADV -->|context + question| LLM[Gemini API]
  ADV -.fallback.-> TPL[Offline answer templates]
  TRAIN[train_forecast.py<br/>evaluate_anomaly.py] --> ML
```

## Tech stack
| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS 3, recharts, lucide-react, react-router-dom |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, JWT (python-jose), passlib bcrypt |
| Database | SQLite (development), PostgreSQL (deployment), selected by `DATABASE_URL` |
| ML | pandas, numpy, scikit-learn, XGBoost, statsmodels, joblib, matplotlib, seaborn |
| AI | Google Gemini through the `google-genai` SDK (key and model name from the environment) |
| Tests | pytest, FastAPI TestClient, httpx |

## Folder structure
```
VyapariAI/
├── backend/
│   ├── app/
│   │   ├── main.py  settings.py  startup.py  database.py  models.py  schemas.py  deps.py  auth.py
│   │   ├── routers/    auth shop products suppliers purchases sales inventory activity reference analysis
│   │   │               forecast anomalies recommendations dashboard imports advisor
│   │   ├── services/   config.py (all business thresholds)  fair_price decision_engine pricing_engine ...
│   │   │   └── advisor/  entities retrieval prompt gemini_client grounding fallback
│   │   └── ml/         build_reference load_reference seed_demo features train_forecast anomaly ...
│   ├── tests/          pytest suite (450 tests)
│   ├── scripts/        e2e_flow.py advisor_eval.py make_eval_docs.py make_api_overview.py
│   ├── data/           raw/ (datasets, not in git)  reference_prices.csv  demand_profile.json
│   └── models_store/   trained forecast models (.joblib)
├── frontend/           src/{pages,components,context,api,hooks,advisor,utils}
├── docs/               data_sources.md  user_manual.md  api_overview.md  bugs.md  eval/  report/  figures/
└── docker-compose.yml
```

## Prerequisites
Python 3.11 or newer, Node.js 20 or newer, Git. (Optional: PostgreSQL 14+ or Docker.)

## Setup (about 15 minutes)

### 1. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows         (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # Mac/Linux: cp .env.example .env     then edit .env
```
Put the four dataset files in `backend/data/raw/` (WPI, wholesale customers, supermarket, online sales; see `docs/data_sources.md`). Then:
```bash
python -m app.ml.build_reference        # cleans the WPI file -> data/reference_prices.csv
python -m app.ml.build_demand_profile   # sales statistics -> data/demand_profile.json
python -m app.ml.load_reference         # loads the CSV into the database (safe to repeat)
python -m app.ml.seed_demo              # demo shop with 12 months of data
python -m app.ml.train_forecast         # trains and compares the forecast models (about 4 minutes)
python -m uvicorn app.main:app --reload
```
The API is now at http://127.0.0.1:8000 (interactive docs at `/docs`).

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173.

### 3. Demo login
`demo@vyapariai.com` / `demo1234` (shop "Sharma General Store", Nagpur, 10 products, 4 suppliers, 12 months of purchases and sales, 25 injected price anomalies).

### 4. AI advisor key (optional)
Get a key from Google AI Studio and set `GEMINI_API_KEY` and `GEMINI_MODEL` in `backend/.env`. Without them the advisor still works with short offline answers.

## Running the tests
```bash
cd backend
python -m pytest -q                                   # whole suite, SQLite in memory
TEST_DATABASE_URL=postgresql+psycopg2://user:pass@localhost/test_db python -m pytest -q     # on PostgreSQL (empty test database!)
pip install pytest-cov && python -m pytest --cov=app --cov-report=term-missing              # coverage
python scripts/e2e_flow.py                            # walks through the whole product on a RUNNING server
```

## Docker
```bash
docker compose up --build                 # PostgreSQL + backend + frontend
docker compose exec backend python -m app.ml.seed_demo
```
Open http://localhost:8080. Deployment on Render / Vercel: see `docs/DEPLOY.md`.

## ML evaluation summary
Everything is generated from real result files: `docs/eval/summary_tables.md`, `docs/eval/model_card.md`, `docs/eval/performance.md`, `docs/eval/advisor_tests.md`,
and charts in `docs/figures/`. Forecasts are evaluated chronologically with a rolling origin (7 days ahead, every 7 days of the test period); anomaly detection
is evaluated on labelled injected anomalies (precision, recall, F1). See the model card for details and limits.

## Known limitations
- Market prices are **partly synthetic**: the WPI is an index (converted to rupees with assumed anchor prices) that ends in 2017 and was date-shifted; recent months and Paneer are generated.
- The demo shop's data is synthetic. Accuracy on a real shop will be different and must be re-measured.
- Forecasts are estimates, 7 to 14 days only; no demand forecasting, no WhatsApp alerts, no mobile app, no invoice scanning, no live market API (out of scope in the synopsis).
- Voice input needs Chrome or Edge and a microphone; the Hindi/Marathi voice for reading answers depends on the voices installed on the device.
- Rate limits, caches and the retrain job status live in memory of one server process.
- Changing a database model needs a new database (no migrations were set up).

## Troubleshooting
| Problem | Fix |
|---|---|
| Browser shows a CORS error | Put the frontend address in `CORS_ORIGINS` (no trailing slash) and restart the backend. |
| Advisor says "Basic answer (AI is offline)" | `GEMINI_API_KEY` or `GEMINI_MODEL` is missing or wrong in `backend/.env`; restart the backend. Check the server log line "Advisor fallback used". |
| `Address already in use` / port 8000 busy | Another server is running. Stop it or use `--port 8001` and set `VITE_API_URL=http://127.0.0.1:8001` in `frontend/.env`. |
| Forecast page says "No trained forecast model" | Run `python -m app.ml.train_forecast` (or the Retrain models button). |
| `/api/reference/commodities` is empty / "No reference prices" | Run `build_reference`, then `load_reference` (the server also loads the CSV at start-up when the table is empty). |
| `sqlite3.OperationalError: no such column/table` after pulling new code | The model changed. Delete `backend/vyapariai.db` and run `load_reference` and `seed_demo` again. |
| Microphone button missing or "Voice works in Chrome or Edge" | Use Chrome/Edge, open the site on `localhost` or `https`, allow the microphone in the address bar. |
| No voice for reading Hindi/Marathi aloud | Install the language voice in your operating system settings (Windows: Speech > Add voices). |
| Login works but pages show "Session expired" | The `SECRET_KEY` changed or the token is older than 24 hours: log in again. |
| `ModuleNotFoundError: app` when running a script | Run it from the `backend` folder, with the virtual environment active. |

## Team
Madhulika Deshpande (A7_B3_34), Sharvari Mainde (A7_B4_55), Oshin Dhabale (A7_B1_09). Guide: Prof. Poonam Meghare. Ramdeobaba University, Computer Science Engineering, IDEA Lab, session 2024-28.

## Licence and data notes
Source code: [TODO: choose a licence, e.g. MIT, or "all rights reserved - academic project"]. Datasets keep their own licences (see `docs/data_sources.md`; fill in the licence column). Google Gemini is used under Google's terms.
