# Deploying VyapariAI

Two parts are deployed separately: the **backend** (FastAPI + PostgreSQL) and the **frontend** (static files).
Typical free setup: backend + database on **Render** (or Railway), frontend on **Vercel** (or Netlify).

> The Docker files and this guide could not be run inside the development sandbox (no Docker there). The backend was tested
> on a real PostgreSQL 16 server (all tests pass), but follow the steps below carefully and check the "Smoke test" at the end.

## 1. Environment variables (backend)

| Variable | Value | Notes |
|---|---|---|
| `ENV` | `production` | turns on the safety checks (the server refuses to start with unsafe settings) |
| `DATABASE_URL` | from your PostgreSQL service | `postgres://...` is accepted and fixed automatically |
| `SECRET_KEY` | 32+ random characters | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CORS_ORIGINS` | your frontend address, e.g. `https://vyapariai.vercel.app` | no trailing slash needed; **not** localhost, **not** `*` |
| `GEMINI_API_KEY` | key from https://aistudio.google.com | optional: without it the advisor gives basic offline answers |
| `GEMINI_MODEL` | a current Gemini Flash model name | check the list in Google AI Studio |

Frontend (build time): `VITE_API_URL` = the public address of the backend, e.g. `https://vyapariai-api.onrender.com`.

## 2. Backend on Render
1. New **PostgreSQL** database (free plan). Copy its *Internal Database URL*.
2. New **Web Service** from your GitHub repo, **Root directory** `backend`, **Runtime** Python 3.
   - Build command: `pip install -r requirements.txt psycopg2-binary uvicorn[standard]`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add the environment variables from the table above.
4. The files `data/reference_prices.csv` and `models_store/*.joblib` must be committed to git (they are small). On the first start the
   server fills the empty `reference_prices` table from the CSV by itself.
5. Optional demo data: open the Render shell and run `python -m app.ml.seed_demo` (needs the reference prices, which step 4 created).

## 3. Frontend on Vercel
1. Import the repo, **Root directory** `frontend`, framework **Vite**.
2. Environment variable `VITE_API_URL` = your backend address. Build command `npm run build`, output `dist`.
3. Add a rewrite so page refreshes work: file `frontend/vercel.json` with
   `{ "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }` (already included).
4. Put the Vercel address into the backend's `CORS_ORIGINS` and redeploy the backend.

## 4. Everything locally with Docker
```
docker compose up --build        # PostgreSQL + backend + frontend
docker compose exec backend python -m app.ml.seed_demo
```
Open http://localhost:8080 and log in with `demo@vyapariai.com` / `demo1234`.

## 5. Smoke test after deploying
1. `GET <backend>/api/health` returns `{"status":"ok"}`.
2. `<backend>/docs` opens; `GET /api/reference/commodities` (with a token) lists 15 commodities.
3. Open the frontend, sign up, create a shop, add a product, record a purchase. Reload the page: you must still be logged in.
4. Ask the advisor a question: with a key you get an AI answer; without it the answer ends with "Basic answer (AI is offline)".

## 6. Known limits
- Free hosting sleeps after inactivity: the first request can take 30-60 seconds.
- Rate limiting, caches and the retrain job status live in the memory of ONE server process. Run a single instance (or add Redis later).
- Forecast models are files (`models_store/`). Retraining on a hosting service with a read-only or temporary disk is lost on restart: retrain locally and commit the files.
- No e-mail password reset, no refresh tokens (a login lasts 24 hours).
