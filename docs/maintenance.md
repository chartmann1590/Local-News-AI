# Maintenance & Data

## Duplicate Cleanup

- The app automatically runs deduplication after each harvest. Duplicates are grouped by normalized title and, in a second pass, by normalized image URL. The best record is kept; others are deleted.
- You can also run it manually from Settings → Maintenance → Deduplicate by Title or call the API: `POST /api/maintenance/dedup`.

## Rewrite Missing

- Re‑queue AI rewrites for items with missing AI text or fallback content from Settings → Maintenance → Rewrite Missing (with optional limit) or `POST /api/maintenance/rewrite-missing?limit=50`.

## Database

- SQLite file lives at `./data/app.db` (host) → `/data/app.db` (container). Back it up by copying while the app is stopped.
- You can inspect contents with any SQLite viewer.

## Logs

- Container logs: `docker compose logs -f`
- Consider setting `LOG_LEVEL=DEBUG` temporarily when diagnosing.

