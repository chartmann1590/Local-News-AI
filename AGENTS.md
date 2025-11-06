# Repository Guidelines

## Project Structure & Module Organization
- `app/` — FastAPI backend (APScheduler jobs, TTS/AI clients). Templates in `app/templates/`, built web assets in `app/static/`.
- `web/` — React + Vite SPA (`web/src/ui/*.jsx`). Built during Docker image build.
- `flutter_app/` — Android client; optional APK built via Flutter.
- `tests/` — Playwright end-to-end tests (`tests/tests/*.spec.js`).
- `docs/` — Product and ops docs.
- `data/` — SQLite DB and generated files (mounted as `/data` in Docker).

## Build, Test, and Development Commands
- Run full stack (Docker): `docker compose up --build`
- Backend locally: `pip install -r requirements.txt` then `uvicorn app.main:app --reload`
- Web dev server: `cd web && npm ci && npm run dev` (optional; Docker builds static assets with `npm run build`)
- E2E tests: `cd tests && npm ci && npm test` (expects app at `http://localhost:18080`)
- Build APK (optional): `cd flutter_app && flutter build apk --release` (Docker copies to `app/static/news-ai-app.apk`)

## Coding Style & Naming Conventions
- Python: 4‑space indent, type hints where practical. Modules/functions `lower_snake_case` (e.g., `app/news_fetcher.py`), classes `PascalCase`.
- React: Functional components in `PascalCase` files (e.g., `web/src/ui/Broadcast.jsx`); props/state `camelCase`.
- Keep functions small, log meaningfully, and prefer explicit names over abbreviations.

## Testing Guidelines
- Framework: Playwright (`@playwright/test`). Specs live under `tests/tests/*.spec.js`.
- Run: `cd tests && npm ci && npm test` (or `npm run test:ui` for the UI runner).
- Cover core flows: loading articles, search/filter, bookmarks, sharing. Add new specs with clear names (e.g., `bookmarks.spec.js`).

## Commit & Pull Request Guidelines
- Use conventional-style prefixes seen in history: `feat:`, `fix:`, `docs:`, `chore:`. Write imperative subject lines.
- Example: `feat: add per-article AI chat endpoint`
- PRs: include a brief description, steps to verify, linked issues, and screenshots for UI changes. Ensure tests pass and docs updated when behavior changes.

## Security & Configuration Tips
- Copy `.env.example` to `.env`; never commit secrets. Common vars: `OPENWEATHERMAP_API_KEY`, `OLLAMA_BASE_URL`, `TTS_BASE_URL` (use `http://host.docker.internal:11434` in Docker).
- Data persists under `data/`; back it up before schema changes.
