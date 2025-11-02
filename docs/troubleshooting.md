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
- **Voice Persistence:** On Docker Desktop for Windows, TTS voices are persisted using WSL path format (`/mnt/h/...`) in the volume mount. If voices disappear after rebuild, verify the volume mount in `docker-compose.yml` is correct.
- **Voice Generation Timeout:** TTS voice generation has a 10-minute timeout to handle longer audio generation. If audio generation fails, check logs for timeout errors.

## No Audio / Playback Issues

- Browser autoplay policies may block audio until user interaction; click Play again after interacting with the page.
- If preview works but article/weather audio fails, confirm articles have `ai_body` and a weather report exists.
- Check the network tab for `/api/tts/...` requests; 400 indicates TTS disabled, 502 indicates the TTS server is unreachable.

## Location Issues

- **Location Changes on Rebuild:** Location should now persist between container rebuilds. If location keeps changing, ensure the database volume (`./data:/data`) is properly mounted.
- **Wrong Coordinates:** If radar shows incorrect location despite setting it correctly, the geocoding has been improved to better match city/state combinations. Try setting the location again with the full city and state name (e.g., "Schenectady, New York").
- **Radar Not Updating:** Radar now updates immediately when location is changed. If it doesn't update, refresh the page or check that the location was s