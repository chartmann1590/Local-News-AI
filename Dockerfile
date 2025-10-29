FROM node:20-alpine AS webbuild
WORKDIR /web
COPY web/package.json /web/package.json
COPY web/package-lock.json /web/package-lock.json
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY web /web
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       curl \
       ca-certificates \
       libxml2 \
       libxml2-dev \
       libxslt1.1 \
       libxslt1-dev \
       libjpeg62-turbo \
       tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
# Copy built React app into static directory
COPY --from=webbuild /web/dist /app/app/static

# SQLite data path
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

ENV TZ=${TZ:-America/New_York}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
