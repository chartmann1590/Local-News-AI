# Customization

This page lists common customization points and their code locations.

## Schedules

- Environment: `SCHEDULE_MORNING`, `SCHEDULE_NOON`, `SCHEDULE_EVENING` (see `docs/configuration.md`).
- Code: scheduler setup in `app/scheduler.py` (`start_scheduler`).

## Harvest Count

- Environment: `MIN_ARTICLES_PER_RUN`.

## Ollama Defaults

- In runtime, the app prefers the values saved via Settings. If not set, it uses `OLLAMA_BASE_URL` and `OLLAMA_MODEL` envs.
- Code: lookups in `app/scheduler.py` around `run_harvest_once`.

## Extra Feeds

- Environment: `FEED_EXTRA_URLS` (comma‑separated URLs added to the pool).
- Code: `app/news_fetcher.py` builds the candidate feed list from Bing, Google, and extra feeds; it normalizes URLs and removes tracking params.

## Deduplication

- Code: `app/maintenance.py` — grouping by normalized title (first pass) and normalized image URL (second pass). The `score()` prefers non‑fallback AI, then any AI, then newest timestamps, then longer raw content.

## UI Tweaks

- Web code lives under `web/src/ui`. The main app is `web/src/ui/App.jsx`.
- Build is handled via Vite during the Docker image build and served under `/static` by the backend.

