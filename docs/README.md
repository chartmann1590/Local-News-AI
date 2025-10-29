# Local News & Weather — Documentation

This folder contains the full documentation for the Local News & Weather app. For a quick start, see the root README.

## Features

- Automatic location detection (city/state, coords, timezone) with manual override.
- Scheduled local news harvesting (morning, noon, evening; configurable) with Ollama AI rewrites and source citation.
- Weather forecast and AI weather report with daily icons and an embedded radar view.
- Smart duplicate removal (by normalized title and image) run automatically after each harvest, plus a manual action in Settings.
- Progress status with live rewrite details; only one rewrite runs at a time.
- Modern UI: React + Tailwind (Vite build) served by FastAPI.

## Architecture Overview

- Backend: FastAPI with APScheduler for cron-like jobs, SQLite for persistence.
- Frontend: React app compiled by Vite; static assets served by the backend.
- AI: Uses a local Ollama server (e.g., `http://host.docker.internal:11434`).
- Weather: Open‑Meteo geocoding + forecast. Radar provided by Windy embed.

## Configuration

Environment variables (via `docker-compose.yml` or container env):

- `LOCATION_NAME`: Optional explicit location (otherwise auto‑detected).
- `MIN_ARTICLES_PER_RUN`: Minimum to create per run (default 10).
- `TZ`: Fallback timezone (auto‑detected from resolved location when available).
- `SCHEDULE_MORNING`, `SCHEDULE_NOON`, `SCHEDULE_EVENING`: `HH:MM` in local TZ.
- `OLLAMA_BASE_URL`: Base URL for Ollama (default `http://host.docker.internal:11434`).
- `FEED_EXTRA_URLS`: Optional comma‑separated RSS URLs to include.
- `LOG_LEVEL`: Logging level (e.g., `INFO`, `DEBUG`).

Data storage:

- SQLite DB is stored at `/data/app.db` (volume‑mounted by Compose to `./data`).

## UI Guide

- Header: Run Now (manual harvest) and Settings.
- Weather (left column):
  - AI weather report; daily icons and high/low temps for 5 days.
  - Embedded radar centered on the detected/selected location.
- News (right column):
  - Latest articles with AI rewrites, playful bylines, and source links.
  - Pagination: 10 items per page with Prev/Next.
- Status bar: shows current phase and rewrite progress; displays the current article being rewritten.
- Settings:
  - Ollama base URL and model, connectivity test.
  - Weather units (F/C) — triggers a fresh fetch/report when changed.
  - Location — manual set or auto‑detect.
  - Maintenance — Deduplicate by Title; Rewrite Missing (with optional limit).

## Operations

- Start: `docker compose up --build -d`
- Logs: `docker compose logs -f`
- Rebuild image: `docker compose build`
- Manual harvest: UI Run Now or `POST /api/run-now`
- Maintenance: from Settings, or via API (see below).

## API Reference (Summary)

See `docs/api.md` for endpoint details and parameters.

- `GET /api/status` — run status, progress, and next runs.
- `GET /api/articles?page=1&limit=10` — paginated articles.
- `POST /api/run-now` — run a harvest immediately.
- `GET /api/weather` — latest weather + forecast.
- `GET /api/config` — basic app config (location, min article count, timezone).
- `GET /api/settings` / `POST /api/settings` — Ollama + unit settings.
- `POST /api/location` / `POST /api/location/auto` — set or auto‑detect location.
- `POST /api/weather/refresh` — refresh weather + AI report.
- `POST /api/maintenance/dedup` — remove duplicates.
- `POST /api/maintenance/rewrite-missing` — re‑queue missing/fallback rewrites.

## Troubleshooting

- `LOCATION_NAME` not set warning: harmless; the app auto‑detects location if not provided.
- Compose `version` key deprecation warning: remove the key to silence it (not functionally required).
- Ollama connectivity: test via Settings → Ollama → Test; ensure base URL is reachable from inside the container (use `host.docker.internal`).

