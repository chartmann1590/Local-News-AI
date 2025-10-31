# Changelog

## [Unreleased]

### Added

- **Article Bookmarking:** You can now bookmark articles in both the web and mobile apps. (2025-10-31)
- **Search and Filtering:** You can now search for articles by keyword and filter by source in both the web and mobile apps. (2025-10-31)
- **Wind Speed Unit Setting:** You can now select your preferred wind speed unit (mph or km/h) in the settings. The AI-generated weather reports will use the selected unit. (2025-10-30)
- **Mobile Log Viewer:** A new panel in the web UI to view, filter, and manage logs uploaded from the mobile app. (2025-10-30)
- **Location-based Time:** The web UI now displays the current date and time for the selected location. (2025-10-30)
- **PWA: in-app Install button + global handler** (2025-10-29)
- **HTTPS reverse proxy (nginx) on free port 18443 with self-signed cert** (2025-10-29)
- **Flutter mobile app and comprehensive documentation** (2025-10-29)

### Changed

- **TTS Service:** The TTS service now supports all available OpenTTS engines, not just Piper. (2025-10-30)
- **Weather Display:** The web UI now displays the weather's `updated_at` time in the location's timezone. (2025-10-30)
- **Android Widgets:** Major improvements to the news and weather widgets, including better data handling, improved UI, and more detailed weather information. (2025-10-30)
- **Web UI:** The status bar now formats dates and times according to the location's timezone. (2025-10-30)
- **Documentation:** The main `README.md` has been rewritten for clarity and completeness. All documentation has been reviewed and updated. (2025-10-30)
- **Sorting:** Articles are now sorted newest-first across the stack. (2025-10-30)
- **Frontend:** Replaced Tailwind CDN with compiled Tailwind and fixed dark mode. (2025-10-29)

### Fixed

- **Database Migration:** A database migration has been added to automatically add the `wind_speed_unit` column to the `app_settings` table, ensuring smooth updates. (2025-10-30)
- **Scheduler:** The scheduler now uses the location's timezone instead of UTC. (2025-10-30)
- **Flutter:** Fixed config navigation, increased timeouts, added retries, and robust link launch. (2025-10-29)
- **PWA:** Fixed manifest scope/start_url and added PNG icons. (2025-10-29)
- Numerous bug fixes and stability improvements for the Android widgets. (2025-10-30)