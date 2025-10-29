Local News & Weather (Dockerized)
================================

Fast local news + weather with on‑device AI rewrites (Ollama). Clean UI. Zero external paid APIs.

Features
- Automatic location detection with manual override in Settings
- 3×/day scheduled harvesting (configurable) with Ollama article rewrites
- Weather report with daily icons and an embedded radar
- Smart deduplication (by normalized title and image) after each run
- Pagination (10/page), live progress, “Now rewriting” details, single-threaded rewrites
- Optional offline Text-to-Speech (Piper via OpenTTS) for articles and weather
- Per-article AI comments: click Comments under any article to chat with the AI using the article’s content; replies use the article’s generated author name

Quick Start
1) Requirements
   - Docker and Docker Compose
   - Ollama on the host (`http://localhost:11434`) with a model available (e.g., `llama3.2`)

2) Run
   - Build + start: `docker compose up --build -d`
   - App: http://localhost:18080
   - TTS service (internal): http://news-ai-tts:5500 (exposed to app only)

3) Configure (optional)
   - Edit env vars in `docker-compose.yml` (see docs below)
   - Or use the in‑app Settings for Ollama URL/model, units (°F/°C), and location

Using the App
- Header → Run Now to trigger an immediate harvest
- Weather (left): AI report, 5-day icons, radar
- News (right): latest local articles with rewrites, bylines, and pagination
- Article Chat: expand Comments on any article to ask questions about it; the AI replies using only that article’s details
- Settings: Ollama settings, units, location, Maintenance (Deduplicate / Rewrite Missing)
  - Text-to-Speech: enable, set base URL (default `http://tts:5500`), choose a voice, and preview

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
- Chat rate limiting: env `CHAT_RATE_LIMIT_PER_MIN` controls per-IP per-article limit (default 10)

Text‑to‑Speech (TTS)
- Self‑hosted, free, offline TTS using OpenTTS (Piper engine) in its own container.
- Multiple natural voices; voices are cached under `./data/tts` on first use.
- Enable under Settings → Text‑to‑Speech. Default TTS URL is `http://tts:5500` (Docker service name).
- The player shows play/pause, a seek slider, elapsed/total, and remaining time.

Security
- Sources are free RSS/HTML only; no paid APIs included
- AI rewrites preserve attribution — verify facts at the source link
