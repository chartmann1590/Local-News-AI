# Deployment

## Docker Compose

This project is designed to run via Docker Compose. See the root `docker-compose.yml` for the default values. Example:

```
docker compose up --build -d
```

## Ports & Volumes

- App HTTP port: 18080 (host) → 8000 (container)
- Data volume: `./data:/data`

## Environment Files

You can move environment values to a `.env` file and reference them from `docker-compose.yml` for easier updates.

## System Service

For auto‑start on boot, use your host’s service manager (e.g., a systemd unit that runs `docker compose up -d` in the repo directory).

