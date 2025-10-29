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

## TTS Connectivity

- Ensure TTS is enabled in Settings and that the base URL is reachable from the app container (default `http://tts:5500`).
- Click Refresh Voices to verify connectivity; if it fails, check `docker compose logs -f tts`.
- If exposing TTS outside Docker, set `TTS_BASE_URL` or the in-app base URL accordingly.

## No Audio / Playback Issues

- Browser autoplay policies may block audio until user interaction; click Play again after interacting with the page.
- If preview works but article/weather audio fails, confirm articles have `ai_body` and a weather report exists.
- Check the network tab for `/api/tts/...` requests; 400 indicates TTS disabled, 502 indicates the TTS server is unreachable.
