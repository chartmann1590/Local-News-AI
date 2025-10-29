# Setup & Run

## Requirements

- Docker and Docker Compose
- Ollama running on the host at `http://localhost:11434` (or set `OLLAMA_BASE_URL`)

## Clone and Run

```
docker compose up --build -d
```

Open the app: http://localhost:18080

## First Steps

- Visit Settings → Ollama and click Test to confirm connectivity.
- Optionally pick a specific model (e.g., `llama3.2`).
- Set your units (°F/°C) and location (or use Auto-detect).
- Click Run Now to start a harvest.

## Install as an App (PWA)

- On Android/Chrome or desktop Chromium/Edge: open Settings → Install App, or use your browser menu → Install/Add to Home Screen.
- On iOS Safari: tap Share → Add to Home Screen (Apple doesn’t show the same install prompt).
- Once installed, the app runs fullscreen and caches assets for offline access.

### Optional: Enable Text-to-Speech (TTS)

- The provided Docker Compose includes an OpenTTS (Piper) service the app can use.
- In Settings → Text-to-Speech, enable TTS, leave the base URL as `http://tts:5500` (default), click Refresh Voices, pick a voice, and Preview.
- Once enabled, the UI shows audio playback for the AI weather report and each article.

### Article Chat (Comments)

- No extra setup required. From the articles list, click the “Comments” button under any article to expand a chat.
- Type a question or comment; the AI replies using only that article’s rewrite as context.
- Replies appear under the article using the generated author byline. Use “Clear” to reset the thread.

## Common Commands

- Rebuild all: `docker compose build`
- Rebuild just the app (frontend/backend image): `docker compose build app`
- Apply new image without touching dependencies: `docker compose up -d --no-deps --force-recreate app`
- Tail logs: `docker compose logs -f`
- Stop: `docker compose down`

### Browser cache tip

- If UI styles don’t update (e.g., theme toggle seems ineffective), hard refresh the browser to clear cached assets and service worker content.
