# --- Stage 1: build the frontend ---
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# vite.config.ts outDir is ../app/static, so the build already lands at /app/static

# --- Stage 2: runtime ---
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY agents ./agents
COPY --from=frontend-build /app/static ./app/static

RUN mkdir -p /app/data/logs /app/data/ssh_keys

EXPOSE 8000

COPY deploy/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
