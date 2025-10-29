Local News & Weather (Dockerized)
================================

Fast local news + weather with on‑device AI rewrites (Ollama). Clean UI. Zero external paid APIs.

Features
- Automatic location detection with manual override in Settings
- 3×/day scheduled harvesting (configurable) with Ollama article rewrites
- Weather report with daily icons and an embedded radar
- Smart deduplication (by normalized title and image) after each run
- Pagination (10/page), live progress, “Now rewriting” details, single‑threaded rewrites

Quick Start
1) Requirements
   - Docker and Docker Compose
   - Ollama on the host (`http://localhost:11434`) with a model available (e.g., `llama3.2`)

2) Run
   - Build + start: `docker compose up --build -d`
   - App: http://localhost:18080

3) Configure (optional)
   - Edit env vars in `docker-compose.yml` (see docs below)
   - Or use the in‑app Settings for Ollama URL/model, units (°F/°C), and location

Using the App
- Header → Run Now to trigger an immediate harvest
- Weather (left): AI report, 5‑day icons, radar
- News (right): latest local articles with rewrites, bylines, and pagination
- Settings: Ollama settings, units, location, Maintenance (Deduplicate / Rewrite Missing)

Documentation
- Overview & Setup: docs/README.md
- Configuration: docs/configuration.md
- Setup & Run: docs/setup.md
- Maintenance & Data: docs/maintenance.md
- Customization: docs/customization.md
- Architecture: docs/architecture.md
- Deployment tips: docs/deployment.md
- Troubleshooting: docs/troubleshooting.md
- API Reference: docs/api.md

Notes
- SQLite DB at `./data/app.db` (mounted volume in Compose)
- APScheduler handles internal schedules
- On Linux, if `host.docker.internal` is unavailable, set `OLLAMA_BASE_URL` to your host IP (e.g., `http://172.17.0.1:11434`)

Security
- Sources are free RSS/HTML only; no paid APIs included
- AI rewrites preserve attribution — verify facts at the source link
