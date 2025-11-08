# Changelog

## [Unreleased]

### Added

- **Segment-by-Segment Broadcast Generation:** Complete refactor of broadcast generation for perfect audio/video/caption alignment. Each segment (intro, articles, weather, ending) is now created individually with its own TTS audio, video slide, and word-level captions before being compiled into the final broadcast. Guarantees synchronization and eliminates timing issues. (2025-11-08)
- **Broadcast Feature:** A new "Broadcast" feature has been added to the web app, which includes a caption overlay and a button to toggle captions. (2025-11-01)
- **Article Sharing:** Share articles from both the web and mobile apps. (2025-10-31)
- **Force Rewrite:** Manually trigger an AI rewrite for an article from the article details screen. (2025-10-31)
- **Article Bookmarking:** You can now bookmark articles in both the web and mobile apps. (2025-10-31)
- **Search and Filtering:** You can now search for articles by keyword and filter by source in both the web and mobile apps. (2025-10-31)
- **Wind Speed Unit Setting:** You can now select your preferred wind speed unit (mph or km/h) in the settings. The AI-generated weather reports will use the selected unit. (2025-10-30)
- **Mobile Log Viewer:** A new panel in the web UI to view, filter, and manage logs uploaded from the mobile app. (2025-10-30)
- **Location-based Time:** The web UI now displays the current date and time for the selected location. (2025-10-30)
- **PWA: in-app Install button + global handler** (2025-10-29)
- **HTTPS reverse proxy (nginx) on free port 18443 with self-signed cert** (2025-10-29)
- **Flutter mobile app and comprehensive documentation** (2025-10-29)
- **AI Fact-Checking for Rewrites:** Optional verification step to ensure rewritten articles preserve facts. Controlled via `ENABLE_FACT_CHECKING` (default `true`). (2025-11-06)
- **AI Quality Analysis:** Articles are now automatically analyzed for quality during fetching to filter out garbage content (lists, forms, navigation menus, etc.). Low-quality articles are rejected and their URLs are tracked to prevent re-fetching. (2025-11-06)
- **API:** `GET /api/articles/sources`, `GET /api/articles/bookmarked`, `POST /api/articles/{id}/bookmark`, `GET /api/broadcasts`, `GET /api/broadcast/{id}/transcript`, `GET /api/broadcast/{id}/srt`, `POST /api/maintenance/analyze-existing`. (2025-11-06)

### Changed

- **Web UI:** The status bar now shows a countdown timer for rewrite and broadcast phases, and includes "Skip" and "Use Fallback" buttons during rewrites. (2025-11-01)
- **TTS Synthesis:** TTS is now more robust, using POST requests for long text and proactive chunking to prevent audio truncation. (2025-11-01)
- **Weather Icons:** Weather icons in the broadcast video are now rendered as geometric shapes for better reliability. (2025-11-01)
- **TTS Timeout:** Increased timeout for TTS voice generation to 10 minutes to handle longer audio generation tasks. (2025-11-01)
- **Geocoding:** Enhanced geocoding logic to parse and match state information more accurately, ensuring correct location coordinates are returned. (2025-11-01)
- **Docker:** The `nginx` service now generates its own self-signed certificate and configuration, removing the need for pre-existing files. (2025-10-31)
- **Flutter:** The `compileSdk` version has been set to 34 for better compatibility. (2025-10-31)
- **Web & Mobile:** The article view now shows the original content if an AI rewrite is not yet available. (2025-10-31)
- **Web:** The app now waits for weather data to update after a location change. (2025-10-31)
- **TTS Service:** The TTS service now supports all available OpenTTS engines, not just Piper. (2025-10-30)
- **Weather Display:** The web UI now displays the weather's `updated_at` time in the location's timezone. (2025-10-30)
- **Android Widgets:** Major improvements to the news and weather widgets, including better data handling, improved UI, and more detailed weather information. (2025-10-30)
- **Web UI:** The status bar now formats dates and times according to the location's timezone. (2025-10-30)
- **Documentation:** The main `README.md` has been rewritten for clarity and completeness. All documentation has been reviewed and updated. (2025-10-30)
- **Sorting:** Articles are now sorted newest-first across the stack. (2025-10-30)
- **Frontend:** Replaced Tailwind CDN with compiled Tailwind and fixed dark mode. (2025-10-29)
- **Progress Controls:** `/api/progress/skip` and `/api/progress/fallback` accept optional `article_id` to target specific items if active. (2025-11-06)
- **Article Quality Filtering:** New articles are automatically analyzed for quality during the fetch phase. Articles below the quality threshold (default 60) or identified as garbage are not published. (2025-11-06)

### Fixed

- **Broadcast Audio/Video/Caption Alignment:** Fixed synchronization issues between audio, video, and captions in broadcasts. The new segment-by-segment approach ensures perfect alignment by creating each segment individually with actual TTS duration before compilation. (2025-11-08)
- **Image Format Conversion in Broadcasts:** Fixed "cannot write mode P/RGBA as JPEG" errors when processing article images. Images with palette or RGBA modes are now automatically converted to RGB with proper background handling. (2025-11-08)
- **Missing Audio Handling in Broadcasts:** Fixed issue where failed TTS segments would add estimated durations causing misalignment. Failed segments are now skipped entirely from the broadcast. (2025-11-08)
- **Location Persistence:** Fixed issue where location would be overwritten on container rebuild. User-set locations are now preserved and never changed unless explicitly modified by the user. (2025-11-01)
- **Temperature/Wind Speed Units:** Fixed bug where temperature and wind speed units would default to Celsius and km/h instead of using user's database settings. Units now always respect user preferences. (2025-11-01)
- **Radar Location Update:** Fixed radar not updating immediately when location is changed. Radar now uses correct coordinates immediately after location change. (2025-11-01)
- **Geocoding Accuracy:** Improved geocoding to better match city/state combinations, preventing incorrect coordinates (e.g., preventing Virginia coordinates when setting New York locations). (2025-11-01)
- **TTS Voice Persistence:** Fixed TTS container volume mount to properly persist voices (Coqui, Piper, etc.) between container rebuilds on Docker Desktop for Windows. (2025-11-01)
- **Article Rewrite Reliability:** Fixed article rewrite process to ensure articles are always rewritten on scheduled runs, even if previous attempts failed. Articles missing rewrites are automatically included in the next rewrite cycle. (2025-11-01)
- **APK Build Process:** Improved Flutter APK build to handle network failures gracefully, allowing Docker image to build successfully even when Gradle dependency downloads fail. (2025-11-01)
- **Article Raw Content Warning:** Added warning display when articles show raw content, indicating they will be rewritten on the next scheduled run. (2025-11-01)
- **Location Auto-Resolution:** Location auto-detection now only runs when no user-set location exists in the database, preventing unwanted location changes. (2025-11-01)
- **Playwright Tests:** The bookmarking and sharing tests have been made more robust to handle asynchronous operations and network delays. (2025-10-31)
- **Database Migration:** A database migration has been added to automatically add the `wind_speed_unit` column to the `app_settings` table, ensuring smooth updates. (2025-10-30)
- **Scheduler:** The scheduler now uses the location's timezone instead of UTC. (2025-10-30)
- **Flutter:** Fixed config navigation, increased timeouts, added retries, and robust link launch. (2025-10-29)
- **PWA:** Fixed manifest scope/start_url and added PNG icons. (2025-10-29)
- Numerous bug fixes and stability improvements for the Android widgets. (2025-10-30)
