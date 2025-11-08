# Architecture

## Components

- Backend: FastAPI app
  - Scheduling: APScheduler (cron-like jobs)
  - Database: SQLite via SQLAlchemy
  - Templates/Static: serves built React assets
  - Modules:
    - `app/main.py` — API routes and server setup
    - `app/scheduler.py` — scheduled harvest, rewrite loop, weather generation
    - `app/news_fetcher.py` — feed discovery and article scraping/normalization
    - `app/maintenance.py` — dedup and rewrite‑missing helpers
    - `app/weather.py` — geocoding and forecast fetch
    - `app/ai.py` — Ollama helpers (rewrite/generate)
    - `app/progress.py` — in-memory progress tracker for UI
    - Chat endpoints: `GET/POST/DELETE /api/articles/{id}/chat` use article context with Ollama

- Frontend: React + Vite + Tailwind
  - `web/src/ui/App.jsx` — main UI
  - Built to `/app/app/static` in the image for FastAPI to serve

## Broadcast Pipeline (Segment-by-Segment Approach)

**Overview**: The broadcast generation creates each segment individually to ensure perfect audio/video/caption alignment.

### Workflow

1. **Preparation**:
   - Collect latest articles (limit 10, last 48 hours)
   - Get latest weather report
   - Download article images
   - Create intro/ending slides

2. **Segment-by-Segment Generation**:
   - **For each segment** (intro, article 1, article 2, ..., weather, ending):
     a. Generate TTS audio → Get actual duration (e.g., 12.4 seconds)
     b. Create video slide with exact duration from audio (12.4 seconds)
     c. Generate word-level captions aligned to actual timing
     d. Validate segment is complete and aligned
     e. Save individual segment video file

3. **Compilation**:
   - Concatenate all validated segment videos sequentially
   - Adjust caption timings based on segment positions
   - Generate final SRT file with precise word-level timing
   - Save final broadcast video and captions

4. **API Exposure**:
   - Video available via `/api/broadcasts/{id}/video`
   - SRT captions via `/api/broadcasts/{id}/srt`
   - Transcript via broadcast record

### Key Benefits

- **Perfect Synchronization**: Video slide duration exactly matches actual audio duration
- **Word-Level Captions**: Captions show 4 words at a time, precisely timed to audio
- **No Estimated Durations**: All timing based on actual TTS-generated audio
- **Validated Segments**: Each segment confirmed complete before moving to next
- **Graceful Failure Handling**: Failed segments are skipped entirely (no silent gaps)

### Technical Details

- **Individual Segment Files**: Each segment creates its own video file (e.g., `intro_intro_video.mp4`, `article_94_video.mp4`)
- **Audio Embedded**: Audio is embedded in each segment video (no separate audio track)
- **Caption Offset Calculation**: Final SRT file adjusts timings based on cumulative segment positions
- **Temp Directory**: Segments created in temp directory, cleaned up after compilation

## Data Flow (Harvest)

1. Resolve location + timezone (`app/geo.py`).
2. Gather RSS candidates (Bing + Google + extra feeds) → normalized publisher URLs.
3. Fetch article content and create new `Article` rows (min count respected).
4. Rewrite each article with Ollama (single‑threaded, retried), fallback to source on failure.
5. Deduplicate articles (title + image).
6. Refresh forecast + generate AI weather report.

## Data Model (Chat)

- `ChatMessage { id, article_id, role, content, created_at }` — persists per-article conversation history in SQLite.
- Author byline: derived via `_funny_author_for(article)` when AI content exists; used to label AI replies.

## Request Flow (Chat)

1. UI toggles comments under an article and loads history via `GET /api/articles/{id}/chat`.
2. User sends a message via `POST /api/articles/{id}/chat`.
3. Backend trims input, applies a per-IP per-article rate limit, merges recent history, and calls Ollama using the article rewrite as context.
4. Persists both the user message and AI reply into `chat_messages`.
5. UI appends the reply inline.

Rate limit: `CHAT_RATE_LIMIT_PER_MIN` (default 10). Exceeding returns HTTP 429.

## Concurrency

- A global rewrite lock ensures only one rewrite routine runs at a time (scheduler vs. maintenance).
- Progress includes `current_title/url` to show the active rewrite in the UI.

## Bookmarks & Sources

- Bookmarks are stored in `Bookmark { id, article_id, created_at }` and surfaced via `/api/articles/bookmarked`.
- Distinct article sources are available at `/api/articles/sources` for building filter UI.

## Mobile Logs

- Mobile apps can upload logs to `/api/logs/upload` (5MB max, rate-limited). Web UI lists, previews, and deletes logs.
