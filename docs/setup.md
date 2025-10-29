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
- Set your units (°F/°C) and location (or use Auto‑detect).
- Click Run Now to start a harvest.

## Common Commands

- Rebuild image: `docker compose build`
- Tail logs: `docker compose logs -f`
- Stop: `docker compose down`

