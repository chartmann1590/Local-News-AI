# Configuration

Configuration can be done via Docker Compose environment variables and via the in‑app Settings page for AI and units.

## Environment Variables

Set these in `docker-compose.yml` (or an `.env` file referenced by Compose):

- `LOCATION_NAME` — Optional explicit location (e.g., `Schenectady, NY`). Leave unset for auto‑detection.
- `MIN_ARTICLES_PER_RUN` — Minimum new articles to create per run (default `10`).
- `TZ` — Fallback timezone (the app prefers resolved location timezone).
- `SCHEDULE_MORNING`, `SCHEDULE_NOON`, `SCHEDULE_EVENING` — `HH:MM` in local TZ.
- `OLLAMA_BASE_URL` — Base URL for Ollama (default `http://host.docker.internal:11434`).
- `FEED_EXTRA_URLS` — Comma‑separated RSS feed URLs to include in harvesting.
- `LOG_LEVEL` — Logging level (`INFO`, `DEBUG`, etc.).

Data volume:

- The SQLite database is stored at `/data/app.db` inside the container and mapped to `./data/app.db` on the host.

## In‑App Settings

- Ollama base URL — normalized for in‑container access (e.g., converts `localhost` to `host.docker.internal`).
- Ollama model — the model name/tag served by Ollama.
- Units — °F or °C; changing this triggers a fresh forecast fetch + AI weather report.
- Location — manual set or auto‑detect; either triggers a fresh weather refresh.

