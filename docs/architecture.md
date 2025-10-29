# Architecture

## Components

- Backend: FastAPI app
  - Scheduling: APScheduler (cron‑like jobs)
  - Database: SQLite via SQLAlchemy
  - Templates/Static: serves built React assets
  - Modules:
    - `app/main.py` — API routes and server setup
    - `app/scheduler.py` — scheduled harvest, rewrite loop, weather generation
    - `app/news_fetcher.py` — feed discovery and article scraping/normalization
    - `app/maintenance.py` — dedup and rewrite‑missing helpers
    - `app/weather.py` — geocoding and forecast fetch
    - `app/ai.py` — Ollama helpers (rewrite/generate)
    - `app/progress.py` — in‑memory progress tracker for UI

- Frontend: React + Vite + Tailwind
  - `web/src/ui/App.jsx` — main UI
  - Built to `/app/app/static` in the image for FastAPI to serve

## Data Flow (Harvest)

1. Resolve location + timezone (`app/geo.py`).
2. Gather RSS candidates (Bing + Google + extra feeds) → normalized publisher URLs.
3. Fetch article content and create new `Article` rows (min count respected).
4. Rewrite each article with Ollama (single‑threaded, retried), fallback to source on failure.
5. Deduplicate articles (title + image).
6. Refresh forecast + generate AI weather report.

## Concurrency

- A global rewrite lock ensures only one rewrite routine runs at a time (scheduler vs. maintenance).
- Progress includes `current_title/url` to show the active rewrite in the UI.

