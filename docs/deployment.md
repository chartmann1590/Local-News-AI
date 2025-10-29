# Deployment

## Docker Compose

This project is designed to run via Docker Compose. See the root `docker-compose.yml` for the default values. Example:

```
docker compose up --build -d
```

To rebuild only the application image after frontend changes and restart it without affecting dependencies:

```
docker compose build app
docker compose up -d --no-deps --force-recreate app
```

## Ports & Volumes

- App HTTP port: 18080 (host) → 8000 (container)
- Data volume: `./data:/data`

### TTS Service (OpenTTS)

- The Compose file includes a TTS container (`synesthesiam/opentts`) for offline voices (Piper engine).
- The app reaches it at `http://tts:5500` on the internal Docker network (no host port is published by default).
- Voice cache is stored under `./data/tts` to persist downloads between runs.

## Environment Files

You can move environment values to a `.env` file and reference them from `docker-compose.yml` for easier updates.

## System Service

For auto-start on boot, use your host’s service manager (e.g., a systemd unit that runs `docker compose up -d` in the repo directory).
## Frontend assets and caching

- The frontend uses compiled Tailwind CSS (darkMode: 'class'). Assets are built during the image build and served from `/static`.
- A simple service worker provides offline caching. If clients don’t see new styles immediately, they may be using cached assets.
  - Ask users to hard refresh.
  - If needed, bump the cache name in `web/public/sw.js` (e.g., update `CACHE_NAME`) and rebuild.
