FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    AIR_AGENTS_DATABASE_PATH=/app/data/air_agents.db

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data && chown -R app:app /app

USER app
EXPOSE 8000

CMD ["uvicorn", "air_agents_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
