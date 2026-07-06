# BRAHL Web — production demo image
FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY qoa_web/api/requirements.txt /app/qoa_web/api/requirements.txt
COPY f/requirements.txt /app/f/requirements.txt

RUN pip install --no-cache-dir -r qoa_web/api/requirements.txt \
    && pip install --no-cache-dir -r f/requirements.txt

COPY . /app

RUN cp qoa_web/data/projects.seed.json qoa_web/data/projects.json 2>/dev/null || true \
    && echo '[]' > qoa_web/data/waitlist.json 2>/dev/null || true

ENV PYTHONUNBUFFERED=1
ENV FOXYIZ_HEADLESS=true
ENV APP_BASE_URL=http://127.0.0.1:8765

EXPOSE 8765

WORKDIR /app/qoa_web/api
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765"]
