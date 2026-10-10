# VyapariAI backend (FastAPI). Build:  docker build -t vyapariai-backend ./backend
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# libgomp is needed by XGBoost / scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary uvicorn[standard]

COPY app ./app
COPY data/reference_prices.csv ./data/reference_prices.csv
COPY data/demand_profile.json ./data/demand_profile.json
COPY models_store ./models_store

EXPOSE 8000
# $PORT is set by hosting services such as Render; 8000 otherwise
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
