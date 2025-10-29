# Local News & Weather — Documentation

This folder holds the in‑depth docs. The root README gives a friendly overview; these pages go deeper and avoid repeating the same content.

## Index

- Setup: `setup.md`
- Configuration: `configuration.md`
- Maintenance & Data: `maintenance.md`
- Customization: `customization.md`
- Architecture: `architecture.md`
- Deployment: `deployment.md`
- Troubleshooting: `troubleshooting.md`
- API Reference: `api.md`

## Feature Summary (context)

- Auto location detection with manual override
- Scheduled harvesting + Ollama rewrites (single-threaded, progress tracked)
- Weather forecast with icons and radar
- Smart dedup (title + image) after each run, plus manual action
- Pagination (10/page), friendly UI
- Optional Text-to-Speech (OpenTTS/Piper) with in-app voice selection and audio playback for articles and weather
- Per-article AI comments: collapsible “Comments” under each article; chat uses article context and the generated author name
