# Troubleshooting

## Common Warnings

- `LOCATION_NAME` not set — harmless; the app auto‑detects location when unset.
- Compose `version` key deprecated — remove the `version:` key from `docker-compose.yml` to silence it.

## Ollama Connectivity

- Use Settings → Ollama → Test to verify connectivity and load models.
- Inside containers, `localhost` refers to the container. Prefer `http://host.docker.internal:11434` or your host IP.

## No Articles

- Verify network access from the container to RSS endpoints.
- Increase `MIN_ARTICLES_PER_RUN` or wait for more feed entries.
- Check logs: `docker compose logs -f` (look for `feeds_start`, `feed_ok`, `created_articles`).

## Duplicate Stories

- Dedup runs automatically post‑harvest. You can also run it from Settings → Maintenance.
- If duplicates persist, confirm titles differ (some publishers vary headlines).

## Encoding / Emoji

- If glyphs look odd in the UI, ensure your browser is set to UTF-8.

## Chat / Comments

- 429 Too Many Requests: you hit the per-IP per-article limit. Increase `CHAT_RATE_LIMIT_PER_MIN` or wait a minute.
- 502 ai_unavailable: the model call failed. Verify Ollama is reachable (Settings → Ollama → Test) and check app logs.
- Messages not saving: ensure the SQLite file is writable and `chat_messages` table exists (created automatically at startup).
- Clearing threads: use the Clear button in the UI, or call `DELETE /api/articles/{id}/chat`.

## TTS Connectivity

- Ensure TTS is enabled in Settings and that the base URL is reachable from the app container (default `http://tts:5500`).
- Click Refresh Voices to verify connectivity; if it fails, check `docker compose logs -f tts`.
- If exposing TTS outside Docker, set `TTS_BASE_URL` or the in-app base URL accordingly.

## No Audio / Playback Issues

- Browser autoplay policies may block audio until user interaction; click Play again after interacting with the page.
- If preview works but article/weather audio fails, confirm articles have `ai_body` and a weather report exists.
- Check the network tab for `/api/tts/...` requests; 400 indicates TTS disabled, 502 indicates the TTS server is unreachable.

## Theme toggle doesn’t change colors

- The UI uses compiled Tailwind with class-based dark mode. If the theme icon changes but colors don’t:
  - Hard refresh the page to clear cached CSS and service worker content.
  - Ensure the `<html>` element has the `dark` class when dark mode is active (Developer Tools → Elements).
  - Rebuild and recreate the app container to pick up CSS changes:
    - `docker compose build app && docker compose up -d --no-deps --force-recreate app`
  - If multiple clients are affected, consider bumping the cache name in `web/public/sw.js` and rebuilding to force a fresh cache.
