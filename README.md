Local News & Weather (Dockerized)

Fast, configurable local news + weather with on‑device AI rewrites via Ollama.

Highlights
- Auto‑detects location (with manual override in Settings).
- Schedules three harvests per day (configurable) and rewrites news with Ollama.
- Weather report with forecast icons and an embedded radar.
- Smart deduplication cleans up lookalike stories automatically after each run.
- Clean UI with pagination (10 per page), live progress, and one‑at‑a‑time rewrites.

Quick Start
1) Requirements
   - Docker and Docker Compose
   - Ollama running on the host (`http://localhost:11434`) with an available model (e.g., `llama3.2`)

2) Optional config — edit env vars in `docker-compose.yml`
   - `LOCATION_NAME` — force a specific city/state; leave unset for auto‑detect
   - `MIN_ARTICLES_PER_RUN` — default `10`
   - `TZ` — fallback timezone (location detection provides the real TZ)
   - `SCHEDULE_MORNING`, `SCHEDULE_NOON`, `SCHEDULE_EVENING` — `HH:MM` in local TZ
   - `OLLAMA_BASE_URL` — default `http://host.docker.internal:11434`

3) Run
   - `docker compose up --build -d`
   - Open http://localhost:18080

Usage
- Click Run Now in the header for a manual harvest.
- Use Settings to configure Ollama URL/model, units (°F/°C), location, and maintenance tasks (dedup / rewrite missing).
- Weather (left) shows the AI report, 5‑day icons, and radar; News (right) shows the latest articles with pagination.

Docs
- Full docs: `docs/README.md`
- API reference: `docs/api.md`

Notes
- Data is stored in `./data/app.db` (SQLite) and volume‑mounted by Compose.
- The app schedules jobs internally with APScheduler.
- From Linux containers, `host.docker.internal` may resolve correctly; otherwise set `OLLAMA_BASE_URL` to your host IP (e.g., `http://172.17.0.1:11434`).

Security/Usage
- Sources are free RSS/HTML; no paid APIs included.
- Rewrites preserve facts/attribution. Always verify at the source link.

