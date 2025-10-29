# API Reference

This document lists the primary API endpoints exposed by the app.

All endpoints are served by the FastAPI backend at the same host/port as the UI.

## Status

- GET `/api/status`
  - Returns the current run status and progress.
  - Response fields: `running`, `phase`, `detail`, `total`, `completed`, `started_at`, `finished_at`, `error`, `next_runs`, `current_id`, `current_title`, `current_url`.

## Articles

- GET `/api/articles?page=1&limit=10`
  - Returns paginated articles.
  - Query params: `page` (default 1), `limit` (default 10, max 100).
  - Response: `{ items, page, limit, total, pages }` where each item includes:
    - `id`, `title`, `source`, `source_url`, `image_url`, `published_at`, `fetched_at`, `ai_model`, `ai_body`, `rewrite_note`, `byline` (present for non‑fallback AI articles).

## Harvest & Jobs

- POST `/api/run-now`
  - Triggers an immediate harvest (fetch + rewrite + weather).
  - Returns `{ status: "ok" }` or error JSON.

## Weather

- GET `/api/weather`
  - Latest weather report + daily forecast and coordinates.
  - Response: `{ location, timezone, latitude, longitude, report, forecast, updated_at, report_note }`.
- POST `/api/weather/refresh`
  - Refreshes forecast and regenerates the AI weather report in the background.
  - Returns `{ status: "queued" }`.

## Configuration & Settings

- GET `/api/config`
  - Returns minimal configuration info: `{ location, timezone, min_articles }`.
- GET `/api/settings`
  - Returns `{ ollama_base_url, ollama_model, temp_unit }`.
- POST `/api/settings`
  - Body fields (all optional): `ollama_base_url`, `ollama_model`, `temp_unit` (`F` or `C`).
  - Changing `temp_unit` triggers a weather refresh + AI report.

## Location

- POST `/api/location`
  - Body: `{ location: "City, State or ZIP" }`.
  - Sets the active location and triggers a weather refresh in the background.
- POST `/api/location/auto`
  - Attempts to auto‑detect location (IP geolocation). Triggers weather refresh.

## Maintenance

- POST `/api/maintenance/dedup`
  - Removes duplicate `Article` rows grouped by normalized title and (in a second pass) by normalized image URL.
  - Returns `{ status: "ok", deleted, kept_groups }`.
- POST `/api/maintenance/rewrite-missing?limit=50`
  - Re‑queues rewrites for articles with missing AI text or fallback AI.
  - Returns `{ status: "queued" }` (runs in background).

## Ollama Utilities

- POST `/api/ollama/test`
  - Body: `{ base_url }` — attempts to connect and list models.
  - Returns `{ ok, models?, error? }`.
- GET `/api/ollama/models?base_url=...`
  - Returns `{ models }` or `{ error }`.

## Health

- GET `/health`
  - Returns `{ ok: true, time: "..." }`.

